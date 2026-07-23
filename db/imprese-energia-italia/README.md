imprese-energia-italia — harvest massivo da registri ufficiali
Aggiornato: 2026-07-23

================================================================================
1) COSA ABBIAMO SCARICATO (NOMINATIVI REALI)
================================================================================
Fonte ARERA — Anagrafiche Operatori (export 22/07/2026):
  sources/arera_operatori/operatori-export-*.xlsx
  derived/arera_operatori_ALL.csv                 ~31.984 P.IVA uniche
  derived/arera_produzione_energia_elettrica.csv  ~25.695 (codice attività a)
  derived/arera_distribuzione_ee.csv
  derived/arera_distribuzione_gas.csv
  derived/arera_venditori_elettrico.csv           ~734
  derived/arera_venditori_gas.csv                 ~634
  derived/arera_activity_counts.json
  derived/summary.json

Conteggi attività ARERA (un operatore può avere più attività):
  produzione EE ..................... ~25.695
  vendita libero EE ................. ~734
  vendita libero gas ................ ~632
  ingrosso EE ....................... ~588
  ingrosso gas ...................... ~523
  misura gas ........................ ~193
  distribuzione gas ................. ~180
  misura EE ......................... ~173
  produzione energia termica ........ ~226
  distribuzione energia termica ..... ~198
  distribuzione EE .................. ~111

Nota: ARERA = operatori regolati (energia + spesso acqua/rifiuti/teleriscaldamento).
Non è il Registro Imprese completo per ATECO installatori/EPC.


================================================================================
2) CODICI ATECO — FILTRO ECOSISTEMA ENERGIA (per Registro Imprese / ciccio)
================================================================================
Usare questi codici per estrarre MASSIVAMENTE dal Registro Imprese / Movimprese /
database imprese su ciccio (~stock imprese IT ~5,85 mln registrate fine 2025):

--- CORE ENERGIA (sezione D) ---
35      Fornitura di energia elettrica, gas, vapore e aria condizionata
35.1    Produzione, trasmissione e distribuzione di energia elettrica
35.11   Produzione di energia elettrica
35.12   Trasmissione di energia elettrica
35.13   Distribuzione di energia elettrica
35.14   Commercio di energia elettrica
35.2    Produzione di gas; distribuzione di combustibili gassosi
35.21   Produzione di gas
35.22   Distribuzione di combustibili gassosi mediante condotte
35.23   Commercio di gas distribuito mediante condotte
35.3    Fornitura di vapore e aria condizionata (teleriscaldamento)

--- UPSTREAM / DOWNSTREAM OIL&GAS ---
06      Estrazione di petrolio greggio e di gas naturale
09.10   Attività di supporto all'estrazione di petrolio e di gas naturale
19.2    Fabbricazione di prodotti di raffinazione del petrolio
46.71   Commercio all'ingrosso di combustibili solidi, liquidi, gassosi

--- RETI / COSTRUZIONE INFRA ---
42.21   Costruzione di opere per fluidi (gasdotti, oleodotti, idrauliche)
42.22   Costruzione di opere per elettricità e telecomunicazioni
42.99   Altre opere di ingegneria civile n.c.a. (parti energy)

--- INSTALLAZIONE / MANUTENZIONE (qui stanno le MIGLIAIA) ---
43.21   Installazione di impianti elettrici          << PMI massive
43.22   Installazione di impianti idraulici, di riscaldamento e di condizionamento
43.29   Altri lavori di costruzione e installazione
33.14   Riparazione e manutenzione di apparecchiature elettriche
33.20   Installazione di macchine e attrezzature industriali
81.21/81.22  Pulizia / facility (O&M building energy, non core)

--- INGEGNERIA / SERVICE ---
71.12   Attività degli studi di ingegneria
71.20   Collaudi e analisi tecniche
74.90   Altre attività professionali n.c.a. (ESCO/consulenza energy)

--- FABBRICAZIONE COMPONENTI ---
27.1    Motori, generatori, trasformatori, apparecchiature distribuzione
27.11   Motori generatori trasformatori
27.12   Apparecchiature per la distribuzione e il controllo dell'elettricità
27.3    Fili e cavi
27.9    Altre apparecchiature elettriche


================================================================================
3) FONTI PER HARVEST MASSIVO (PRIORITÀ)
================================================================================
A) ARERA (FATTO — nominativi gratis)
   https://www.arera.it/area-operatori/ricerca-operatori
   → zip operatori + venditori EE + venditori gas
   Script: harvest_arera.py / count_activities.py

B) Registro Imprese / InfoCamere (NOMINATIVI COMPLETI ATECO — a pagamento / account)
   https://www.registroimprese.it/
   https://ateco.infocamere.it/
   Estrarre liste per ATECO 35* + 43.21 + 43.22 + 42.21/22 + 06 + 09.10 + 19.2 + 27.*
   Su ciccio: se hai già dump imprese (~centinaia di migliaia / milioni),
   filtrare con la mappa ATECO sopra.

C) Movimprese (STOCK per territorio×ATECO — gratis, non nominativo)
   https://www.infocamere.it/movimprese
   Sezione D energia: +5,16% stock 2025 (Unioncamere/InfoCamere / Sole 24 Ore)
   Stock imprese IT registrate fine 2025: ~5.849.524

D) Open Data Camere (stock JSON-stat / schede)
   https://opendata.marche.camcom.it/
   Dataset "Settore Ateco D - Imprese Attive in Italia per Territorio e Tempo"
   Licenza CC-BY 4.0 — conteggi regione/provincia, non elenco ragioni sociali

E) GSE (produttori incentivati / RID / FER — nominativi parziali)
   Portali GSE (applicativi operatori, open data incentivi)
   Utile per produttore RES oltre ARERA

F) Terna codici DSO / GAUDI (punti di connessione)
   Complementare a ARERA distribuzione


================================================================================
4) COME ARRIVARE ALLE MIGLIAIA (PROCEDURA OPERATIVA)
================================================================================
1. Tenere ARERA derived/*.csv come layer "operatori regolati" (~26k produttori EE).
2. Su ciccio / Registro Imprese: query ATECO IN (35%, 43.21, 43.22, 42.21, 42.22,
   06%, 09.10%, 19.2%, 27.1%, 27.3%, 33.14, 33.20, 71.12) → export CSV.
3. Join su Partita IVA: ARERA ⋊ Registro Imprese.
4. Arricchire regione da CAP / codice catastale sede.
5. Separare layer:
   - PRODUZIONE (ARERA a + ATECO 35.11)
   - RETI (ARERA d/p + ATECO 35.12/35.13/35.22)
   - VENDITA (ARERA i/t + ATECO 35.14/35.23)
   - INSTALLAZIONE/O&M (ATECO 43.21/43.22/33.*)  ← volume PMI
   - EPC/INGEGNERIA (42.2* / 71.12)
6. Aggiornare mensile: re-download zip ARERA + delta Movimprese.


================================================================================
5) LIMITI IMPORTANTI
================================================================================
- Open data camerali = STOCK, raramente ragioni sociali complete gratis.
- registroaziende.it e simili mostrano sottoinsiemi con bilanci pubblici
  (es. ATECO 43.21 "3.807 con fatturato" ≠ totale imprese 43.21).
- Il file aziende-energetiche-it.txt resta la MAPPA dei big/regionali;
  i CSV in derived/ sono l'anagrafica MASSIVA.
