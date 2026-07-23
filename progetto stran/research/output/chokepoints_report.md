# Chokepoint monitoring report

_No AIS snapshot — showing catalog baseline and monitoring plan._

## Baseline flows (EIA 1H25, mb/d)

- **malacca**: 23.2 mb/d
- **hormuz**: 20.9 mb/d
- **bab_el_mandeb**: 4.2 mb/d
- **suez_sumed**: 4.9 mb/d

## Corridors to monitor (AIS bbox)

- **HORMUZ** Strait of Hormuz: bbox [26.0, 27.0, 55.5, 57.0] — Feb 2026: -90% traffic at peak; Qatar LNG 100% dependent
- **MALACCA** Strait of Malacca: bbox [0.5, 6.0, 99.0, 104.5] — Largest oil chokepoint globally; 84% Hormuz oil continues here to Asia
- **SUNDA** Sunda Strait: bbox [-7.0, -5.0, 104.5, 106.5] — VLCC fully loaded; Anak Krakatoa hazard
- **LOMBOK** Lombok Strait: bbox [-9.5, -7.5, 115.0, 116.5] — ULCC/deep draft; TSS since 2020
- **FUJAIRAH** Fujairah / Khor Fakkan (UAE bypass): bbox [24.8, 25.5, 56.0, 56.8] — Only major bypass into Indian Ocean; drone risk 2026
- **YANBU** Yanbu (Saudi Petroline): bbox [23.5, 24.5, 37.5, 38.5] — Red Sea export; second choke Bab el-Mandeb
- **BAB_EL_MANDEB** Bab el-Mandeb: bbox [12.0, 13.5, 42.5, 44.5] — Houthi attacks resumed Feb 2026; links Yanbu bypass to Suez
- **CAPE** Cape of Good Hope: bbox [-36.0, -32.0, 17.0, 20.0] — +35% traffic Mar 2026 during Hormuz closure
- **KYAUKPYU** Kyaukpyu / Maday Island (Myanmar-China pipeline): bbox [18.5, 20.0, 92.5, 94.5] — ~6.5 mb/d China imports via Malacca vs 0.44 mb/d via pipeline

## Pipeline bypass capacity

- **ADCOP**: 1.80 mb/d equiv — avoids ['HORMUZ']
- **PETROLINE**: 7.00 mb/d equiv — avoids ['HORMUZ']
- **KIRKUK_CEYHAN**: 0.25 mb/d equiv — avoids ['HORMUZ']
- **GOREH_JASK**: 1.00 mb/d equiv — avoids ['HORMUZ']
- **MYANMAR_CHINA**: 0.44 mb/d equiv — avoids ['MALACCA']

## Next steps

1. Export AIS positions from desk page N to `research/output/ais_snapshot.json`
2. Integrate IMF PortWatch transit counts
3. Compare Malacca/Hormuz ratio vs EIA baseline
4. Track Fujairah vs Hormuz tanker origin split

Full analysis: `docs/research/CHOKEPOINTS_ROUTES.md`
