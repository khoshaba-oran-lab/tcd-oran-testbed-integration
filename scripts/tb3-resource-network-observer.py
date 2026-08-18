#!/usr/bin/env python3

import argparse
import glob
import json
import os
import subprocess
import time
from datetime import datetime, timezone


CONTAINERS = {
    "gnb": "base05_srsran_gnb",
    "srsue": "base05_srsran_srsue",
    "5gc": "base05_open5gs_5gc",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_int(path):
    value = read_text(path).strip()
    if value == "max":
        return None
    return int(value)


def read_key_values(path):
    result = {}
    for line in read_text(path).splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                result[parts[0]] = int(parts[1])
            except ValueError:
                result[parts[0]] = parts[1]
    return result


def read_proc_stat():
    cpus = {}
    system = {}

    for line in read_text("/proc/stat").splitlines():
        parts = line.split()
        if not parts:
            continue

        key = parts[0]

        if key == "cpu" or key.startswith("cpu") and key[3:].isdigit():
            values = [int(x) for x in parts[1:]]
            cpus[key] = values
        elif key in (
            "ctxt",
            "intr",
            "processes",
            "procs_running",
            "procs_blocked",
        ):
            system[key] = int(parts[1])

    return cpus, system


def cpu_percentages(previous, current):
    names = [
        "user",
        "nice",
        "system",
        "idle",
        "iowait",
        "irq",
        "softirq",
        "steal",
    ]

    delta = [
        max(0, current[i] - previous[i])
        for i in range(min(8, len(previous), len(current)))
    ]

    while len(delta) < 8:
        delta.append(0)

    total = sum(delta)
    if total <= 0:
        return None

    result = {
        names[i] + "_pct": round(delta[i] * 100.0 / total, 3)
        for i in range(8)
    }

    result["busy_pct"] = round(
        100.0 - result["idle_pct"] - result["iowait_pct"], 3
    )
    return result


def read_loadavg():
    parts = read_text("/proc/loadavg").split()
    running, total = parts[3].split("/", 1)

    return {
        "load1": float(parts[0]),
        "load5": float(parts[1]),
        "load15": float(parts[2]),
        "procs_running_loadavg": int(running),
        "procs_total": int(total),
    }


def read_meminfo():
    wanted = {
        "MemTotal",
        "MemFree",
        "MemAvailable",
        "Buffers",
        "Cached",
        "SwapTotal",
        "SwapFree",
        "Dirty",
    }

    result = {}
    for line in read_text("/proc/meminfo").splitlines():
        key, value = line.split(":", 1)
        if key in wanted:
            fields = value.split()
            result[key + "_bytes"] = int(fields[0]) * 1024

    return result


def read_net_dev(path):
    result = {}

    for line in read_text(path).splitlines()[2:]:
        if ":" not in line:
            continue

        iface, values = line.split(":", 1)
        iface = iface.strip()
        fields = values.split()

        if len(fields) < 16:
            continue

        result[iface] = {
            "rx_bytes": int(fields[0]),
            "rx_packets": int(fields[1]),
            "rx_errors": int(fields[2]),
            "rx_dropped": int(fields[3]),
            "tx_bytes": int(fields[8]),
            "tx_packets": int(fields[9]),
            "tx_errors": int(fields[10]),
            "tx_dropped": int(fields[11]),
        }

    return result


def read_softirqs():
    lines = read_text("/proc/softirqs").splitlines()
    result = {}

    for line in lines[1:]:
        if ":" not in line:
            continue

        name, values = line.split(":", 1)
        name = name.strip()

        if name not in {
            "TIMER",
            "NET_TX",
            "NET_RX",
            "BLOCK",
            "SCHED",
            "RCU",
        }:
            continue

        result[name] = [int(x) for x in values.split()]

    return result


def read_guest_cpu_mhz():
    values = []

    for line in read_text("/proc/cpuinfo").splitlines():
        if line.lower().startswith("cpu mhz"):
            try:
                values.append(float(line.split(":", 1)[1].strip()))
            except ValueError:
                pass

    return {
        "runtime_frequency_reliable": False,
        "source": "/proc/cpuinfo_guest_reported",
        "per_cpu_mhz": values,
    }


def read_thermal():
    zones = []

    for zone in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        try:
            zone_type = read_text(os.path.join(zone, "type")).strip()
            raw_temp = read_int(os.path.join(zone, "temp"))
            zones.append(
                {
                    "zone": os.path.basename(zone),
                    "type": zone_type,
                    "temp_millicelsius": raw_temp,
                }
            )
        except (OSError, ValueError):
            continue

    return {
        "available": bool(zones),
        "zones": zones,
    }


def docker_inventory():
    names = list(CONTAINERS.values())

    cp = subprocess.run(
        ["docker", "inspect", *names],
        check=True,
        capture_output=True,
        text=True,
    )

    raw = json.loads(cp.stdout)
    by_name = {
        item["Name"].lstrip("/"): item
        for item in raw
    }

    result = {}

    for role, name in CONTAINERS.items():
        item = by_name[name]
        state = item["State"]
        pid = int(state["Pid"])

        result[role] = {
            "name": name,
            "id": item["Id"],
            "pid": pid,
            "status": state["Status"],
            "running": bool(state["Running"]),
            "oom_killed": bool(state["OOMKilled"]),
            "restart_count": int(item["RestartCount"]),
            "started_at": state["StartedAt"],
        }

    return result


def cgroup_path(pid):
    for line in read_text(f"/proc/{pid}/cgroup").splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3 and parts[0] == "0":
            return "/sys/fs/cgroup" + parts[2]

    raise RuntimeError(f"cgroup v2 path not found for PID {pid}")


def read_io_stat(path):
    devices = {}
    totals = {
        "rbytes": 0,
        "wbytes": 0,
        "rios": 0,
        "wios": 0,
        "dbytes": 0,
        "dios": 0,
    }

    for line in read_text(path).splitlines():
        parts = line.split()
        if not parts:
            continue

        dev = parts[0]
        values = {}

        for token in parts[1:]:
            key, value = token.split("=", 1)
            values[key] = int(value)

            if key in totals:
                totals[key] += int(value)

        devices[dev] = values

    return {
        "totals": totals,
        "devices": devices,
    }


def read_container_metrics(info):
    pid = info["pid"]
    cg = cgroup_path(pid)

    return {
        "state": info,
        "cgroup": cg,
        "cpu_stat": read_key_values(os.path.join(cg, "cpu.stat")),
        "cpu_max": read_text(os.path.join(cg, "cpu.max")).strip(),
        "memory_current_bytes": read_int(os.path.join(cg, "memory.current")),
        "memory_peak_bytes": read_int(os.path.join(cg, "memory.peak")),
        "memory_max_bytes": read_int(os.path.join(cg, "memory.max")),
        "memory_events": read_key_values(os.path.join(cg, "memory.events")),
        "pids_current": read_int(os.path.join(cg, "pids.current")),
        "io": read_io_stat(os.path.join(cg, "io.stat")),
        "network": read_net_dev(f"/proc/{pid}/net/dev"),
    }


def read_qdisc(interface):
    try:
        cp = subprocess.run(
            ["tc", "-s", "-j", "qdisc", "show", "dev", interface],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(cp.stdout)
    except Exception as exc:
        return {
            "error": str(exc),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Sampling interval in seconds; default: 1.0",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Number of emitted samples; 0 means run until interrupted",
    )
    parser.add_argument(
        "--qdisc-every",
        type=int,
        default=5,
        help="Sample host enp1s0 qdisc every N output samples",
    )
    args = parser.parse_args()

    if args.interval <= 0:
        raise SystemExit("--interval must be > 0")

    previous_cpus, _ = read_proc_stat()
    previous_time_ns = time.monotonic_ns()

    interval_ns = int(args.interval * 1_000_000_000)
    next_deadline_ns = previous_time_ns + interval_ns

    sample_no = 0
    qdisc_cache = None

    while args.count == 0 or sample_no < args.count:
        sleep_ns = next_deadline_ns - time.monotonic_ns()

        if sleep_ns > 0:
            time.sleep(sleep_ns / 1_000_000_000.0)

        now_ns = time.monotonic_ns()
        dt_s = (now_ns - previous_time_ns) / 1_000_000_000.0

        current_cpus, proc_system = read_proc_stat()

        cpu = {}
        for cpu_name, values in current_cpus.items():
            if cpu_name in previous_cpus:
                cpu[cpu_name] = cpu_percentages(
                    previous_cpus[cpu_name],
                    values,
                )

        inventory = docker_inventory()

        containers = {}
        for role, info in inventory.items():
            try:
                containers[role] = read_container_metrics(info)
            except Exception as exc:
                containers[role] = {
                    "state": info,
                    "error": str(exc),
                }

        if (
            qdisc_cache is None
            or args.qdisc_every <= 1
            or sample_no % args.qdisc_every == 0
        ):
            qdisc_cache = {
                "interface": "enp1s0",
                "sampled_utc": utc_now(),
                "data": read_qdisc("enp1s0"),
            }

        record = {
            "schema": "sci_oran_resource_network_observability_v1",
            "timestamp_utc": utc_now(),
            "timestamp_unix_ns": time.time_ns(),
            "sample_no": sample_no + 1,
            "interval_requested_s": args.interval,
            "interval_actual_s": round(dt_s, 6),
            "host": {
                "cpu": cpu,
                "load": read_loadavg(),
                "proc_stat": proc_system,
                "memory": read_meminfo(),
                "softirqs": read_softirqs(),
                "frequency": read_guest_cpu_mhz(),
                "thermal": read_thermal(),
                "network": read_net_dev("/proc/net/dev"),
                "qdisc": qdisc_cache,
            },
            "containers": containers,
        }

        print(
            json.dumps(
                record,
                separators=(",", ":"),
                sort_keys=True,
            ),
            flush=True,
        )

        previous_cpus = current_cpus
        previous_time_ns = now_ns
        sample_no += 1

        next_deadline_ns += interval_ns

        current_ns = time.monotonic_ns()
        if next_deadline_ns <= current_ns:
            missed = (
                (current_ns - next_deadline_ns) // interval_ns
            ) + 1
            next_deadline_ns += missed * interval_ns


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
