"""
PyroPlus v3.0.0 — System-Statistiken
© HalloWelt42 - Nur für private Nutzung

Sammelt CPU, RAM, Disk, Netzwerk, Docker, Fan-State.
Liest aus /host/* Mounts für echte Host-Daten im Container.
"""

import time
import os
import json
import subprocess
import logging
from collections import deque
from pathlib import Path

logger = logging.getLogger("stats")

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
HISTORY_LEN = 60
_history = {
    "cpu": deque(maxlen=HISTORY_LEN),
    "temp": deque(maxlen=HISTORY_LEN),
    "ram": deque(maxlen=HISTORY_LEN),
    "fan_speed": deque(maxlen=HISTORY_LEN),
    "net_rx": deque(maxlen=HISTORY_LEN),
    "net_tx": deque(maxlen=HISTORY_LEN),
}

# Exportierbare Referenz für fan/controller.py
fan_speed_history = _history["fan_speed"]
_prev_net = {"rx": 0, "tx": 0, "time": 0}


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        return 0.0


def get_cpu_percent():
    try:
        with open("/proc/loadavg") as f:
            load1 = float(f.read().split()[0])
        cores = os.cpu_count() or 4
        return round(min(100.0, (load1 / cores) * 100), 1)
    except Exception:
        return 0.0


def get_ram():
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if parts[0] in ("MemTotal:", "MemAvailable:"):
                    info[parts[0].rstrip(":")] = int(parts[1]) * 1024
        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", 0)
        used = total - available
        return {
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "available_gb": round(available / (1024**3), 1),
            "percent": round((used / total) * 100, 1) if total else 0,
        }
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "available_gb": 0, "percent": 0}


# ─── Disk-Konfiguration ─────────────────────────────────────
_disk_config_path = DATA_DIR / "disk_config.json"

def get_disk_config() -> dict:
    """Disk-Konfiguration laden. monitored_mounts=[] → nur Default (/)."""
    try:
        if _disk_config_path.exists():
            return json.loads(_disk_config_path.read_text())
    except Exception:
        pass
    return {"monitored_mounts": []}  # Leer = alle Disks anzeigen

def set_disk_config(config: dict):
    """Disk-Konfiguration speichern."""
    try:
        _disk_config_path.parent.mkdir(parents=True, exist_ok=True)
        _disk_config_path.write_text(json.dumps(config, indent=2))
    except Exception as e:
        logger.error(f"Disk-Config speichern: {e}")

def get_all_disks():
    """Alle erkannten Disks zurückgeben (ungefiltert, für Settings-UI)."""
    return _detect_disks()

def get_disks():
    """Nur konfigurierte Disks zurückgeben."""
    all_disks = _detect_disks()
    config = get_disk_config()
    monitored = config.get("monitored_mounts", ["/"])
    if not monitored:
        return all_disks  # Leer = alle anzeigen
    return [d for d in all_disks if d["mount"] in monitored]

