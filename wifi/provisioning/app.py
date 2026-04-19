"""Flask web application for Wi-Fi onboarding.

Serves a single-page UI that lists nearby networks,
accepts SSID/password input, and triggers connection.

Bound to the hotspot IP only – never exposed on other interfaces.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from provisioning import config
from provisioning import hotspot as hotspot_mod
from provisioning import nm, scanner
from provisioning.state import State, StateMachine

logger = logging.getLogger(__name__)

sm = StateMachine()


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    @app.route("/")
    def index():
        sm.touch()
        return render_template("index.html", config=config)

    @app.route("/api/status")
    def api_status():
        sm.touch()
        payload: dict[str, Any] = sm.to_dict()
        payload["hotspot_active"] = hotspot_mod.is_active()
        payload["hotspot_ssid"] = config.HOTSPOT_SSID
        payload["hotspot_ip"] = config.HOTSPOT_IP
        payload["current_connection"] = nm.get_active_connection()
        payload["connected"] = nm.is_connected()
        return jsonify(payload)

    @app.route("/api/scan")
    def api_scan():
        sm.touch()
        force = request.args.get("force", "0") == "1"
        networks = scanner.scan(force=force)
        return jsonify({"networks": networks})

    @app.route("/api/connect", methods=["POST"])
    def api_connect():
        sm.touch()
        data = request.get_json(force=True, silent=True) or {}
        ssid = (data.get("ssid") or "").strip()
        password = (data.get("password") or "").strip() or None
        hidden = bool(data.get("hidden", False))
        open_network = bool(data.get("open_network", False))

        if not ssid:
            return jsonify({"ok": False, "error": "SSID is required"}), 400

        if not open_network and password is None:
            return jsonify(
                {"ok": False, "error": "Password is required for secured networks"}
            ), 400

        if len(ssid) > 32:
            return jsonify(
                {"ok": False, "error": "SSID too long (max 32 characters)"}
            ), 400

        if password is not None and len(password) > 63:
            return jsonify(
                {"ok": False, "error": "Password too long (max 63 characters)"}
            ), 400

        sm.transition(State.USER_SUBMITS)

        if not nm.create_wifi_connection(
            ssid, password, hidden=hidden, open_network=open_network
        ):
            sm.transition(State.FAILED, error=f"Failed to create connection for {ssid}")
            return jsonify(
                {"ok": False, "error": "Failed to create connection profile"}
            )

        import threading

        def _attempt_connect() -> None:
            logger.info("stopping hotspot to free wlan0 for client connection …")
            nm.stop_hotspot()
            time.sleep(2)

            if not nm.activate_connection(ssid):
                logger.warning("connection failed – restarting hotspot for retry")
                nm.start_hotspot()
                sm.transition(State.FAILED, error=f"Failed to connect to {ssid}")
                return

            assoc_ok, assoc_msg = nm.verify_association()
            if not assoc_ok:
                logger.warning("association failed – restarting hotspot for retry")
                nm.start_hotspot()
                sm.transition(State.FAILED, error=assoc_msg)
                return

            conn_ok, conn_msg = nm.verify_connectivity()
            status_detail = (
                conn_msg if conn_ok else "Connected to Wi-Fi but no internet detected"
            )
            logger.info("connection successful: %s", status_detail)
            sm.transition(State.TEARDOWN)
            hotspot_mod.stop(sm)
            os.kill(os.getpid(), signal.SIGTERM)

        connect_thread = threading.Thread(target=_attempt_connect, daemon=True)
        connect_thread.start()

        return jsonify(
            {
                "ok": True,
                "message": f"Attempting to connect to {ssid} … "
                f"The hotspot will stop shortly. If successful, the Pi will join your network.",
                "ssid": ssid,
            }
        )

    @app.route("/api/connections")
    def api_connections():
        sm.touch()
        return jsonify({"connections": nm.get_connections()})

    @app.route("/api/trigger_teardown", methods=["POST"])
    def api_trigger_teardown():
        _schedule_teardown()
        return jsonify({"ok": True, "message": "Teardown scheduled"})

    return app


_teardown_scheduled = False


def _schedule_teardown() -> None:
    global _teardown_scheduled
    _teardown_scheduled = True
    logger.info("teardown scheduled – will exit after serving final responses")

    def _do_teardown() -> None:
        time.sleep(1.5)
        logger.info("shutting down setup mode …")
        hotspot_mod.stop(sm)
        os.kill(os.getpid(), signal.SIGTERM)

    import threading

    t = threading.Thread(target=_do_teardown, daemon=True)
    t.start()


def check_trigger_file() -> bool:
    for p in config.TRIGGER_FILE_PATHS:
        if p.exists():
            logger.info("trigger file found: %s", p)
            return True
    return False


def consume_trigger_file() -> None:
    for p in config.TRIGGER_FILE_PATHS:
        if p.exists():
            try:
                p.unlink()
                logger.info("consumed trigger file: %s", p)
            except OSError as exc:
                logger.warning("could not remove trigger file %s: %s", p, exc)


def wait_for_wifi(timeout: int | None = None) -> bool:
    """Wait up to *timeout* seconds for an existing Wi-Fi connection.

    Returns True if connected before the deadline.
    """
    deadline = time.monotonic() + (timeout or config.BOOT_TIMEOUT)
    logger.info(
        "waiting up to %ds for Wi-Fi connection …", timeout or config.BOOT_TIMEOUT
    )
    while time.monotonic() < deadline:
        if nm.is_connected():
            logger.info("Wi-Fi connected – staying in normal mode")
            return True
        time.sleep(2)
    logger.info("no Wi-Fi connection within timeout")
    return False


def _idle_watcher() -> None:
    """Background thread that shuts down setup mode after idle timeout."""
    while True:
        time.sleep(30)
        if sm.state not in (State.SETUP_MODE, State.FAILED):
            continue
        if sm.idle_seconds >= config.IDLE_TIMEOUT:
            logger.info(
                "idle timeout reached (%ds) – shutting down setup mode",
                config.IDLE_TIMEOUT,
            )
            hotspot_mod.stop(sm)
            os.kill(os.getpid(), signal.SIGTERM)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stdout,
    )

    if not nm.nmcli_available():
        logger.critical("nmcli not found – cannot operate")
        sys.exit(1)

    if not nm.networkmanager_running():
        logger.critical("NetworkManager is not running")
        sys.exit(1)

    force_setup = check_trigger_file()
    if force_setup:
        logger.info("trigger file present – forcing setup mode")
        consume_trigger_file()

    if not force_setup:
        connected = wait_for_wifi()
        if connected:
            logger.info("normal boot – Wi-Fi already connected, exiting setup service")
            sys.exit(0)

    logger.info("entering setup mode")

    if not hotspot_mod.start(sm):
        logger.critical("could not start hotspot – exiting")
        sys.exit(1)

    import threading

    idle_thread = threading.Thread(target=_idle_watcher, daemon=True)
    idle_thread.start()
    logger.info("idle timeout watcher started (%ds)", config.IDLE_TIMEOUT)

    app = create_app()
    logger.info("starting web UI on %s:%d", config.WEB_HOST, config.WEB_PORT)

    try:
        app.run(
            host=config.WEB_HOST,
            port=config.WEB_PORT,
            debug=False,
            use_reloader=False,
            threaded=True,
        )
    except KeyboardInterrupt:
        pass
    finally:
        hotspot_mod.stop(sm)
        logger.info("setup mode ended")


if __name__ == "__main__":
    main()
