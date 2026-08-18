# TCD KPM read-only collector

This component is the project-owned FlexRIC KPM collector.

Implemented through COLLECTOR-01 Action 4A:

- internal owned-record model and lifecycle;
- atomic operational counters;
- bounded E2-node discovery;
- deterministic selection of exactly one E2 node;
- selection of exactly one matching KPM profile from the FlexRIC xApp
  configuration;
- KPM event-trigger and action-definition construction for action formats 1
  and 4;
- one read-only KPM report subscription through `report_sm_xapp_api`;
- KPM v3 indication handling for indication formats 1 and 3;
- defensive measurement-record/measurement-info length handling;
- copied node, UE, descriptor and value data with no retained FlexRIC
  callback pointers;
- bounded stop by indication count and/or duration;
- best-effort subscription removal through `rm_report_sm_xapp_api` on normal
  and failure paths;
- optional post-callback last-record diagnostics on standard error.

Not implemented:

- telemetry output adapters;
- reconnect/resubscribe handling;
- semantic KPM validation beyond the minimal structural status model;
- RAN control.

The component is strictly read-only. RAN control APIs are prohibited.

The source targets the validated FlexRIC configuration used by this project:
E2AP v2, KPM v3.00 and `XAPP_DB=NONE_XAPP`. A real FlexRIC build is deferred
from Action 4A to Action 4B.
