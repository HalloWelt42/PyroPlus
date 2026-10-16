"""
Testumgebung: kein Hardware-Proxy, eigenes Datenverzeichnis je Testlauf.
Die Umgebungsvariablen müssen vor dem ersten Import von config gesetzt sein.
"""

import os
import tempfile
from pathlib import Path

_DATA = Path(tempfile.mkdtemp(prefix="pyroplus-test-"))
os.environ["HW_PROXY_URL"] = "none"
os.environ["DATA_DIR"] = str(_DATA)
os.environ["OLED_RENDER_INTERVAL"] = "0.05"

import pytest  # noqa: E402


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def stats_dict() -> dict:
    return {
        "cpu": {"temp": 43.5, "temp_min": 41.0, "temp_max": 47.0, "percent": 92.0, "cores": 4},
        "ram": {"total_gb": 16.0, "used_gb": 3.9, "available_gb": 12.1, "percent": 24.4},
        "disks": [
            {"label": "System", "mount": "/", "total_gb": 500.0, "used_gb": 123.4, "available_gb": 376.6,
             "percent": 24.7, "model": "NVMe", "fstype": "ext4"},
            {"label": "Daten", "mount": "/mnt/data", "total_gb": 2000.0, "used_gb": 1500.0,
             "available_gb": 500.0, "percent": 75.0, "model": "USB", "fstype": "ext4"},
        ],
        "network": {"ip": "192.168.178.49", "interface": "eth0", "hostname": "raspberrypi",
                    "rx_bytes_sec": 2048.0, "tx_bytes_sec": 512.0},
        "fan": {"rpm": 1200, "pwm_level": 1, "level_name": "Leise"},
        "uptime": {"seconds": 90061, "formatted": "1d 1h 1m"},
        "history": {"cpu": [10, 20, 30, 40], "temp": [40, 41, 42, 43], "ram": [20, 21, 22, 23]},
    }
