# OpenSanctions

- **Fonti dati:** [OFAC/EU/UN sanctions · yente API](https://www.opensanctions.org/docs/api/) · [elenco completo](../data-sources/25-opensanctions.md)
- **Sito:** https://www.opensanctions.org
- **API:** https://api.opensanctions.org
- **Stack:** Python (zavod), FollowTheMoney schema
- **Licenza:** MIT (codice); dati CC BY-NC 4.0

## Screenshot UI

*Ricerca entità su [opensanctions.org](https://www.opensanctions.org/). Nessun desk trading — dati compliance.*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/25-opensanctions.md](../data-sources/25-opensanctions.md)

Database aggregato **sanzioni + PEP** — gap non coperto dai 18 progetti originali.

| Fonte | Dati |
|-------|------|
| **OFAC SDN** | Sanzioni US Treasury |
| **EU Consolidated** | Lista UE |
| **UN Security Council** | Sanzioni ONU |
| **UK HMT/OFSI** | Sanzioni UK |
| **PEP multi-country** | Politically exposed persons |
| **yente API** | Entity matching fuzzy |

Export bulk: FollowTheMoney JSON, CSV. Crawler `datasets/` nel repo.

**Cosa rubare per STRAN:** screening vessel/company contro sanzioni; enrich AIS callsign → beneficial owner.
