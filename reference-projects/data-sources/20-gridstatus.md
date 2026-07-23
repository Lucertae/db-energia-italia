# gridstatus — fonti dati

- **Portale dati:** [US/Canada ISO + EIA](https://www.gridstatus.io/)

- **Demo:** https://www.gridstatus.io/

Libreria Python. Molti endpoint pubblici senza key; alcuni richiedono credenziali (vedi .env.template).

## ISO / operator supportati (10)

1. CAISO — prices, load, renewables, outages
2. ERCOT — SPP prices, load, wind/solar, congestion
3. PJM — LMP, load, generation fuel mix
4. MISO — day-ahead/real-time LMP, load
5. SPP — prices, load, renewables
6. ISONE — prices, load, fuel mix
7. NYISO — prices, load, interface flows
8. IESO — Ontario market data
9. AESO — Alberta market data
10. EIA — fuel mix, generation (US aggregate)

## Moduli Python nel package (13)

1. aeso
2. base
3. caiso
4. eia
5. ercot
6. ieso
7. isone
8. miso
9. nyiso
10. pjm
11. spp
12. utils
13. version
