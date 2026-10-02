# Sci-O-RAN Ansible controller contract

This directory is the provisional canonical repository source for Sci-O-RAN
bundle transfer and Tb3 lifecycle playbooks.

## Roles

- The controller is an external host with this repository and Ansible.
- `tb3-dell` is the managed virtual machine.
- Lifecycle playbooks must not be started from `tb3-dell`.
- The exact controller host must pass a separate qualification action.

## Repository source

Run the repository compatibility wrapper:

```text
scripts/tb3-lifecycle.sh
```

This top-level script is a compatibility proxy only. It delegates all
arguments to `sci-oran/ansible/lifecycle/bin/tb3-lifecycle.sh`, which is
the canonical lifecycle mutation authority. The top-level compatibility
proxy must not invoke `ansible-playbook`, generate lifecycle operation
identities, or implement state-changing lifecycle logic independently.


It resolves the default Ansible root relative to the repository. An alternative
installation may set `SCI_ORAN_ANSIBLE_ROOT`.

## Inventory

`inventory.ini` is controller-local and intentionally ignored by Git. Create it
from `inventory.ini.example` and replace both `CHANGE_ME` values. Do not commit
addresses, credentials, private keys, passwords or tokens.

The required inventory group is `sci_oran_vms`. It may contain one or more compatible experimental VMs. Host identity is supplied through inventory variables, with `tb3-dell` remaining the currently validated runtime target.

An inventory outside this directory may be selected with
`SCI_ORAN_INVENTORY=/absolute/path/to/inventory.ini`.

## Controller result staging

Fetched bundle results default to `$HOME/sci-oran/staging` on the controller.
Set `SCI_ORAN_STAGING_DIR` to select another controller-local directory.

## Safety boundary

## R6-C centralized multi-VM operator contract

The authoritative Ansible source tree is the tracked repository tree:

`/home/khoshaba/project/tcd-oran-testbed-integration/sci-oran/ansible`

The controller-local `inventory.ini` remains intentionally untracked.
`inventory.ini.example` is the tracked template.

Managed experimental VMs belong to the `sci_oran_vms` inventory group.
Host-specific identity and repository settings are supplied through
`host_vars/<inventory-host>.yml`; group-wide settings are supplied through
`group_vars/sci_oran_vms.yml`.

Every state-changing lifecycle operation must name exactly one target:

`lifecycle/bin/tb3-lifecycle.sh <operation> --target <inventory-host> --confirm`

For example:

`lifecycle/bin/tb3-lifecycle.sh day-stop --target tb3-dell --confirm`

The wrapper validates that the selected target belongs to `sci_oran_vms` and
passes the target to Ansible with `--limit <inventory-host>`. Omitting the
target or selecting an unknown target fails closed.

The controlled day-start interface follows the same rule:

`lifecycle/bin/tb3-controlled-day-start.sh --preflight --target <inventory-host>`

and, only with separate execution authorisation:

`lifecycle/bin/tb3-controlled-day-start.sh --execute --target <inventory-host>`

`tb3-controlled-day-start.sh` is retained as an R5 compatibility facade.
Its `--preflight` mode remains read-only. Its state-changing `--execute`
mode delegates to `lifecycle/bin/tb3-lifecycle.sh day-start` and must not
invoke `ansible-playbook` directly.


An implicit state-changing operation against all hosts in `sci_oran_vms` is
forbidden.

`tb3-dell` is the currently validated runtime VM. Additional compatible VMs
must be introduced through inventory and host-specific variables rather than
through independent lifecycle source trees or manual edits to common
playbooks.
