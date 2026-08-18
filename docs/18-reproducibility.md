# Sci_O-RAN Software and Docker Reproducibility

## 1. Purpose

This document records the software and container environment used for the
Sci_O-RAN Tb3 Base05 baseline and defines the reproducibility policy for the
associated Docker images.

The machine-readable inventories are maintained in:

- `manifests/software.yaml`
- `manifests/docker-images.yaml`

This phase documents the observed environment and identifies Docker images that
should be preserved. No Docker Hub push is performed as part of this inventory
phase.

## 2. Host environment

The inventory was collected on host `tb3-dell`.

Observed host environment:

- OS: Ubuntu 24.04.4 LTS (Noble Numbat)
- kernel: Linux 6.8.0-137-generic
- architecture: x86_64
- Docker: 29.7.2, build a7dcaa6
- Docker Compose: v5.4.0
- Git branch: `feat/tb3-dell-reproducibility`
- baseline Git commit:
  `7258aa21956fdee3cc66117f7ea6b11535ce5e05`

The detailed values are stored in `manifests/software.yaml`.

## 3. Docker Compose runtime

The active Compose project is:

`tcd-base05-zmq`

The runtime working directory is:

`deploy/phase-1-baseline/base-05-zmq`

The project is instantiated from the following Compose files:

1. `deploy/phase-1-baseline/base-05-zmq/compose.runtime.yml`
2. `deploy/phase-1-baseline/base-05-zmq/compose.sandybridge.yml`

Their SHA256 hashes are recorded in `manifests/software.yaml`.

## 4. Runtime containers

The Base05 runtime consists of three containers:

| Container | Service | Role |
|---|---|---|
| `base05_open5gs_5gc` | `5gc` | Open5GS 5G Core |
| `base05_srsran_gnb` | `gnb` | srsRAN gNB ZeroMQ |
| `base05_srsran_srsue` | `srsue` | srsUE ZeroMQ |

Each container is mapped to an immutable Docker image ID and registry digest in
`manifests/software.yaml`.

The current runtime images are all `linux/amd64`.

## 5. Runtime configuration files

The gNB configuration is bind-mounted read-only from:

`deploy/phase-1-baseline/base-05-zmq/configs/gnb_zmq_base05.yaml`

SHA256:

`ba211c4b5b600a77869560981469302d17c57440ab9898ea61ff84d14780c17d`

The srsUE configuration is bind-mounted read-only from:

`deploy/phase-1-baseline/base-05-zmq/configs/ue_zmq_base05.conf`

SHA256:

`ceab877f0f8105966ee89f910a98ee51158550a8503e7a6eea6e41fc8ce1e47e`

The Open5GS container has no host bind mounts in the observed runtime.

## 6. Docker image inventory

Seven unique local Docker images were identified during the inventory.

The complete mapping between:

- image IDs;
- repository tags;
- observed RepoDigests;
- architecture;
- creation time;
- image role;
- Dockerfile provenance;
- Docker Hub preservation decision;

is stored in `manifests/docker-images.yaml`.

The `hello-world` image is treated only as a Docker smoke-test dependency and is
not part of the Sci_O-RAN runtime.

## 7. Current Base05 runtime images

### 7.1 Open5GS

Current immutable image ID:

`sha256:e584550ebb654abcce8801c479d977f97b0397319e5dd92c1e06b7091d92160d`

Local archival tag:

`khoshaba/tb3-base05-artifacts:open5gs-v2.7.0-e584550e`

The application version `2.7.0` is inferred from the local image tag.

A repository Dockerfile and exact build procedure for this image were not
established during the inventory phase. Consequently, this image must currently
be treated as an archival reproducibility artifact.

### 7.2 srsRAN gNB

Current immutable image ID:

`sha256:7e3a3c4d9e4a46d1e2bf566420e714f8f69f27fa0239a066330c59f0384d6319`

Archival tag:

`khoshaba/tb3-base05-artifacts:gnb-zmq-24.10.0-9d5dd742-sandybridge-v1`

Relevant source revision:

`9d5dd742a70e82c0813c34f57982f9507f1b6d5d`

CPU profile:

`sandybridge-avx-no-avx2-no-fma`

Relevant Dockerfile:

`deploy/phase-1-baseline/base-05-zmq/docker/sandybridge/Dockerfile.gnb`

The image metadata explicitly records:

`release-24.10-not-historical-commit-exact`

Therefore this image should be preserved even though a Dockerfile exists,
because the exact historical source equivalence is qualified rather than fully
established.

### 7.3 srsUE

Current immutable image ID:

`sha256:ea98a2ab87f98037bc172f8422dc1f5fc65ebad21f847bc10b5765b9ecf02410`

Archival tag:

`khoshaba/tb3-base05-artifacts:srsue-zmq-23.11-eea87b1d893a-sandybridge-v2`

Source revision:

`eea87b1d893ae58e0b08bc381730c502024ae71f`

CPU profile:

`sandybridge-avx-no-avx2-no-fma-v2`

Relevant Dockerfile:

`deploy/phase-1-baseline/base-05-zmq/docker/sandybridge/Dockerfile.srsue`

This Dockerfile depends on the immutable base image:

`sha256:b02c44dda074a512a916eb526e78ee895867fa5798adde2e3673935c1edcf622`

Therefore both the final Sandy Bridge srsUE image and its immutable build
dependency should be preserved.

## 8. Docker Hub preservation policy

Docker images must not be reproduced primarily through `docker commit` when a
Dockerfile and controlled build procedure can be used.

The preferred reproducibility chain is:

`Git commit -> Dockerfile -> pinned source/base image -> build procedure -> image digest`

However, an immutable image should also be preserved when:

1. the exact build procedure is not fully established;
2. historical source equivalence is uncertain;
3. the image is an immutable dependency required to reproduce another image;
4. it represents the exact experimentally validated runtime baseline.

Based on the current inventory, the required Docker Hub preservation candidates
are:

1. `khoshaba/tb3-base05-artifacts:open5gs-v2.7.0-e584550e`
2. `khoshaba/tb3-base05-artifacts:gnb-zmq-24.10.0-9d5dd742-sandybridge-v1`
3. `khoshaba/tb3-base05-artifacts:srsue-zmq-23.11-eea87b1d893a-sandybridge-v2`
4. `khoshaba/tb3-base05-artifacts:srsue-zmq-23.11-eea87b1d893a`

No Docker Hub push is authorized by this document.

Any future publication action must explicitly verify:

- Docker Hub repository;
- final tag;
- local image ID;
- resulting remote digest;
- Dockerfile;
- base image;
- exact build command;
- Git commit associated with the build.

## 9. Images excluded from the current baseline

The following images are not required for the current validated Base05 runtime:

- `khoshaba/tb3-base05-artifacts:gnb-zmq-24.10.0-eca587d0597a-v2`
- `srsran/srsue-zmq:23.11-eea87b1d893a-sandybridge`
- `hello-world:latest`

They remain part of the local inventory but are not current baseline
publication candidates.

## 10. Reproducibility status

The software environment, runtime containers, immutable image IDs, image
digests, platform information, Compose configuration, and relevant
configuration-file hashes have been inventoried.

The remaining Docker publication operation is intentionally separated from this
inventory phase. No image should be pushed until an explicit publication Action
is approved.

The authoritative machine-readable records for this phase are:

- `manifests/software.yaml`
- `manifests/docker-images.yaml`
