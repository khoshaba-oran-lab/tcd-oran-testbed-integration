FROM ubuntu@sha256:3b06811b2afd352be909dd088a004166d665dc76d38b13eada33522a9d915c6f

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        iproute2 \
        iputils-ping \
        iperf3 \
        tcpdump \
        netcat-openbsd \
        socat \
        curl \
        jq \
        procps \
        psmisc \
        lsof \
        traceroute \
        ethtool \
        lksctp-tools \
        strace \
        dnsutils \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

LABEL io.sci-oran.image.role="diagnostic-toolbox"
LABEL io.sci-oran.diagnostic.contract="toolbox-v1"
LABEL io.sci-oran.base.reference="ubuntu:22.04"
LABEL io.sci-oran.base.digest="sha256:3b06811b2afd352be909dd088a004166d665dc76d38b13eada33522a9d915c6f"
LABEL io.sci-oran.base.registry-digest-status="resolved"

LABEL io.sci-oran.toolbox.network-namespace-mode="container:<target>"
LABEL io.sci-oran.toolbox.capability-policy="cap-drop-all-add-as-needed"
LABEL io.sci-oran.toolbox.packet-capture-capability="NET_RAW"
LABEL io.sci-oran.toolbox.network-admin-capability="NET_ADMIN"
LABEL io.sci-oran.toolbox.privileged-default="false"

CMD ["/bin/bash"]
