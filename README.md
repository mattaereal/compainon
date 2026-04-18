# AI Health Status Board

A small Python application for Raspberry Pi that displays AI service status on a 2.13" e-paper display.

## What it does

Polls public health/status endpoints for AI services and renders a clean status dashboard on a Waveshare 2.13" V3 e-paper display. Supports extension via YAML config and plugin adapters.

## Supported hardware

- Raspberry Pi Zero 2 W / Pi 3 / Pi 4 / Pi 5 (with SPI)
- Waveshare 2.13" V3 e-paper display (black/white, 122x250)
- Mock PNG backend for development on laptops

## Quick start on a laptop (mock mode)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config/providers.yaml.example config/providers.yaml
python app.py preview
# Output: ./out/frame.png
```

## Raspberry Pi setup

### 1. Install system packages

Raspberry Pi OS Trixie (64-bit) uses the character device GPIO interface, not the deprecated sysfs interface. You must install `lgpio`:

```bash
sudo apt update
sudo apt install -y python3-lgpio python3-spidev python3-rpi.gpio python3-pip python3-setuptools
```

### 2. Enable SPI

```bash
sudo raspi-config
# -> Interface Options -> SPI -> Enable -> Finish -> Reboot
```

### 3. Install Waveshare e-paper driver

```bash
cd ~
git clone https://github.com/waveshareteam/e-Paper.git
cd e-Paper/RaspberryPi_JetsonNano/python
sudo python3 setup.py install
```

### 4. Add user to GPIO/SPI groups

```bash
sudo usermod -a -G spi,gpio $USER
# Log out and back in for group changes to take effect
```

### 5. Set GPIO pin factory

Required on Trixie/Bookworm so gpiozero uses `lgpio` instead of the deprecated sysfs:

```bash
export GPIOZERO_PIN_FACTORY=lgpio
# Add to ~/.bashrc for persistence:
echo 'export GPIOZERO_PIN_FACTORY=lgpio' >> ~/.bashrc
```

### 6. Copy repo and install

```bash
# From your dev machine:
scp -r ai-health-board pi@raspberrypi.local:~/

# On the Pi:
cd ~/ai-health-board
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```

**Important:** The venv MUST be created with `--system-site-packages` so the app can access `lgpio`, `spidev`, and `waveshare_epd` installed at the system level.

### 7. Configure for e-paper display

Edit `config/providers.yaml`:

```yaml
display:
  backend: waveshare_2in13_v3  # Change from 'mock'
  width: 122
  height: 250
  full_refresh_every_n_updates: 6
```

### 8. Test

```bash
source venv/bin/activate
export GPIOZERO_PIN_FACTORY=lgpio
python app.py once
```

### 9. Install as systemd service

```bash
# Edit the service file to match your username/path if not 'pi'
sudo cp systemd/ai-health-board.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-health-board
sudo systemctl start ai-health-board
```

View logs:
```bash
sudo journalctl -u ai-health-board -f
```

## CLI Commands

```bash
python app.py doctor        # Check environment and dependencies
python app.py preview       # Render one frame to PNG (mock mode)
python app.py once          # Fetch and display once, then exit
python app.py run           # Long-running service loop
python app.py run --once-after 30  # Wait 30s before first refresh
```

## Configuring providers

Edit `config/providers.yaml`:

```yaml
refresh_seconds: 300
timezone: UTC
display:
  backend: waveshare_2in13_v3
  width: 122
  height: 250
  full_refresh_every_n_updates: 6

providers:
  - name: Claude
    type: statuspage
    url: https://status.claude.com/api/v2/summary.json
    components:
      - claude.ai
      - Claude Code
      - Claude API (api.anthropic.com)

  - name: OpenAI
    type: statuspage
    url: https://status.openai.com/api/v2/summary.json
    components:
      - App
      - Conversations
      - Codex Web
      - Codex API
```

Component name matching:
1. Exact match first
2. Case-insensitive fallback
3. If not found -> UNKNOWN (logged as warning)

## Adding a new provider adapter

1. Create `ai_health_board/providers/custom.py`
2. Implement `StatusProvider` base class
3. Register in `ai_health_board/providers/__init__.py`
4. Add entries to `config/providers.yaml`

```python
from ai_health_board.providers.base import StatusProvider, ServiceStatus
from typing import Any, Dict

class CustomProvider(StatusProvider):
    def __init__(self, display_name: str, url: str, component_keys: list):
        self._display_name = display_name
        self.url = url
        self.component_keys = component_keys

    def provider_type(self) -> str:
        return "custom"

    def display_name(self) -> str:
        return self._display_name

    async def fetch_status(self, session, timeout=10) -> Dict[str, Any]:
        resp = await session.get(self.url, timeout=aiohttp.ClientTimeout(total=timeout))
        resp.raise_for_status()
        return await resp.json()

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, ServiceStatus]:
        return {"service": ServiceStatus.OK}
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'lgpio'`
```bash
sudo apt install python3-lgpio
```

### `PinFactoryFallback: Falling back from lgpio`
The `GPIOZERO_PIN_FACTORY` environment variable is not set:
```bash
export GPIOZERO_PIN_FACTORY=lgpio
```

### `OSError: [Errno 22] Invalid argument` on `/sys/class/gpio`
You're on Trixie which removed the sysfs GPIO interface. Set:
```bash
export GPIOZERO_PIN_FACTORY=lgpio
```

### Display not updating
1. Check SPI: `ls /dev/spidev*`
2. Check driver: `python3 -c "from waveshare_epd import epd2in13_V3"`
3. Check config: `display.backend` should be `waveshare_2in13_v3`
4. Check env: `echo $GPIOZERO_PIN_FACTORY` should be `lgpio`
5. Try mock first: set `backend: mock`, run `python app.py preview`

### venv can't find lgpio/spidev
The venv was created without `--system-site-packages`. Recreate it:
```bash
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
```

## Security notes

- Outbound-only HTTP polling (no inbound services)
- No secrets required for public status endpoints
- SSH keys recommended for deployment
- Runs as unprivileged user (must be in `spi` and `gpio` groups)

## Development

```bash
python -m pytest tests/ -v
```

## License

MIT License
