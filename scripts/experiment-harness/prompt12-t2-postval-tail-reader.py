#!/usr/bin/env python3
"""Read-only bounded tail verifier for T2-POSTVAL-v1.

No FIFO, scientific control, or lifecycle side effects.
Uses the production parser parse_interval() and verified raw line hashes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import time
from decimal import Decimal
from pathlib import Path

MAX_AGE_NS = 800_000_000
TAIL_BYTES = 32768


class GateError(Exception):
    pass


def check(test, reason):
    if not test:
        raise GateError(reason)


def _open_regular(path):
    path = Path(path)
    check(path.is_absolute(), 'NONABSOLUTE_PATH')
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        st = os.fstat(fd)
        check(stat.S_ISREG(st.st_mode), 'SOURCE_NOT_REGULAR')
        check(st.st_size > 0, 'SOURCE_EMPTY')
        return fd, st
    except (OSError, ValueError) as exc:
        raise GateError('SOURCE_UNAVAILABLE') from exc


def _timestamp_tail(fd, st):
    size = min(st.st_size, TAIL_BYTES)
    buf = os.pread(fd, size, st.st_size - size)
    check(buf.endswith(b'\n'), 'TIMESTAMP_UNFINISHED_LAST_LINE')
    if st.st_size > size:
        offset = buf.find(b'\n')
        check(offset >= 0, 'TIMESTAMP_TAIL_NO_BOUNDARY')
        buf = buf[offset + 1:]
    rows = []
    for raw in buf.splitlines():
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GateError('TIMESTAMP_BAD_JSON') from exc
        check(isinstance(obj, dict), 'TIMESTAMP_NOT_OBJECT')
        rows.append((obj, raw))
    check(len(rows) >= 2, 'TIMESTAMP_TAIL_TOO_SHORT')
    return rows


def _load_parser(parser_path):
    parser_path = Path(parser_path)
    check(parser_path.is_absolute(), 'PARSER_PATH_NOT_ABSOLUTE')
    check(parser_path.is_file() and not parser_path.is_symlink(), 'PARSER_NOT_REGULAR')
    spec = importlib.util.spec_from_file_location('sci_oran_verified_interval_parser', parser_path)
    check(spec is not None and spec.loader is not None, 'PARSER_IMPORT_FAILED')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    check(callable(getattr(module, 'parse_interval', None)), 'PARSER_NO_INTERVAL_API')
    return module.parse_interval, hashlib.sha256(parser_path.read_bytes()).hexdigest()


def inspect(raw_path, timestamp_path, parser_path, *, _test_clock_ns=None):
    parse_interval, parser_sha = _load_parser(parser_path)
    raw_fd, raw_st = _open_regular(raw_path)
    try:
        ts_fd, ts_st = _open_regular(timestamp_path)
        try:
            rows = _timestamp_tail(ts_fd, ts_st)
            intervals = []
            last_sequence = last_wall = last_mono = last_end = None
            for item, raw_stamp in rows:
                check(item.get('schema') == 'sci_oran_iperf_receiver_line_capture_v1',
                      'TIMESTAMP_SCHEMA_MISMATCH')
                try:
                    sequence = item['sequence']
                    start = item['raw_offset_start']
                    end = item['raw_offset_end']
                    wall = item['rx_wall_ns']
                    mono = item['rx_mono_ns']
                    encoded_line = item['line_utf8']
                    line_size = item['raw_line_length_bytes']
                    claimed_sha = item['raw_line_sha256']
                except KeyError as exc:
                    raise GateError('TIMESTAMP_REQUIRED_FIELD_MISSING') from exc
                check(all(type(value) is int for value in
                          (sequence, start, end, wall, mono, line_size)),
                      'TIMESTAMP_FIELD_TYPE_INVALID')
                check(0 <= start < end <= raw_st.st_size and end - start == line_size,
                      'RAW_OFFSET_INVALID')
                check(wall > 0 and mono > 0, 'TIMESTAMP_NOT_POSITIVE')
                if last_sequence is not None:
                    check(sequence == last_sequence + 1, 'SEQUENCE_GAP')
                    check(start == last_end, 'RAW_OFFSET_GAP')
                    check(wall >= last_wall and mono > last_mono, 'TIMESTAMP_ORDER_INVALID')
                line_bytes = os.pread(raw_fd, end - start, start)
                check(len(line_bytes) == end - start, 'RAW_SHORT_READ')
                check(hashlib.sha256(line_bytes).hexdigest() == claimed_sha,
                      'RAW_LINE_SHA_MISMATCH')
                check(line_bytes.decode('utf-8', errors='replace').rstrip('\r\n') == encoded_line,
                      'RAW_LINE_TEXT_MISMATCH')
                parsed = parse_interval(encoded_line)
                if parsed is not None:
                    check(parsed['interval_shape'] == 'complete_0p2',
                          'LATEST_INTERVAL_NOT_COMPLETE')
                    check(Decimal(str(parsed['interval_duration_s'])) == Decimal('0.2'),
                          'SAMPLE_DURATION_INVALID')
                    # Match production canonicalizer's startup_guard rule.
                    # A valid 0.2s interval ending <=1s is not eligible,
                    # but does not invalidate subsequent prephase samples.
                    if Decimal(str(parsed['interval_end_s'])) > Decimal('1.000001'):
                        intervals.append((sequence, wall, mono, parsed, claimed_sha))
                last_sequence, last_wall, last_mono, last_end = sequence, wall, mono, end
            check(len(intervals) >= 2, 'COMPLETE_PAIR_UNAVAILABLE')
            a, b = intervals[-2:]
            check(Decimal(str(a[3]['interval_end_s'])) ==
                  Decimal(str(b[3]['interval_start_s'])), 'COMPLETE_PAIR_NOT_CONTIGUOUS')
            check(Decimal(str(b[3]['interval_end_s'])) >= Decimal('26'),
                  'PREPHASE_UNDER_26_SECONDS')
            # Historical tests can inject a clock through the private API;
            # production admission always calls without _test_clock_ns.
            decision_ns = time.time_ns() if _test_clock_ns is None else _test_clock_ns
            age_ns = decision_ns - b[1]
            check(0 <= age_ns <= MAX_AGE_NS, 'SAMPLE_AGE_OUT_OF_BOUNDS')
            # A true runtime implementation would need an *independent* final
            # age check immediately before the one authorized FIFO write.
            return {
                'GATE': 'PASS', 'scientific_trigger_enabled': False,
                'source': 'verified_raw_line_capture_tail',
                'selection': 'last_two_contiguous_complete_intervals',
                'last_sequence': b[0], 'latest_sample_timestamp_utc_ns': b[1],
                'latest_sample_rx_mono_ns': b[2],
                'latest_interval_end_s': b[3]['interval_end_s'],
                'sample_age_ms': age_ns / 1e6,
                'raw_line_sha256': b[4], 'production_parser_sha256': parser_sha,
            }
        finally:
            os.close(ts_fd)
    finally:
        os.close(raw_fd)
