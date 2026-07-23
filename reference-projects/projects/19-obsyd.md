# OBSYD

- **Fonti dati:** [ENTSO-E · Fraunhofer · GIE gas API](https://obsyd.dev/api/docs) · [elenco completo](../data-sources/19-obsyd.md)
- **Demo:** https://obsyd.dev
- **Stack:** TypeScript, web dashboard
- **Licenza:** AGPL-3.0

## Screenshot UI

*Desk live su [obsyd.dev](https://obsyd.dev). Screenshot da aggiungere in `images/`.*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/19-obsyd.md](../data-sources/19-obsyd.md)

Desk energia europeo open source — “gridstatus per l’Europa”. Copre **DE-LU, FR, NL**.

| Fonte | Dati | Auth |
|-------|------|------|
| **ENTSO-E** | Prezzi day-ahead, load, mix generazione, flussi cross-border | Token free (Transparency Platform) |
| **Fraunhofer Energy-Charts** | Mix, residual load, forecast | Pubblico |
| **GIE** | Gas storage ALSI/AGSI, LNG, flussi EU | Pubblico |

### Anomaly radar

Regole e soglie in codice aperto (no ML black-box): prezzi negativi, Dunkelflaute, spike day-ahead, movimenti gas.

**Cosa rubare per STRAN:** desk unificato energia+gas, flag anomalie con contesto “vs normal”, correlazione marginal price ↔ gas balance.
