# Focused tests

COLLECTOR-01 Action 4A is source implementation only. It does not run a real
FlexRIC build or emulator.

The Action 4A controlled script performs source-level checks for:

- allowed-path confinement;
- whitespace correctness;
- presence of report_sm_xapp_api and rm_report_sm_xapp_api;
- absence of control_sm_xapp_api;
- absence of build/runtime execution.

One fresh validated FlexRIC build is reserved for Action 4B. One bounded
emulator runtime is reserved for Action 4C.

Focused malformed-input and record/lifecycle unit tests are introduced in
COLLECTOR-01 Action 5.
