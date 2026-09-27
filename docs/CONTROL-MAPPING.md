# Illustrative control mapping

**Not an authorization, FedRAMP assessment, certification, or assertion of compliance.**
The system compliance owner must validate applicability, implementation details,
control enhancements, organizational responsibilities, and FedRAMP High parameters.

Reference: [NIST SP 800-53 Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final).
The demo does not implement the full FedRAMP High baseline.

| Control | Illustrative implementation | Evidence / limitation |
|---|---|---|
| CM-3 Configuration Change Control | Spec/task trace, required checks, human review | PR, check and approval snapshots; bootstrap bypass logged as rule suite 4243669608 |
| CM-5 Access Restrictions for Change | Protected main/tags, agent path allowlist (src/, tests/, specs/), PR gates executed from the default branch | Active ruleset JSON; independent ownership needed |
| AC-5 Separation of Duties | Codeowner review and production self-review prevention | A solo account does not meet independent duty separation |
| SA-11 Developer Testing and Evaluation | Tests, coverage threshold, CodeQL, dependency review | JUnit, coverage, SARIF, check results |
| SA-15 Development Process, Standards, and Tools | Constitution, pinned tools, Spec Kit, bounded agents | Versioned configuration and build log |
| RA-5 Vulnerability Monitoring and Scanning | CodeQL and dependency scanning | Findings and remediation history, not just workflow files |
| SI-2 Flaw Remediation | Dependabot updates and reviewed fixes | Alert remediation durations and merged PRs |
| SI-7 Software, Firmware, and Information Integrity | Verified provenance and artifact hashes | Native verification output; local checksums alone are insufficient |
| SR-4 Provenance | Source-bound build and SPDX attestations | Signed provenance, lockfile inventory limitations disclosed |
| AU-2 Event Logging | Selected agent lifecycle/tool events | Argument hashes, no raw prompts or PII |
| AU-12 Audit Record Generation | JSONL hooks, PR evidence, release ZIP | Local logs are not immutable centralized audit storage |

Section 508 is an accessibility lens, not satisfied by a control table. The dashboard
provides semantic HTML and text chart equivalents; independent keyboard/screen-reader
testing remains necessary.
