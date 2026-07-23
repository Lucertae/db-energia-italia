Terna IMCEI (industria energivori) e IMSER (servizi ATECO):
  Dashboard: https://dati.terna.it/en/load/imcei
             https://dati.terna.it/en/load/imser
  API pubblica (richiede registrazione + token):
             https://developer.terna.it/docs/read/apis_catalog
  Endpoint catalogato: Monthly Index Industrial Electrical Consumption

In questo harvest è incluso il bilancio annuale per settore (fonte Terna via ISPRA).
Per serie mensili IMCEI/IMSER: crea app su developer.terna.it e metti il token in
  db/consumi-italia/terna.token  (una riga), poi ri-lancia harvest_all.py
