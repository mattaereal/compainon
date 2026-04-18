#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

echo "=== AI Health Board – Doctor ==="
echo ""

ERRORS=0
WARNINGS=0

IS_PI=false
if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null || grep -q "raspberrypi" /etc/hostname 2>/dev/null; then
    IS_PI=true
    echo "Platform: Raspberry Pi"
else
    echo "Platform: Non-Pi (development machine)"
fi

# Python version
echo -n "Python: "
python3 --version 2>&1 | awk '{print $2}'

# Virtual environment
if [[ -d "venv" ]]; then
    if $IS_PI && ! grep -q "system-site-packages = true" venv/pyvenv.cfg 2>/dev/null; then
        echo "Virtual environment: WARNING – missing --system-site-packages"
        echo "  Pi packages (lgpio, spidev) won't be accessible."
        echo "  Fix: rm -rf venv && python3 -m venv --system-site-packages venv"
        ((ERRORS++))
    else
        echo "Virtual environment: OK"
    fi
else
    echo "Virtual environment: MISSING (run ./scripts/install.sh)"
    ((ERRORS++))
fi

# Config
if [[ -f "config/providers.yaml" ]]; then
    echo "Config: OK"
else
    echo "Config: MISSING (cp config/providers.yaml.example config/providers.yaml)"
    ((WARNINGS++))
fi

# Core imports
echo -n "Core imports: "
if python3 -c "import ai_health_board, ai_health_board.config, ai_health_board.models" 2>/dev/null; then
    echo "OK"
else
    echo "FAIL"
    ((ERRORS++))
fi

# aiohttp
echo -n "aiohttp: "
if python3 -c "import aiohttp; print(aiohttp.__version__)" 2>/dev/null; then
    : # version printed above
else
    echo "MISSING (pip install aiohttp)"
    ((ERRORS++))
fi

# Pillow
echo -n "Pillow: "
if python3 -c "from PIL import Image; print('OK')" 2>/dev/null; then
    echo "OK"
else
    echo "MISSING"
    ((ERRORS++))
fi

# PyYAML
echo -n "PyYAML: "
if python3 -c "import yaml; print('OK')" 2>/dev/null; then
    echo "OK"
else
    echo "MISSING"
    ((ERRORS++))
fi

# Pi-specific checks
if $IS_PI; then
    echo ""
    echo "--- Raspberry Pi checks ---"

    # System apt packages
    for pkg in python3-lgpio python3-spidev python3-rpi.gpio; do
        echo -n "$pkg: "
        if dpkg -s "$pkg" &>/dev/null; then
            echo "INSTALLED"
        else
            echo "MISSING (sudo apt install $pkg)"
            ((ERRORS++))
        fi
    done

    # lgpio import
    echo -n "lgpio import: "
    if python3 -c "import lgpio; print('OK')" 2>/dev/null; then
        echo "OK"
    else
        echo "FAIL (sudo apt install python3-lgpio)"
        ((ERRORS++))
    fi

    # spidev import
    echo -n "spidev import: "
    if python3 -c "import spidev; print('OK')" 2>/dev/null; then
        echo "OK"
    else
        echo "FAIL (sudo apt install python3-spidev)"
        ((ERRORS++))
    fi

    # GPIOZERO_PIN_FACTORY
    echo -n "GPIOZERO_PIN_FACTORY: "
    if [[ -n "${GPIOZERO_PIN_FACTORY:-}" ]]; then
        echo "$GPIOZERO_PIN_FACTORY"
    else
        echo "NOT SET"
        echo "  Fix: export GPIOZERO_PIN_FACTORY=lgpio"
        echo "  (Add to ~/.bashrc or set in systemd service)"
        ((WARNINGS++))
    fi

    # SPI devices
    echo ""
    echo "SPI devices:"
    SPI_FOUND=false
    for dev in /dev/spidev0.0 /dev/spidev0.1; do
        if [[ -e "$dev" ]]; then
            echo "  $dev – EXISTS"
            SPI_FOUND=true
        else
            echo "  $dev – NOT FOUND"
        fi
    done
    if ! $SPI_FOUND; then
        echo "  Enable: sudo raspi-config -> Interface Options -> SPI -> Enable"
        ((WARNINGS++))
    fi

    # Waveshare driver
    echo ""
    echo -n "waveshare_epd V3: "
    if python3 -c "from waveshare_epd import epd2in13_V3; print('OK')" 2>/dev/null; then
        echo "INSTALLED"
    else
        echo "NOT INSTALLED"
        echo "  git clone https://github.com/waveshareteam/e-Paper.git"
        echo "  cd e-Paper/RaspberryPi_JetsonNano/python"
        echo "  sudo apt install -y python3-setuptools"
        echo "  sudo python3 setup.py install"
        ((WARNINGS++))
    fi

    # Config backend check
    echo ""
    if [[ -f "config/providers.yaml" ]]; then
        BACKEND=$(python3 -c "import yaml; c=yaml.safe_load(open('config/providers.yaml')); print(c.get('display',{}).get('backend','mock'))" 2>/dev/null || echo "unknown")
        echo "Config backend: $BACKEND"
        if [[ "$BACKEND" == "mock" ]] && $SPI_FOUND; then
            echo "  [HINT] SPI is available – change backend to 'waveshare_2in13_v3' for e-paper"
            ((WARNINGS++))
        fi
    fi
fi

# Summary
echo ""
if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
    echo "=== All checks passed ==="
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    echo "=== $WARNINGS warning(s), no errors ==="
    exit 0
else
    echo "=== $ERRORS error(s), $WARNINGS warning(s) ==="
    echo "Fix errors before running."
    exit 1
fi
