ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG PYARROW_VERSION=17.0.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/tcd-kpm

COPY tools/parquet/requirements.lock /tmp/requirements.lock
RUN python -m pip install \
        --no-cache-dir \
        --only-binary=:all: \
        --requirement /tmp/requirements.lock \
    && python -c "import pyarrow; assert pyarrow.__version__ == '${PYARROW_VERSION}'"

COPY docs/collector-03/canonical-record-emulator-draft-0.1.tsv \
    /opt/tcd-kpm/schema/canonical-record-emulator-draft-0.1.tsv
COPY docs/collector-03/canonical-record-emulator-draft-0.1.schema.json \
    /opt/tcd-kpm/schema/canonical-record-emulator-draft-0.1.schema.json
COPY tools/parquet/jsonl_to_parquet.py \
    /opt/tcd-kpm/bin/jsonl_to_parquet.py
COPY tests/test_parquet_converter.py \
    /opt/tcd-kpm/tests/test_parquet_converter.py

RUN chmod 0555 \
        /opt/tcd-kpm/bin/jsonl_to_parquet.py \
        /opt/tcd-kpm/tests/test_parquet_converter.py

LABEL org.opencontainers.image.title="TCD KPM JSONL to Parquet converter" \
      org.opencontainers.image.version="collector03-sw-prototype-emulator-draft-0.1" \
      org.opencontainers.image.description="Strict canonical tcd.kpm.record.emulator-draft-0.1 JSONL to typed Parquet converter"

ENTRYPOINT ["python", "/opt/tcd-kpm/bin/jsonl_to_parquet.py"]
