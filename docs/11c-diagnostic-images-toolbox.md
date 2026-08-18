# Sci_O-RAN Prompt 11C — Diagnostic Images, Toolbox and Image Locks

## 1. Purpose

Prompt 11C defines a reproducible diagnostic-instrumentation architecture
for the Sci_O-RAN Tb3 testbed.

The primary objective is to provide network and system diagnostic tools
without performing ad-hoc package installation inside validated runtime
containers.

Permanent diagnostic changes are introduced only through version-controlled
Dockerfiles and explicitly versioned images.

The general rule is:

    validated application image
        +
    minimal native diagnostics where justified
        +
    standalone Toolbox for extended diagnostics

Commands such as:

    docker exec <container> apt install ...

are not considered part of the reproducible Sci_O-RAN workflow.

## 2. Selected component strategy

The final Prompt 11C diagnostic strategy is:

| Component | Diagnostic strategy | Separate diagnostic image |
|---|---|---|
| gNB | lightweight derived image plus Toolbox | yes |
| UE | native basic tools plus Toolbox | no |
| 5GC | native basic tools plus Toolbox | no |
| Near-RT RIC | Toolbox-first | no |

The machine-readable policy is stored in:

    deploy/images/diagnostic/diagnostic-policy.json

The canonical local image lock is stored in:

    deploy/images/diagnostic/images.lock.json

## 3. gNB diagnostic derived image

Validated application base:

    sci-oran/gnb:action11.226-plmnfix-sandybridge

Validated base local image ID:

    sha256:aac094264803c663fd714af28840aa9db10d323526c5e0ca6cbc22645022c292

Diagnostic derived image:

    sci-oran/gnb:action11.226-plmnfix-sandybridge-diag-v1

Validated diagnostic local image ID:

    sha256:997a6280c7e4aa3db81c9e83181f8efe88901849bc9d1339e2393a6f840c9408

Validated gNB application binary SHA-256:

    e5615cb2400aebda43f68bf8b6c756449442e02e6940a0b91ed59bd9a928aa90

The derived image adds lightweight diagnostic utilities while preserving the
validated gNB application stack.

Validated equivalence includes:

- gNB binary identity;
- runtime image configuration;
- Sandy Bridge CPU profile;
- dynamic library linkage;
- command-line runtime behaviour.

Full normal Tb3 startup validation with this diagnostic image is intentionally
deferred to the Prompt 11A and Prompt 11B integration stage.

Image-size evidence:

    base_bytes       = 127139809
    diagnostic_bytes = 131095086
    delta_bytes      = 3955277

## 4. Standalone Toolbox v1

Toolbox image:

    sci-oran/toolbox:v1

Validated local image ID:

    sha256:2f60d32db88bb07cfc8af06830fe5e25b3183c107591ce5044e1711eb28b0adb

Immutable Ubuntu base:

    ubuntu@sha256:3b06811b2afd352be909dd088a004166d665dc76d38b13eada33522a9d915c6f

The Toolbox contract contains 22 diagnostic commands:

    ip
    ss
    tc
    ping
    iperf3
    tcpdump
    nc
    socat
    curl
    jq
    ps
    pgrep
    fuser
    pstree
    lsof
    traceroute
    ethtool
    sctp_darn
    sctp_status
    strace
    dig
    nslookup

Image-size evidence:

    ubuntu_base_bytes = 29745680
    toolbox_bytes     = 54186896
    delta_bytes       = 24441216

## 5. Toolbox network-namespace model

The principal network diagnostic mechanism is:

    docker run --rm \
        --network container:<target-container> \
        --cap-drop ALL \
        sci-oran/toolbox:v1 \
        ss -lntu

Prompt 11C experimentally validated that the Toolbox can enter the network
namespace of another running container.

The validation demonstrated:

- identical network namespace identifier;
- identical container IP address;
- visibility of interfaces;
- visibility of routes;
- visibility of listening sockets;
- successful local TCP reachability testing.

The target container was not modified.

Passive network inspection succeeded with zero effective Linux capabilities.

Validated gate:

    TOOLBOX_NETWORK_NAMESPACE_GATE=PASS

## 6. Linux capability policy

The Toolbox follows a least-privilege model.

### Passive diagnostics

Default:

    --cap-drop ALL

This mode is validated for passive inspection of:

- interfaces;
- addresses;
- routes;
- listening sockets;
- TCP reachability.

### ICMP diagnostics

Ping requires:

    --cap-drop ALL --cap-add NET_RAW

This requirement was experimentally confirmed during Prompt 11C.

### Packet capture

Initial packet-capture policy:

    --cap-drop ALL --cap-add NET_RAW

NET_ADMIN may be added only when a specific capture operation demonstrably
requires it.

### Network administration

Operations that modify network state, including applicable tc operations,
may temporarily require:

    NET_ADMIN

### Prohibited defaults

The diagnostic architecture does not grant by default:

    NET_RAW
    NET_ADMIN
    SYS_ADMIN
    --privileged

No permanent capability escalation is embedded into the diagnostic images.

