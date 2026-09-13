# Sci-O-RAN Ansible controller contract

This directory is the provisional canonical repository source for Sci-O-RAN
bundle transfer and Tb3 lifecycle playbooks.

## Roles

- The controller is an external host with this repository and Ansible.
- `tb3-dell` is the managed virtual machine.
- Lifecycle playbooks must not be started from `tb3-dell`.
- The exact controller host must pass a separate qualification action.

## Repository source

Run the repository wrapper:

```text
scripts/tb3-lifecycle.sh
```

It resolves the default Ansible root relative to the repository. An alternative
installation may set `SCI_ORAN_ANSIBLE_ROOT`.

## Inventory

`inventory.ini` is controller-local and intentionally ignored by Git. Create it
from `inventory.ini.example` and replace both `CHANGE_ME` values. Do not commit
addresses, credentials, private keys, passwords or tokens.

The required inventory group is `sci_oran_vms`. Its required inventory hostname
is `tb3-dell`, matching the fail-closed preflight contract.

An inventory outside this directory may be selected with
`SCI_ORAN_INVENTORY=/absolute/path/to/inventory.ini`.

## Controller result staging

Fetched bundle results default to `$HOME/sci-oran/staging` on the controller.
Set `SCI_ORAN_STAGING_DIR` to select another controller-local directory.

## Safety boundary
