# Aergia CV Builder — Tracker

File-based project knowledge graph maintained with the `tracker` CLI
(project-tracker, SCHEMA 3). Every entry is a Markdown file with YAML
frontmatter; `tracker rebuild` generates `graph.json`, and `tracker validate`
checks schema integrity.

## Summary

| Folder | Type | Total |
|--------|------|-------|
| [bugs/](bugs/) | bug | 9 |
| [features/](features/) | feature | 29 |
| [decisions/](decisions/) | adr | 3 |
| [tasks/](tasks/) | task | 22 |
| [docs/](docs/) | doc | 1 |
| [epics/](epics/) | epic | 0 |

**Status** (from `tracker stats`, 2026-08-01): DONE 39 · PLANNED 14 · PROPOSED 11 · 64 entries total.

## Usage

```bash
tracker search "<topic>"        # find related entries before editing
tracker affects <file-path>     # which entries touch a file
tracker validate && tracker rebuild
```

## Migration history (SCHEMA 2 → SCHEMA 3)

On 2026-08-01 all 44 legacy SCHEMA 2 entries (sequential IDs, `issue` type,
`OPEN`/`CLOSED` statuses) were migrated to SCHEMA 3 ULID IDs using the
`tracker` CLI. Every migrated entry carries a
"*Migrated from SCHEMA 2 entry …*" provenance line in its `## Background`,
and its old `SUMMARY` is preserved in the frontmatter. The old files were
deleted — git history retains the originals.
| Old | New |
|-----|-----|
| bugs/001 | BUG-01KYZ1D1S29KD6NWB2R9J01GWF |
| bugs/002 | BUG-01KYZ1D1VQQPKM6XFGQH4DXY4J |
| bugs/003 | BUG-01KYZ1D1Y3TJ8WB8YAHDYF15YN |
| bugs/004 | BUG-01KYZ1D20GRTWMQ5HE27MJET0H |
| bugs/005 | BUG-01KYZ1D22R68NT6BAN8AEY9VPV |
| bugs/006 | BUG-01KYZ1D257KRJHAB9XDQ7RC79X |
| bugs/007 | BUG-01KYZ1D27H4YVHPY977NX7HWGQ |
| bugs/008 | BUG-01KYZ1D29WYPVF1J2HE7MSZ4XZ |
| bugs/009 | BUG-01KYZ1D2C4C1P0R85P0J15G72D |
| features/001 | FEAT-01KYZ1HC53CSABYXTWZ6ATXYZ8 |
| features/002 | FEAT-01KYZ1HC7DYBXKJ66538Z9P64K |
| features/003 | FEAT-01KYZ1HC9HQ698013QR0GYMJMP |
| features/004 | FEAT-01KYZ1HCBW2CNCNE7D50C34X4S |
| features/005 | FEAT-01KYZ1HCE56JWXA4B21Q3DFANT |
| features/006 | FEAT-01KYZ1HCGN5HVFW52A5PG9ZEDB |
| features/007 | FEAT-01KYZ1HCJVE31KF3F1HVGMRNHZ |
| features/008 | FEAT-01KYZ1HCMYDT2HS1JS7R4QAGHJ |
| features/009 | FEAT-01KYZ1HCQ40GHEYZA567JRGTKV |
| features/010 | FEAT-01KYZ1HCS9ZKCJ9NDHXZP1SA9K |
| features/011 | FEAT-01KYZ1HCVSDJN5FRA0R4AY3VR4 |
| features/012 | FEAT-01KYZ1HCXWZKHG4D03XDV4MBJB |
| features/013 | FEAT-01KYZ1HD041TCC8X6GW22KYFSA |
| features/014 | FEAT-01KYZ1HD2DD5H9CQ3DH2737WZB |
| features/015 | FEAT-01KYZ1HD4Y02CSHEZ6BP5TM9G2 |
| features/016 | FEAT-01KYZ1HD75D2JV0MHF45JDSYVT |
| features/017 | FEAT-01KYZ1HD9CXS24FQ19PBX1T219 |
| features/018 | FEAT-01KYZ1HDBPMFG4G6HANFNCHJGA |
| features/019 | FEAT-01KYZ1HDDXK2PHFQPFDW0XCC83 |
| features/020 | FEAT-01KYZ1HDG3JY6G1F68VQ0V0549 |
| features/021 | FEAT-01KYZ1HDJ96T4F0PBXVSSC2QWG |
| features/022 | FEAT-01KYZ1HDMJRX33A5HEPJXGQ4FC |
| features/023 | FEAT-01KYZ1HDPSK52529VXQBYAEX64 |
| features/024 | FEAT-01KYZ1HDSB1FAWT6HX1RMRPR36 |
| features/025 | FEAT-01KYZ1HDVH8B6KRFHAAG9K43D7 |
| features/026 | FEAT-01KYZ1HDXP92GQS3Z8CA47R3HW |
| features/027 | FEAT-01KYZ1HDZVZB1DAZZP53GM2ASH |
| features/028 | FEAT-01KYZ1HE23VRV2ZH5MB4HGBW75 |
| issues/001 | TASK-01KYZ1XG23G90A9XDRGPRJSQQ0 |
| issues/002 | TASK-01KYZ1XG4C56PXE6T313P1W5TP |
| issues/003 | ADR-01KYZ1XG6W0K8NQPMV2Z6WCVYM |
| issues/004 | ADR-01KYZ1XG9EWRX1VXY30CRCTMJH |
| issues/005 | TASK-01KYZ1XGBV9JW9CK98079H4B6J |
| issues/006 | DOC-01KYZ1XGE9FSXGDWY3T3SZHKDT |
| issues/007 | ADR-01KYZ1XGGHXX9F2DW5HDXBBWMG |

*Issue classification: 001 → task (test-suite gap), 002 → task (closed by
design), 003/004/007 → adr (decisions), 005 → task (chore), 006 → doc.*