def _detect_disks():
    """Alle relevanten Festplatten — erkennt Host-Disks über /host Mount.
    Dedupliziert nach Device-Pfad UND Dateisystem-ID (dev_t) um doppelte Einträge zu vermeiden.
    Pi 5 hat typischerweise 3 Partitionen: System (/), NVMe (/mnt/nvme), USB (/mnt/usb).
    """
    disks = []
    seen_devices = set()   # Device-Pfad z.B. /dev/nvme0n1p1
    seen_fs_ids = set()    # (total_bytes, device_base) um identische Mounts zu erkennen
    skip_fs = {"tmpfs", "devtmpfs", "squashfs", "overlay", "fuse.mergerfs",
               "swap", "sysfs", "proc", "cgroup2", "cgroup", "efivarfs",
               "autofs", "securityfs", "pstore", "bpf", "tracefs",
               "debugfs", "configfs", "fusectl", "mqueue", "hugetlbfs",
               "ramfs", "binfmt_misc", "nsfs"}
    skip_mount_prefixes = ("/snap", "/run", "/sys", "/proc", "/dev/shm", "/boot/firmware")

    # Zuerst über /host/proc/mounts die echten Host-Mounts finden
    host_mounts_file = "/host/proc/mounts"
    use_host = os.path.exists(host_mounts_file)

    if use_host:
        try:
            with open(host_mounts_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 3:
                        continue
                    source, mount, fstype = parts[0], parts[1], parts[2]
                    if fstype in skip_fs:
                        continue
                    if not source.startswith("/dev/"):
                        continue
                    if any(mount.startswith(p) for p in skip_mount_prefixes):
                        continue

                    # Dedup: gleiches Device überspringen
                    if source in seen_devices:
                        continue

                    host_path = "/host" + mount
                    if not os.path.exists(host_path):
                        continue

                    try:
                        st = os.statvfs(host_path)
                        total = st.f_frsize * st.f_blocks
                        used = st.f_frsize * (st.f_blocks - st.f_bfree)
                        avail = st.f_frsize * st.f_bavail
                        if total == 0:
                            continue
                        pct = round(used / total * 100)
                    except Exception:
                        continue

                    # Dedup: gleiches Filesystem (gleiche Größe + gleiche Device-Basis) überspringen
                    dev_name = source.split("/")[-1]
                    base_dev = dev_name.rstrip("0123456789")
                    if base_dev.endswith("p"):
                        base_dev = base_dev[:-1]
                    fs_id = (total, base_dev)
                    if fs_id in seen_fs_ids:
                        continue

                    seen_devices.add(source)
                    seen_fs_ids.add(fs_id)

                    # Model bestimmen
                    model = ""
                    for model_path in [f"/host/sys/block/{base_dev}/device/model",
                                       f"/sys/block/{base_dev}/device/model"]:
                        try:
                            with open(model_path) as f:
                                model = f.read().strip()
                                break
                        except Exception:
                            pass

                    # Label
                    if mount == "/":
                        label = "System"
                    elif "/mnt/" in mount:
                        label = mount.split("/")[-1].capitalize() or mount
                    elif mount == "/boot/firmware":
                        label = "Boot"
                    else:
                        label = mount.split("/")[-1].capitalize() or mount

                    disks.append({
                        "device": source,
                        "mount": mount,
                        "label": label,
                        "fstype": fstype,
                        "total_gb": round(total / (1024**3), 1),
                        "used_gb": round(used / (1024**3), 1),
                        "available_gb": round(avail / (1024**3), 1),
                        "percent": pct,
                        "model": model,
                    })
        except Exception:
            pass

    # Fallback: df-basiert (für Docker ohne /host Mount)
    if not disks:
        try:
            result = subprocess.run(
                ["df", "-B1", "--output=source,fstype,size,used,avail,pcent,target"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) < 7:
                    continue
                source, fstype = parts[0], parts[1]
                size, used, avail = int(parts[2]), int(parts[3]), int(parts[4])
                pcent = parts[5].rstrip("%")
                mount = parts[6]

                if fstype in skip_fs or not source.startswith("/dev/"):
                    continue
                if any(mount.startswith(p) for p in skip_mount_prefixes):
                    continue
                if source in seen_devices:
                    continue
                seen_devices.add(source)

                model = ""
                dev_name = source.split("/")[-1]
                base_dev = dev_name.rstrip("0123456789")
                if base_dev.endswith("p"):
                    base_dev = base_dev[:-1]
                try:
                    with open(f"/sys/block/{base_dev}/device/model") as f:
                        model = f.read().strip()
                except Exception:
                    pass

                if mount == "/":
                    label = "System"
                elif mount == "/boot/firmware":
                    label = "Boot"
                else:
                    label = mount.split("/")[-1].capitalize()

                disks.append({
                    "device": source, "mount": mount, "label": label,
                    "fstype": fstype,
                    "total_gb": round(size / (1024**3), 1),
                    "used_gb": round(used / (1024**3), 1),
                    "available_gb": round(avail / (1024**3), 1),
                    "percent": int(pcent) if pcent.isdigit() else 0,
                    "model": model,
                })
        except Exception:
            pass

    # Sortieren: System zuerst, dann nach Label
    disks.sort(key=lambda d: (0 if d["label"] == "System" else 1, d["label"]))
    return disks


def get_network():
    """Host-Netzwerk-Stats — liest AUSSCHLIESSLICH aus /host Filesystem.
    ip command im Container zeigt nur Container-Interfaces!"""
    result = {
        "ip": "N/A",
        "interface": "",
        "rx_bytes_sec": 0,
        "tx_bytes_sec": 0,
        "all_ips": [],
    }
    try:
        # 1. Host-Interface über /host/proc/net/route finden (Default-Route)
        host_iface = ""
        try:
            with open("/host/proc/net/route") as f:
                for line in f.readlines()[1:]:
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[1] == "00000000":  # Default-Route
                        iface = parts[0]
                        if iface not in ("lo",) and not iface.startswith(("br-", "docker", "veth")):
                            host_iface = iface
                            break
        except Exception:
            pass

        # 2. Host-IP über /host/proc/net/fib_trie (IPv4)
        host_ip = ""
        if host_iface:
            try:
                # Methode: /host/proc/1/net/if_inet6 oder einfach aus fib_trie
                # Einfachster Weg: alle IPs aus /host/proc/net/fib_trie parsen
                with open("/host/proc/net/fib_trie") as f:
                    lines = f.readlines()
                local_ips = []
                in_local = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if "/32 host LOCAL" in stripped:
                        in_local = True
                    elif in_local and "|--" in stripped:
                        ip = stripped.split("|--")[-1].strip()
                        if ip and not ip.startswith("127.") and not ip.startswith("172.") and not ip.startswith("0."):
                            local_ips.append(ip)
                        in_local = False
                    elif stripped and not stripped.startswith("|"):
                        in_local = False

                # Alternativ: /host/proc/net/if_inet6 → nein, IPv4 besser aus arp
                # Einfachster zuverlässiger Weg:
                if not local_ips:
                    # Parse /host/proc/net/arp für Gateway-Interface
                    try:
                        with open("/host/proc/net/arp") as f:
                            for line in f.readlines()[1:]:
                                parts = line.split()
                                if len(parts) >= 6 and parts[5] == host_iface:
                                    # Das ist die Gateway-Zeile, nicht unsere IP
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass

            # Robuster Fallback: nsenter oder IP aus hostname
            if not host_ip:
                try:
                    # /host/etc/hostname für Name, IP aus /host/proc/net/tcp
                    import struct, socket
                    with open("/host/proc/net/tcp") as f:
                        for line in f.readlines()[1:]:
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                local = parts[1].split(":")
                                hex_ip = local[0]
                                if len(hex_ip) == 8 and hex_ip != "00000000":
                                    ip_int = struct.unpack("=I", bytes.fromhex(hex_ip))[0]
                                    ip = socket.inet_ntoa(struct.pack("=I", ip_int))
                                    if not ip.startswith("127.") and not ip.startswith("172.") and not ip.startswith("10."):
                                        host_ip = ip
                                        break
                                    elif ip.startswith("192.168."):
                                        host_ip = ip
                                        break
                except Exception:
                    pass

            # Letzter Fallback: IP aus fib_trie local_ips
            if not host_ip and local_ips:
                # Bevorzuge 192.168.x.x
                for ip in local_ips:
                    if ip.startswith("192.168."):
                        host_ip = ip
                        break
                if not host_ip:
                    host_ip = local_ips[0]

        if host_iface:
            result["interface"] = host_iface
            result["ip"] = host_ip or "Host"
            if not _prev_net.get("logged"):
                logger.info(f"Netzwerk erkannt: {host_iface} → {host_ip or 'IP unbekannt'}")
                _prev_net["logged"] = True

        # 3. Throughput aus /host/sys/class/net/{iface}/statistics/
        now = time.time()
        rx_total = tx_total = 0
        if host_iface:
            try:
                with open(f"/host/sys/class/net/{host_iface}/statistics/rx_bytes") as f:
                    rx_total = int(f.read().strip())
                with open(f"/host/sys/class/net/{host_iface}/statistics/tx_bytes") as f:
                    tx_total = int(f.read().strip())
            except Exception:
                pass

        if _prev_net["time"] > 0 and rx_total > 0:
            dt = now - _prev_net["time"]
            if dt > 0:
                result["rx_bytes_sec"] = max(0, round((rx_total - _prev_net["rx"]) / dt))
                result["tx_bytes_sec"] = max(0, round((tx_total - _prev_net["tx"]) / dt))
        _prev_net.update(rx=rx_total, tx=tx_total, time=now)

    except Exception:
        pass
    return result


_docker_client = None
_docker_cache = None
_docker_cache_time = 0
_DOCKER_CACHE_TTL = 10.0  # Docker nur alle 10s abfragen

def get_docker_containers():
    """Docker-Container via Python SDK — cached für 10 Sekunden."""
    global _docker_client, _docker_cache, _docker_cache_time
    now = time.time()
    if _docker_cache is not None and (now - _docker_cache_time) < _DOCKER_CACHE_TTL:
        return _docker_cache

    containers = []
    try:
        import docker as docker_sdk
        if _docker_client is None:
            _docker_client = docker_sdk.DockerClient(base_url="unix:///var/run/docker.sock", timeout=5)
        for c in _docker_client.containers.list(all=True):
            name = c.name
            status_raw = c.status  # running, exited, paused, etc.
            running = status_raw == "running"
            # Ports extrahieren
            ports_dict = c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            port_strs = []
            for internal, bindings in ports_dict.items():
                if bindings:
                    for b in bindings:
                        hp = b.get("HostPort", "")
                        if hp:
                            port_strs.append(f"{hp}→{internal}")
                else:
                    port_strs.append(internal)
            containers.append({
                "name": name,
                "status": "running" if running else "stopped",
                "status_raw": status_raw,
                "ports": ", ".join(port_strs[:4]),
                "image": c.image.tags[0] if c.image.tags else str(c.image.short_id),
            })
        # Client bleibt offen (persistent)
    except Exception as ex:
        logger.warning(f"Docker SDK Fehler: {ex}")
        _docker_client = None  # Reset bei Fehler
        # Fallback: docker CLI
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    containers.append({
                        "name": parts[0],
                        "status": "running" if parts[1].lower().startswith("up") else "stopped",
                        "status_raw": parts[1],
                        "ports": parts[2] if len(parts) > 2 else "",
                        "image": parts[3] if len(parts) > 3 else "",
                    })
            logger.info(f"Docker CLI fallback: {len(containers)} Container")
        except Exception as ex2:
            logger.warning(f"Docker CLI Fehler: {ex2}")
    running = sum(1 for c in containers if c["status"] == "running")
    _docker_cache = {"containers": containers, "running": running, "total": len(containers)}
    _docker_cache_time = time.time()
    return _docker_cache


def get_fan_state():
    """Fan: PWM Kernel-Stufe (0-3) + RPM."""
    state = {"pwm_level": 0, "rpm": 0, "pwm_supported": False, "level_name": "Aus"}
    level_names = ["Aus", "Leise", "Mittel", "Voll"]

    try:
        if os.path.exists("/sys/class/thermal/cooling_device0/cur_state"):
            with open("/sys/class/thermal/cooling_device0/cur_state") as f:
                state["pwm_level"] = int(f.read().strip())
            state["pwm_supported"] = True
            state["level_name"] = level_names[min(state["pwm_level"], 3)]
    except Exception:
        pass

    try:
        hwmon_dir = "/sys/devices/platform/cooling_fan/hwmon/"
        if os.path.exists(hwmon_dir):
            sub = os.listdir(hwmon_dir)[0]
            with open(f"{hwmon_dir}{sub}/fan1_input") as f:
                state["rpm"] = int(f.read().strip())
    except Exception:
        pass

    return state


def get_uptime():
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        days = int(secs // 86400)
        hours = int((secs % 86400) // 3600)
        mins = int((secs % 3600) // 60)
        if days > 0:
            formatted = f"{days}d {hours}h {mins}m"
        elif hours > 0:
            formatted = f"{hours}h {mins}m"
        else:
            formatted = f"{mins}m"
        return {"seconds": int(secs), "formatted": formatted}
    except Exception:
        return {"seconds": 0, "formatted": "?"}


_cached_stats = None
_cached_stats_time = 0
_STATS_CACHE_TTL = 0.8  # Muss < WS_STATS_INTERVAL sein

def collect_stats():
    """Alle Stats sammeln + History aktualisieren. Cached für 2 Sekunden."""
    global _cached_stats, _cached_stats_time
    now = time.time()
    if _cached_stats and (now - _cached_stats_time) < _STATS_CACHE_TTL:
        return _cached_stats

    temp = get_cpu_temp()
    cpu_pct = get_cpu_percent()
    ram = get_ram()
    try:
        disks = get_disks()
    except Exception:
        disks = []
    try:
        network = get_network()
    except Exception:
        network = {"interface": "?", "ip": "?", "rx_bytes_sec": 0, "tx_bytes_sec": 0}
    docker = {"running": 0, "total": 0, "containers": []}
    try:
        fan = get_fan_state()
    except Exception:
        fan = {"pwm_level": 0}
    uptime = get_uptime()

    _history["cpu"].append(cpu_pct)
    _history["temp"].append(temp)
    _history["ram"].append(ram["percent"])
    _history["fan_speed"].append(fan["pwm_level"] * 33)
    _history["net_rx"].append(network["rx_bytes_sec"])
    _history["net_tx"].append(network["tx_bytes_sec"])

    temp_history = list(_history["temp"])

    _cached_stats = {
        "cpu": {
            "temp": temp,
            "temp_min": min(temp_history) if temp_history else 0,
            "temp_max": max(temp_history) if temp_history else 0,
            "percent": cpu_pct,
            "cores": os.cpu_count() or 4,
        },
        "ram": ram,
        "disks": disks,
        "network": network,
        "docker": docker,
        "fan": fan,
        "uptime": uptime,
        "history": {k: list(v) for k, v in _history.items()},
    }
    _cached_stats_time = now
    return _cached_stats

# Alias für oled/engine.py
get_system_stats = collect_stats
