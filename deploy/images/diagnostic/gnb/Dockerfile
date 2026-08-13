FROM sci-oran/gnb:action11.226-plmnfix-sandybridge

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        iproute2 \
        iputils-ping \
        iperf3 \
        procps \
        psmisc \
        lsof \
        curl \
        jq \
        netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

LABEL io.sci-oran.image.role="gnb-diagnostic"
LABEL io.sci-oran.diagnostic.contract="gnb-diag-v1"

LABEL io.sci-oran.base.reference="sci-oran/gnb:action11.226-plmnfix-sandybridge"
LABEL io.sci-oran.base.local-image-id="sha256:aac094264803c663fd714af28840aa9db10d323526c5e0ca6cbc22645022c292"
LABEL io.sci-oran.base.gnb-sha256="e5615cb2400aebda43f68bf8b6c756449442e02e6940a0b91ed59bd9a928aa90"
LABEL io.sci-oran.base.provenance-mode="validated-local-image-id"
LABEL io.sci-oran.base.registry-digest-status="not-yet-published"

LABEL io.sci-oran.diagnostic.extended-tools="toolbox"
