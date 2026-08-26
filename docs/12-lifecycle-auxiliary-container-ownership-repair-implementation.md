# Prompt 12 lifecycle auxiliary-container ownership repair implementation

## Status

Implementation status: **OFFLINE VALIDATED**

Canonical deployment status: **NOT STARTED**

Canonical Ansible syntax validation: **PENDING ON coll.vntu.org**

Fresh day-start: **NOT AUTHORISED**

## Scope

This record freezes the Git implementation candidate for the proven
`LIFECYCLE_AUXILIARY_CONTAINER_OWNERSHIP_GAP`.

Repository branch:

`feat/prompt12-siso-identification`

Parent HEAD:

`93090f1fc3e7cf0c96cd5885b5f716253aacde0d`

Affected source:

`ansible/playbooks/tb3-teardown.yml`

Pre-repair SHA256:

`2e52af6087502785554afac509578e84837f31b24fbf4f63e3d80e33340e4e36`

Offline-validated candidate SHA256:

`49c85c35989d78ccfdac1915938dde9cecdd5fa56b4f107bc423eb6b3c8ed476`

## Implemented ownership policy

The candidate implements the frozen explicit auxiliary namespace:

`^(action11_|action11r|prompt12[-_])[A-Za-z0-9][A-Za-z0-9_.-]*$`

It provides:

- explicit Action11, Action11 naming-drift and Prompt12 helper discovery;
- exact active-RIC exclusion from the auxiliary removal list;
- controlled BASE-05 network membership classification;
- fail-closed rejection of unknown network members;
- ownership evidence before the admission assertion;
- bounded pre-teardown logs;
- full `docker inspect` provenance before auxiliary removal;
- removal only from the explicit owned-helper list;
- final clean-state validation using the complete frozen ownership namespace.

Generic Docker cleanup remains prohibited.

## Fail-closed ordering

The implementation establishes the following ordering before destructive
helper cleanup:

1. resolve active RIC;
2. discover explicit auxiliary ownership candidates;
3. discover BASE-05 network members;
4. classify network members;
5. persist ownership classification evidence;
6. assert zero unknown members and active-RIC exclusion;
7. capture bounded logs;
8. persist auxiliary inspect provenance;
9. remove only explicitly owned auxiliary helpers.

Therefore a rejected ownership admission leaves classification evidence while
preventing destructive teardown from proceeding.

## Offline validation

The candidate passed on `tb3-dell`:

- YAML parser validation;
- frozen ownership regex fixtures;
- source contract validation;
- legacy Action11-only policy absence;
- destructive ordering validation;
- pre-admission non-destructive validation;
- fail-closed evidence validation;
- active RIC exclusion fixture;
- known-network admission fixture;
- unknown-network fail-closed fixture;
- Git diff integrity validation;
- validation non-mutation check.

`ansible-playbook` is not installed on `tb3-dell`.

Therefore native Ansible syntax validation is explicitly deferred and remains
mandatory on `coll.vntu.org` before any lifecycle execution using the repaired
source.

## Scientific boundary

No scientific control was part of this implementation or offline validation.

The preserved T2 R01 boundary remains:

- trigger write attempts: 0;
- trigger write successes: 0;
- scientific trigger consumed: NO;
- T2 scientific trigger count: 0.

Fresh day-start remains prohibited.

## Frozen design provenance

Design document:

`docs/12-lifecycle-auxiliary-container-ownership-repair-design.md`

SHA256:

`e46c9cf7ba63d8958a4d6e69d4809bec582b21a1782a70fbc21f1a32592c4406`

Design manifest:

`experiments/manifests/prompt12-lifecycle-auxiliary-container-ownership-repair-design-v1.0.0.json`

SHA256:

`1fb96f3a326c5c207d10e03c4704b6de3ffdeefadaaf48d79f07ed149d610ccb`

## External implementation evidence

`/home/khoshaba/sci-oran-evidence/prompt12/lifecycle-auxiliary-container-ownership-repair-implementation-v1`

`SHA256SUMS` SHA256:

`c127617880283cc7339c3edeb18a4b0ed7f4f809c98f5058abb845ab16652d6c`

The evidence contains:

- the exact candidate teardown source;
- the pre-commit Git diff;
- implementation/validation gates;
- SHA256 validation.

## Next authorised work

After this implementation checkpoint is committed and remotely checkpointed:

1. deploy only the exact validated lifecycle source to the separate canonical
   installation on `coll.vntu.org`;
2. verify exact SHA256 parity;
3. run native Ansible syntax validation on `coll.vntu.org`;
4. perform controlled lifecycle validation before fresh day-start.

Fresh T2 runtime acquisition remains **NOT AUTHORISED** at this checkpoint.
