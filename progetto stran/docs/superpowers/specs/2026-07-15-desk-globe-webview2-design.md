# Design: OPS DESK GLOBE (WebView2 + Real-Time Earthquake Globe)

**Date:** 2026-07-15  
**Status:** approved  
**Base:** https://github.com/AaronMurillo01/Real-Time-Earthquake-Globe

## Goal
Embed a multi-layer 3D globe *inside* the Win32 OPS DESK, using that repo as the visual/technical base, with World Monitor–style layers (quakes, fires, flights, AIS, conflicts, …).

## Architecture
1. **globe/** — Vite + React + Three.js app forked/adapted from the base repo.
2. **Local data bridge** — HTTP endpoints served with the globe (or desk `cache/`) exposing GeoJSON/FeatureCollections from USGS + `cache/live/events.json` + AIS snapshot.
3. **Desk PAGE_GLOBE** — Win32 page hosting **WebView2** filling the content area; starts local static/preview server if needed; navigates to `http://127.0.0.1:<port>/`.

## Layers (v1 toggles)
- natural / quakes (USGS)
- fires (EONET / live)
- flights (OpenSky points from live events)
- ais (ships if positions available)
- conflicts / unrest (ACLED/GDELT points if present)
- other live events with lat/lon as generic markers

## Non-goals (v1)
- Full WM CII choropleth / Deck.gl parity
- Replacing flat AIS/MET maps

## Success
- From `--data` or full desk, open GLOBE and see interactive globe with layer toggles and live USGS points within seconds.