## 7. UE diagnostic decision

Validated UE image:

    khoshaba/tb3-base05-artifacts:srsue-zmq-23.11-eea87b1d893a-sandybridge-v2

Validated local image ID:

    sha256:ea98a2ab87f98037bc172f8422dc1f5fc65ebad21f847bc10b5765b9ecf02410

Native basic diagnostic commands confirmed:

    ip
    ss
    tc
    ping
    ps
    pgrep

Decision:

    UE_DERIVED_DIAGNOSTIC_IMAGE_REQUIRED=NO

Extended UE diagnostics are delegated to Toolbox.

## 8. 5GC diagnostic decision

Validated Open5GS image:

    tcd-oran/base05-open5gs:v2.7.0-e584550e

Validated local image ID:

    sha256:e584550ebb654abcce8801c479d977f97b0397319e5dd92c1e06b7091d92160d

Native diagnostic commands confirmed:

    ip
    ss
    tc
    ping
    ps
    pgrep
    iperf3
    curl
    nc

Decision:

    5GC_DERIVED_DIAGNOSTIC_IMAGE_REQUIRED=NO

Extended 5GC diagnostics are delegated to Toolbox.

## 9. Near-RT RIC diagnostic decision

Canonical Prompt 11 RIC runtime image:

    tcd-oran/flexric-action11:e2ap-v3-live-probe

Validated local image ID:

    sha256:02a7181afaf1cb5892bbaaaeb3808e9db9bcb7594fa48396e3da56e210bc60bb

Native process diagnostics confirmed:

    ps
    pgrep

The image does not contain the basic network commands:

    ip
    ss
    tc
    ping

A separate RIC diagnostic derived image is intentionally not created.

Decision:

    RIC_DERIVED_DIAGNOSTIC_IMAGE_REQUIRED=NO
    RIC_DIAGNOSTIC_STRATEGY=TOOLBOX_FIRST

The validated Toolbox network-namespace mechanism provides the required
network visibility without modifying the RIC runtime image.

## 10. Image provenance

Prompt 11C distinguishes three different concepts:

1. image tag;
2. local immutable image ID;
3. remote registry digest.

These values must not be treated as interchangeable.

For the gNB diagnostic base, provenance currently relies on the exact validated
local image ID because the parent image is not yet represented by a verified
remote registry digest.

The Toolbox Ubuntu base is stronger: it is directly pinned by an immutable
registry digest.

## 11. Publication state

At this stage:

    gNB diagnostic image = local-only-unpublished
    Toolbox image        = local-only-unpublished

A Docker RepoDigest observed locally is not accepted as proof of Docker Hub
publication.

Therefore the canonical image lock currently records:

    registry_digest = null

for both new Sci-O-RAN diagnostic images.

If Docker Hub publication is authorized later, the required sequence is:

1. validate the local image;
2. select the final repository and version tag;
3. push the image;
4. verify the remote image independently;
5. capture the real remote registry digest;
6. update images.lock.json;
7. commit the updated lock.

Unvalidated images must not be published.

## 12. Update policy

Diagnostic images must preserve the application stack.

A diagnostic rebuild must not silently update:

- srsRAN application binaries;
- Open5GS application binaries;
- FlexRIC application binaries;
- application runtime libraries;
- CPU compatibility profile.

The intended rule is:

    same validated application stack
        +
    explicitly defined diagnostic utilities

A change to the application stack requires separate validation and must not be
hidden inside a diagnostic image rebuild.

## 13. Naming and versioning

Current diagnostic image names are:

    sci-oran/gnb:action11.226-plmnfix-sandybridge-diag-v1
    sci-oran/toolbox:v1

The suffix or version must change when the diagnostic contract changes.

Image identity for reproducible execution must ultimately rely on an immutable
digest or, while local-only, on the validated local image ID recorded in the
canonical lock.

## 14. Integration boundary

Prompt 11C does not execute the Runtime Actuation Gate.

Prompt 11 remains:

    PAUSED_AT_ACTUATION_GATE

The diagnostic artifacts produced by Prompt 11C are intended for later
integration with:

- Prompt 11A — reproducible lifecycle automation;
- Prompt 11B — comprehensive read-only doctor;
- SCI_ORAN_READY_GATE.

Full normal gNB testbed integration with the diagnostic image remains:

    PENDING_11A_11B

This prevents Prompt 11C from duplicating lifecycle and readiness validation
that belongs to Prompts 11A and 11B.

## 15. Reproducibility artifacts

Prompt 11C currently produces the following version-controlled artifacts:

    deploy/images/diagnostic/gnb/Dockerfile
    deploy/images/diagnostic/toolbox/Dockerfile
    deploy/images/diagnostic/diagnostic-policy.json
    deploy/images/diagnostic/images.lock.json
    docs/11c-diagnostic-images-toolbox.md

Together they define:

- diagnostic image construction;
- Toolbox construction;
- component-specific diagnostic strategy;
- least-privilege capability policy;
- image identities and provenance;
- image-size evidence;
- publication state;
- future Prompt 11A/11B integration contract.
