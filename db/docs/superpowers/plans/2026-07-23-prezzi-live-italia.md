# Prezzi live Italia — Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox syntax.

**Goal:** Download automatic Italy economic price feeds into `mercati-italia/sources/prezzi_live/`.

**Architecture:** Single script `db/scripts/harvest_prezzi_live.py` pulls ENTSO-E DA (90d), Ember IT daily, ARERA indices, SISEN fuels, EEX EUA current year; writes manifest + snapshot.

**Tech Stack:** Python 3, pandas, entsoe-py, urllib

## Tasks

- [ ] Task 1: Implement `harvest_prezzi_live.py`
- [ ] Task 2: Run harvest and verify outputs
- [x] Task 3: Update METADATI (GAPS.md rimosso)
