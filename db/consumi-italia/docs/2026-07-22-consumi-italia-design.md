# Consumi Italia — Design (approccio A)

## Goal

Offline Italy consumption DB combining Terna (IMCEI/IMSER/bilanci), ARERA (domestici + non domestici ATECO), and Eurostat energy balances.

## Layout

`db/consumi-italia/sources/{terna,arera,eurostat}/` + `scripts/harvest_all.py` + `catalog.csv`

## Rules

- Italy only; aggregated ATECO/sector/territory — no company names / POD.
- Resume-safe downloads; keep originals + thin normalized Italy tables where useful.
