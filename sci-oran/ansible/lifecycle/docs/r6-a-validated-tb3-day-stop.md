# Recovery R6-A: Validated Tb3 Day-Stop

STATUS=PASS
DATE=2026-09-29
CONTROLLER=coll.vntu.org
RUNTIME_HOST=tb3-dell

CANONICAL_WRAPPER=/home/khoshaba/sci-oran/ansible/lifecycle/bin/tb3-lifecycle.sh
CANONICAL_COMMAND=tb3-lifecycle.sh day-stop --confirm

SUCCESSFUL_DAY_STOP_ID=lifecycle-day-stop-20260929T160154Z-e5eb6e69
SUCCESSFUL_TEARDOWN_ID=lifecycle-teardown-20260929T160154Z-e5eb6e69

DAY_STOP_RUNTIME_CAPTURE_GATE=PASS
DAY_STOP_EVIDENCE_GATE=PASS
DAY_STOP_TEARDOWN_GATE=PASS
DAY_STOP_CLEAN_STATE_GATE=PASS
DAY_STOP_GATE=PASS

ANSIBLE_OK=143
ANSIBLE_CHANGED=21
ANSIBLE_UNREACHABLE=0
ANSIBLE_FAILED=0
ANSIBLE_SKIPPED=1
ANSIBLE_RESCUED=0
ANSIBLE_IGNORED=0

Validated repair:
1. tb3-preflight.yml expected branch changed from
   feat/prompt12-siso-identification
   to
   main.

2. tb3-day-stop.yml now imports tb3-preflight.yml before
   any day-stop evidence mutation.

Required ordering:
READ_ONLY_PRECONDITIONS -> PASS -> MUTATION

Qualified source identities:
tb3-preflight.yml SHA256=1199d41a12da0d65c9a966f81a2208531f26e3bcf7a4f13e4ccfae69aa6fb37b
tb3-day-stop.yml SHA256=cf96425c3f3a67959f8ed41709d61fa3ae25072e1ab050fd570815858259f6f4

Consumed failed operation - NEVER REPLAY:
lifecycle-day-stop-20260927T165207Z-8652a4a7

Future normal shutdown rule:
- run from coll.vntu.org;
- use the canonical lifecycle wrapper;
- use C.utf8 locale;
- always use a fresh operation ID;
- require DAY_STOP_GATE=PASS;
- require failed=0 and unreachable=0;
- do not use manual docker stop/down for normal shutdown;
- do not repeat R6-A forensic investigation unless the validated
  lifecycle procedure itself produces a new failure.

Scientific traffic, PRB control and Prompt-12 T1-T6 are not authorised
by this lifecycle result.

R6_A=PASS
TARGET_STATE=O_RAN_RUNTIME_STOPPED
NEXT_WORKSTREAM=R6-B_SINGLE_SOURCE_OF_TRUTH
