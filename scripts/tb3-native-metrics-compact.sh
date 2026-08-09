#!/usr/bin/env bash

set -Eeuo pipefail

HOST="${1:-10.53.1.1}"
PORT="${2:-55555}"

exec python3 -u - "$HOST" "$PORT" <<'PY'
import json
import socket
import sys
import time

host = sys.argv[1]
port = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((host, port))

print(f"COMPACT_METRICS_READY={host}:{port}", flush=True)

previous_rx_ns = None

try:
    while True:
        data, addr = sock.recvfrom(65535)
        rx_ns = time.time_ns()

        if previous_rx_ns is None:
            dt_ms = None
        else:
            dt_ms = (rx_ns - previous_rx_ns) / 1_000_000.0

        previous_rx_ns = rx_ns

        try:
            obj = json.loads(data.decode("utf-8"))
        except Exception as exc:
            print(
                f"PARSE_ERROR src={addr[0]}:{addr[1]} "
                f"bytes={len(data)} error={exc}",
                flush=True
            )
            continue

        timestamp = obj.get("timestamp")
        cell = obj.get("cell_metrics") or {}
        ue_list = obj.get("ue_list") or []

        if not ue_list:
            print(
                f"ts={timestamp} "
                f"dt_ms={dt_ms if dt_ms is not None else '-'} "
                f"ue=NONE "
                f"cell_avg_latency={cell.get('average_latency', '-')} "
                f"cell_errors={cell.get('error_indication_count', '-')}",
                flush=True
            )
            continue

        for entry in ue_list:
            ue = (entry or {}).get("ue_container") or {}

            print(
                f"ts={timestamp} "
                f"dt_ms={dt_ms if dt_ms is not None else '-'} "
                f"rnti={ue.get('rnti', '-')} "
                f"cqi={ue.get('cqi', '-')} "
                f"dl_mcs={ue.get('dl_mcs', '-')} "
                f"dl_brate={ue.get('dl_brate', '-')} "
                f"dl_bs={ue.get('dl_bs', '-')} "
                f"dl_ok={ue.get('dl_nof_ok', '-')} "
                f"dl_nok={ue.get('dl_nof_nok', '-')} "
                f"ul_mcs={ue.get('ul_mcs', '-')} "
                f"ul_brate={ue.get('ul_brate', '-')} "
                f"bsr={ue.get('bsr', '-')} "
                f"ul_ok={ue.get('ul_nof_ok', '-')} "
                f"ul_nok={ue.get('ul_nof_nok', '-')} "
                f"pusch_snr={ue.get('pusch_snr_db', '-')} "
                f"pucch_snr={ue.get('pucch_snr_db', '-')} "
                f"ta_ns={ue.get('ta_ns', '-')} "
                f"cell_avg_latency={cell.get('average_latency', '-')}",
                flush=True
            )

except KeyboardInterrupt:
    print("\nCOMPACT_METRICS_STOPPED=OK", flush=True)

finally:
    sock.close()
PY
