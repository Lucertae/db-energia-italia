# Plan — Metadati + cataloghi db/*

> **For agentic workers:** implement end-to-end; delete GAPS.md.

**Goal:** Uniform METADATI.txt + catalog.csv per package; global catalog; no GAPS.md.

### Task 1: Builder script
- Create `db/scripts/build_metadata_catalogs.py` with dataset registry and disk measurement.
- Run it to emit catalogs.

### Task 2: METADATI narratives
- Write complete METADATI.txt for stub packages; refresh others; include AUTO-STATS block.

### Task 3: Cleanup
- Delete `db/GAPS.md`; update README/script references.
- Update `db/README.md` index volumes from catalog.
