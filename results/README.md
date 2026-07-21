# Experiment Results

This directory stores only small, reviewed and sanitised result summaries.

Do not commit:

- raw PCAP or PCAPNG files;
- large CSV, JSONL or Parquet datasets;
- internal IP addresses;
- subscriber identifiers;
- SIM/USIM credentials;
- authentication material;
- unpublished testbed configuration;
- unrestricted application or network logs.

A committed result should normally contain:

- experiment identifier;
- upstream commit;
- integration-repository commit;
- container image versions;
- sanitised configuration summary;
- pass/fail verdict;
- hashes or references to externally stored artifacts.
