#!/usr/bin/env bash

set -Eeuo pipefail

HOST="10.53.1.1"
PORT="55555"

exec python3 -u - "$HOST" "$PORT" <<'PY'
import socket
import sys
import time

host = sys.argv[1]
port = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((host, port))

print(f"UDP_RECEIVER_READY={host}:{port}", flush=True)

try:
    while True:
        data, addr = sock.recvfrom(65535)

        wall_ns = time.time_ns()
        mono_ns = time.monotonic_ns()

        print(
            f"WALL_NS={wall_ns} "
            f"MONO_NS={mono_ns} "
            f"SRC={addr[0]}:{addr[1]} "
            f"BYTES={len(data)} "
            f"DATA={data.decode('utf-8', errors='replace')}",
            flush=True
        )
except KeyboardInterrupt:
    print("\nUDP_RECEIVER_STOPPED=OK", flush=True)
finally:
    sock.close()
PY
