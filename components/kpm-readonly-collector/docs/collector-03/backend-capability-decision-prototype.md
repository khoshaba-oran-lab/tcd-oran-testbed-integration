# COLLECTOR-03 software prototype backend capability decision

> **Status:** Software prototype only. The canonical record is derived from emulator evidence, is not frozen, and is not an accepted schema v1. REAL-GATE-01 and REAL-GATE-02 remain pending.

## Controlled-start observation

The controlled-start inventory found the following relevant host state:

- C compiler and `pkg-config`: present;
- Python 3 and Docker: present;
- host CMake: absent;
- Arrow and Parquet `pkg-config` packages: absent;
- libmicrohttpd: absent;
- PyArrow, pandas, and prometheus-client: absent.

No dependency was installed during controlled start.

## Decision

The implementation will preserve a small collector runtime:

| Backend | COLLECTOR-03 implementation | External runtime dependency |
|---|---|---|
| CSV | native C streaming serializer and file sink | none |
| JSONL | native C streaming serializer and file sink | none |
| Prometheus | native C atomic textfile exposition | none |
| Parquet | separate pinned offline conversion tool image | pinned PyArrow inside tool image |

## Rationale

Linking Arrow/Parquet or an HTTP server into the collector would enlarge the
runtime and build surface while the host currently provides none of those
libraries. A canonical JSONL stream plus a pinned conversion image gives typed
Parquet output without introducing compression or columnar-writing work into
the callback or collector lifecycle.

The Prometheus textfile contract avoids an embedded web server and avoids
unbounded label cardinality. It remains directly consumable by standard
textfile collection or a separate HTTP publishing component.

## Gate for implementation

Implementation may start only after:

1. canonical schema and backend contract files pass machine validation;
2. the COLLECTOR-02A-SW baseline manifest remains unchanged;
3. the dedicated COLLECTOR-03 branch is created from the COLLECTOR-02A-SW software-only baseline
   commit;
4. no source or deployment file outside the new COLLECTOR-03 documentation
   directory is changed in Action 1.
