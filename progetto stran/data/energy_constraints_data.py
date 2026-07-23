"""Constraints per fonte: meteo, vincoli legali, manutenzione/gestione."""

from __future__ import annotations

# Template per famiglia — override per id dove serve specificità
_T = {
    "coal": {
        "meteo": "Piene e infiltrazioni in miniera; gelo su vie di trasporto; siccità → polveri e rischio incendio depositi.",
        "legal": "Concessione estrattiva; VIA/VINCA; Direttiva IEED; EU ETS; D.Lgs. 81/08 sicurezza; limiti emissioni PM/SO₂.",
        "ops": "Drenaggio, ventilazione, manutenzione convogliatori/frantumazione; gestione sterili; turni continui; fermo stagionale possibile.",
    },
    "peat": {
        "meteo": "Umidità torba (potere calorifico); siccità prolungata riduce estraibilità; gelo blocca lavorazioni.",
        "legal": "Vincoli Ramsar/zone umide; autorizzazione estrattiva; limiti CO₂ da suoli organici.",
        "ops": "Essiccazione controllata; gestione falda; ripristino ambientale obbligatorio.",
    },
    "oil_extract": {
        "meteo": "Mareggiate e nebbia (offshore); gelo (onshore nord); caldo estremo → perdite evaporative.",
        "legal": "Concessione mineraria/Idrocarburi D.Lgs. 625/96; MARPOL offshore; REACH; norme Seveso raffineria.",
        "ops": "Workover pozzi; pigging condotte; turnaround raffineria 3–5 anni; gestione H₂S e flare.",
    },
    "oil_sands": {
        "meteo": "Gelo frena estrazione a cielo aperto; pioggia allaga mine; temperatura incide su diluente bitume.",
        "legal": "Valutazione impatto territoriale; obblighi ripristino; carbon tax / ETS; diritti indigeni (CA).",
        "ops": "Manutenzione shovel/truck; upgraders; gestione tailings pond; alto CAPEX O&M.",
    },
    "oil_shale": {
        "meteo": "Temperatura incide su retorting; acqua di processo vincolata da siccità.",
        "legal": "Autorizzazione sperimentale/commerciale; vincoli idrici; emissioni CO₂ elevata → ETS.",
        "ops": "Manutenzione forni/fratturazione; gestione scorie; tecnologia ancora marginale.",
    },
    "oil_products": {
        "meteo": "Caldo → pressione vapore serbatoi; gelo → viscosità e pompe; fulmini su impianti.",
        "legal": "Autorizzazione impianto raffineria/deposito; ADR trasporto; norme antincendio UNI; REACH prodotti.",
        "ops": "Turnaround unità; calibrazione strumentazione; stock rotation; manutenzione burner/coker.",
    },
    "gas_field": {
        "meteo": "Gelo riduce portata compressori; caldo estremo → domanda picco; vento su flare.",
        "legal": "Concessione pozzo; TEN-E / regolazione gas; REMIT reporting; norme fughe metano UE.",
        "ops": "Compressione, disidratazione, filtri; ispezioni smart pig; manutenzione wellhead.",
    },
    "shale_gas": {
        "meteo": "Gelo frena fracking; pioggia intensa → gestione flowback; sismicità indotta monitorata post-evento.",
        "legal": "Permesso fratturazione idraulica (vietata in diversi Stati UE); vincoli acqua; norme sismiche locali.",
        "ops": "Workover frequenti; gestione acque di processo; declino rapido pozzi → drilling continuo.",
    },
    "lng_chain": {
        "meteo": "Temperatura mare incide su regasificazione; nebbia salina su terminali costieri; gelo su evaporatori.",
        "legal": "Autorizzazione terminale LNG; codice IMO cargo; distanze sicurezza portuale; contratti take-or-pay.",
        "ops": "Manutenzione treni liquefazione/regas; boil-off gas; interventi su storage criogenico.",
    },
    "lpg": {
        "meteo": "Caldo aumenta pressione serbatoi; gelo incide su vaporizzatori.",
        "legal": "Norme Seveso depositi; ADR; UNI 11653 installazioni GPL.",
        "ops": "Controlli tenuta; ricertificazione bombole; manutenzione pompanti/caricamento.",
    },
    "gas_hydrates": {
        "meteo": "Pressione/temperatura fondale critiche per stabilità idrati; correnti marine.",
        "legal": "Ricerca sperimentale; zone economiche esclusive; valutazione impatto marino.",
        "ops": "Tecnologia non matura; manutenzione offshore estrema; R&D.",
    },
    "nuclear": {
        "meteo": "Temperatura acqua di scarico (limite reattore); siccità riduce refrigerazione; vento per dispersione (emergenza).",
        "legal": "Licenza autorità nucleare nazionale; Direttiva 2014/87/Euratom; piani emergenza; gestione rifiuti radioattivi.",
        "ops": "Outage programmato 18–24 mesi; ricarica combustibile; controlli non distruttivi; gestione scorie.",
    },
    "nuclear_fusion": {
        "meteo": "Trascurabile sulla fisica; raffreddamento impianto sensibile a temperatura.",
        "legal": "Autorizzazione sperimentale; normativa in evoluzione; fusione non commerciale.",
        "ops": "R&D continuo; manutenzione superconduttori; cicli brevi sperimentali.",
    },
    "nuclear_rtg": {
        "meteo": "Temperatura ambiente su dissipazione radiatore.",
        "legal": "Trasporto materiali nucleari; licenze uso spaziale/militare; dose ALARA.",
        "ops": "Sostituzione radioisotopo a fine vita; nessuna manutenzione ordinaria in missione.",
    },
    "solar_pv": {
        "meteo": "Irraggiamento GHI; temperatura modulo (−0,3%/°C); neve/occlusione; albedo.",
        "legal": "Autorizzazione PAUR/unica; connessione Terna; GSE/tariffe; vincoli paesaggistici.",
        "ops": "Pulizia moduli; inverter; monitoraggio stringhe; sostituzione 25–30 anni.",
    },
    "solar_floating": {
        "meteo": "GHI + vento onda; umidità e corrosione; evaporazione superficie.",
        "legal": "Concessione specchio d'acqua; autorizzazione idraulica; impatto ecosistema lacustre.",
        "ops": "Ancoraggi; corrosione galleggianti; accesso barca per O&M.",
    },
    "solar_csp": {
        "meteo": "DNI (non GHI); vento su specchi; sabbia/polvere su specchi; nuvolosità blocca.",
        "legal": "Autorizzazione impianto termoelettrico; consumo acqua cooling; vincoli territorio arido.",
        "ops": "Pulizia specchi/heliostat; sale termico; turbine vapore; manutenzione tracking.",
    },
    "solar_thermal_flat": {
        "meteo": "Irraggiamento e temperatura ambiente; gelo → antigelo fluido; nuvole riducono rendimento.",
        "legal": "Autorizzazione impianto; incentivi conto termico (IT); norme edilizie.",
        "ops": "Controllo fluido termovettore; pompe; pulizia collettori.",
    },
    "wind_onshore": {
        "meteo": "Velocità/direzione vento (power curve); turbolenza; icing (altitudine); fulmini.",
        "legal": "Autorizzazione ENAC/regionale; distanze minime; valutazione impatto ornitologico/bat.",
        "ops": "Gearbox/generatore; ispezione pale (drone/rope); lubrificazione; availability 95–98%.",
    },
    "wind_offshore": {
        "meteo": "Vento marino; onde significative (accesso); icing; tempeste → stop turbine.",
        "legal": "Concessione demaniale marittima; MIT/MASE; valutazione Natura 2000; cavi in mare.",
        "ops": "SOV/CTV/Heli access; corrosione; interventi weather window; costi O&M 2–3× onshore.",
    },
    "wind_awes": {
        "meteo": "Profilo vento ad alta quota; shear; turbolenza; temporali.",
        "legal": "Spazio aereo ENAC; autorizzazione sperimentale; normativa in definizione.",
        "ops": "Manutenzione cavo/ala; recupero aerostato; tecnologia pre-commerciale.",
    },
    "hydro_reservoir": {
        "meteo": "Precipitazioni e scioglimento neve (afflusso); siccità → vincolo idrico; piene.",
        "legal": "Concessione derivazione/acqua; sicurezza diga (D.Lgs. 152); piano emergenza bacino.",
        "ops": "Gestione sedimenti; manutenzione turbine/paratoie; revisione diga decennale.",
    },
    "hydro_run": {
        "meteo": "Portata fiume in tempo reale; piene improvvise; siccità.",
        "legal": "Concessione idroelettrica; portata minima vitale; vincoli pescicoltura.",
        "ops": "Griglie sedimenti; manutenzione turbine; meno stoccaggio → più variabilità.",
    },
    "hydro_pumped": {
        "meteo": "Differenziale prezzo legato a vento/solare; disponibilità acqua bacino superiore.",
        "legal": "Autorizzazione accumulo; stesso vincoli diga; mercato capacità.",
        "ops": "Cicli start/stop frequenti; usura turbine reversible; gestione evaporazione bacini.",
    },
    "hydro_micro": {
        "meteo": "Portata locale variabile; detriti in pioggia.",
        "legal": "Semplificazione autorizzativa (<100 kW IT); vincoli torrenti.",
        "ops": "Pulizia griglia; manutenzione ridotta; spesso senza personale residente.",
    },
    "hydro_in_stream": {
        "meteo": "Velocità corrente; livello fiume; detriti.",
        "legal": "Concessione corso d'acqua; impatto idraulico minimo richiesto.",
        "ops": "Manutenzione turbina a flusso libero; ostruzioni.",
    },
    "geothermal": {
        "meteo": "Temperatura ambiente su cooling tower; siccità → acqua di raffreddamento.",
        "legal": "Autorizzazione perforazione (DPR 616/77); concessione fluido geotermico; VIA.",
        "ops": "Manutenzione pompe/reiniezione; scaling minerali; corrosion loop.",
    },
    "geothermal_egs": {
        "meteo": "Come geotermico; sismicità indotta monitorata.",
        "legal": "Autorizzazione stimolazione; norme sismiche; sperimentale in molte aree.",
        "ops": "Manutenzione pozzi stimolati; reiniezione obbligatoria; R&D.",
    },
    "biomass_trad": {
        "meteo": "Umidità legna (PCI); stagionalità raccolta; gelo blocca trasporto.",
        "legal": "Combustione domestica → norme regionali PM; inquinamento atmosferico.",
        "ops": "Stoccaggio coperto; pulizia caldaia/fumi; fornitura manuale.",
    },
    "biomass_mod": {
        "meteo": "Umidità cippato/pellet; pioggia su stoccaggio outdoor.",
        "legal": "Autorizzazione impianto; tracciabilità FSC/PEFC; limiti emissioni BIORAF.",
        "ops": "Manutenzione griglia/bruciatore; rimozione cenere; logistica rifornimento.",
    },
    "charcoal": {
        "meteo": "Umidità e vento in carbonaia; siccità rischio incendio.",
        "legal": "Norme regionali carbonaie; deforestazione (tropicali).",
        "ops": "Gestione forni tradizionali; resa 15–25%; lavoro stagionale.",
    },
    "energy_crops": {
        "meteo": "Pioggia/stagione vegetativa; siccità → resa ton/ha; gelo tardivo.",
        "legal": "Vincoli uso suolo (no food vs fuel); PAC; RED III sostenibilità.",
        "ops": "Raccolta meccanica; essiccazione; stoccaggio; rotazione colture.",
    },
    "bagasse": {
        "meteo": "Stagionalità zucchero; umidità residuo post-molienda.",
        "legal": "Integrato industria saccarifera; emissioni in situ.",
        "ops": "Combustione continua in stagione zucchero; manutenzione caldaia annuale.",
    },
    "black_liquor": {
        "meteo": "Minima; temperatura recupero solfite.",
        "legal": "Impianto carta integrato; norme chimica industriale.",
        "ops": "Recovery boiler; manutenzione evaporatori; continuità produzione carta.",
    },
    "biogas": {
        "meteo": "Temperatura digestore (mesofilo 38–42°C); freddo riduce produzione.",
        "legal": "Autorizzazione impianto; GSE biogas; REACH digestato come fertilizzante.",
        "ops": "Agitatori; manutenzione CHP; gestione H₂S; svuotamento periodico.",
    },
    "landfill_gas": {
        "meteo": "Temperatura discarica incide su produzione gas; pioggia → lixiviati.",
        "legal": "Autorizzazione discarica (D.Lgs. 36/03); captazione obbligatoria; emissioni CH₄.",
        "ops": "Pozzi captazione; flare/CHP; declino produzione 15–30 anni.",
    },
    "sewage_gas": {
        "meteo": "Temperatura depuratore; portata influenti.",
        "legal": "Concessione depurazione; norme biogas impianto pubblico.",
        "ops": "Manutenzione digestori; cogenerazione; gestione schiume.",
    },
    "biofuels": {
        "meteo": "Stagionalità materia prima; umidità cereali/oilseed.",
        "legal": "RED III; mandato blending; ISCC/RSB certificazione; limiti ILUC.",
        "ops": "Turnaround bioraffineria; catalizzatori; controllo qualità blend.",
    },
    "biomethane": {
        "meteo": "Come biogas a monte; temperatura upgrading.",
        "legal": "Immissione rete gas (UNI/TR 11537); incentivi GSE; contatore qualità.",
        "ops": "Upgrading membranes; compressione; odorizzazione; analisi continua.",
    },
    "waste_municipal": {
        "meteo": "Umidità rifiuti (PCI); caldo accelera decomposizione in discarica pre-trattamento.",
        "legal": "Autorizzazione WTE; norme emissioni UE 2010/75; gerarchia rifiuti.",
        "ops": "Manutenzione griglia/bruciatore; manutenzione precipitatori; stop per refrattario.",
    },
    "waste_industrial": {
        "meteo": "Umidità CSS; temperatura stoccaggio.",
        "legal": "Autorizzazione combustione rifiuti speciali; tracciabilità FIR.",
        "ops": "Controllo composizione; manutenzione forno; gestione clinker.",
    },
    "srf": {
        "meteo": "Umidità CSS in stoccaggio; autocombustione rischio caldo.",
        "legal": "Autorizzazione produzione CSS; limiti Cl/S; norme combustione.",
        "ops": "Essiccazione; triturazione; controllo qualità lotto.",
    },
    "marine_wave": {
        "meteo": "Altezza/significant wave period; tempeste danneggiano; swell.",
        "legal": "Concessione zona mare; MIT; valutazione costiera.",
        "ops": "Corrosione marina; accesso limitato; manutenzione idraulica; pre-commercial.",
    },
    "marine_tidal": {
        "meteo": "Escursione marea; correnti; ghiaccio (alte latitudini).",
        "legal": "Concessione demaniale; impatto idrodinamico; rotte navigazione.",
        "ops": "Manutenzione turbine; biofouling; interventi finestra marea.",
    },
    "marine_current": {
        "meteo": "Velocità corrente; tempeste; profondità.",
        "legal": "Come tidal; zone economiche esclusive.",
        "ops": "Manutenzione fondale; cavi; mooring.",
    },
    "marine_otec": {
        "meteo": "Gradiente termico superficie-fondale (tropicale); tempeste.",
        "legal": "Concessione marittima; sperimentale.",
        "ops": "Biofouling scambiatori; manutenzione offshore costosa.",
    },
    "marine_salinity": {
        "meteo": "Gradiente salinità (foce); portata fiume; temperatura.",
        "legal": "Autorizzazione sperimentale; impatto ecosistema estuarino.",
        "ops": "Manutenzione membrane; prevenzione fouling; R&D.",
    },
    "hydrogen_green": {
        "meteo": "Dipende da rinnovabile di alimentazione (vento/solare curtailment).",
        "legal": "Certificazione GO/H₂ verde; norme trasporto H₂; direttiva gas rinnovabili.",
        "ops": "Manutenzione elettrolizzatori; compressione/stoccaggio; purezza 99,99%.",
    },
    "hydrogen_blue": {
        "meteo": "Dipende da disponibilità gas; temperatura SMR.",
        "legal": "CCS autorizzazione stoccaggio CO₂; EU ETS; contabilità emissioni.",
        "ops": "Manutenzione reformer; capture unit; monitoraggio fughe.",
    },
    "hydrogen_grey": {
        "meteo": "Temperatura processo SMR; disponibilità gas rete.",
        "legal": "EU ETS; norme Seveso; obblighi decarbonizzazione futura.",
        "ops": "Turnaround SMR; catalizzatori; manutenzione compressione.",
    },
    "hydrogen_turquoise": {
        "meteo": "Temperatura pirolisi; alimentazione metano.",
        "legal": "Gestione carbon black; norme industriali chimica.",
        "ops": "Manutenzione forno pirolisi; separazione H₂; sperimentale/commerciale emergente.",
    },
    "hydrogen_pink": {
        "meteo": "Dipende da disponibilità nucleare (baseload); temperatura elettrolisi.",
        "legal": "Certificazione origine; norme nuclear-linked H₂ in evoluzione.",
        "ops": "Elettrolizzatori; coupling con reattore; gestione intermittenza manutenzione nucleare.",
    },
    "ammonia": {
        "meteo": "Temperatura sintesi Haber-Bosch; energia elettrica per elettrolisi H₂.",
        "legal": "REACH; trasporto IMO cargo NH₃; norme Seveso.",
        "ops": "Manutenzione sintesi; stoccaggio criogenico/refrigerato; sicurezza fughe.",
    },
    "methanol": {
        "meteo": "Temperatura reazione; feedstock (gas/co₂/biomassa).",
        "legal": "REACH; norme combustibile marino (IMO); incentivi e-methanol.",
        "ops": "Catalizzatori Cu/Zn; distillation; manutenzione reformer.",
    },
    "synthetic_methane": {
        "meteo": "Dipende da elettricità rinnovabile (methanation).",
        "legal": "Immissione rete gas; contabilizzazione GO; TEN-E.",
        "ops": "Metanazione catalitica; upgrading qualità gas; sincronia con electrolysis.",
    },
    "e_fuels": {
        "meteo": "Dipende da curtailment rinnovabile per FT/e-fuel synthesis.",
        "legal": "RED III RFNBO; certificazione; REACH carburanti sintetici.",
        "ops": "Sintesi Fischer-Tropsch/e-refining; manutenzione catalizzatori; alto costo energia.",
    },
    "waste_heat": {
        "meteo": "Temperatura ambiente incide su scambiatori e dissipazione.",
        "legal": "Contabilizzazione energia recuperata; white certificate (IT); nessuna emissione aggiuntiva.",
        "ops": "Manutenzione scambiatori; isolamento rete; sporadico fermo impianto ospite.",
    },
    "ambient_heat": {
        "meteo": "Temperatura esterna (COP pompa di calore); gelo → sbrinamento.",
        "legal": "F-Gas regulation refrigeranti; autorizzazione impianto termico.",
        "ops": "Manutenzione compressori; filtri; controllo refrigerante; stagionale.",
    },
}

# Mapping id → template key
_ID_MAP: dict[str, str] = {
    "coal_anthracite": "coal",
    "coal_bituminous": "coal",
    "coal_subbituminous": "coal",
    "coal_lignite": "coal",
    "coal_coke": "coal",
    "coal_derived_gas": "coal",
    "peat": "peat",
    "oil_crude": "oil_extract",
    "oil_sands": "oil_sands",
    "oil_shale": "oil_shale",
    "oil_products": "oil_products",
    "natural_gas": "gas_field",
    "shale_gas": "shale_gas",
    "tight_gas": "gas_field",
    "associated_gas": "gas_field",
    "coalbed_methane": "gas_field",
    "lng": "lng_chain",
    "lpg": "lpg",
    "gas_hydrates": "gas_hydrates",
    "nuclear_fission_u": "nuclear",
    "nuclear_fission_th": "nuclear",
    "nuclear_fusion": "nuclear_fusion",
    "nuclear_rtg": "nuclear_rtg",
    "solar_pv": "solar_pv",
    "solar_pv_floating": "solar_floating",
    "solar_thermal_csp": "solar_csp",
    "solar_thermal_flat": "solar_thermal_flat",
    "wind_onshore": "wind_onshore",
    "wind_offshore": "wind_offshore",
    "wind_high_altitude": "wind_awes",
    "hydro_reservoir": "hydro_reservoir",
    "hydro_run_of_river": "hydro_run",
    "hydro_pumped_gen": "hydro_pumped",
    "hydro_micro": "hydro_micro",
    "hydro_in_stream": "hydro_in_stream",
    "geothermal": "geothermal",
    "geothermal_egs": "geothermal_egs",
    "biomass_traditional": "biomass_trad",
    "biomass_modern": "biomass_mod",
    "charcoal": "charcoal",
    "energy_crops": "energy_crops",
    "bagasse": "bagasse",
    "black_liquor": "black_liquor",
    "biogas": "biogas",
    "landfill_gas": "landfill_gas",
    "sewage_gas": "sewage_gas",
    "biofuels_liquid": "biofuels",
    "biomethane": "biomethane",
    "municipal_waste": "waste_municipal",
    "industrial_waste": "waste_industrial",
    "solid_recovered_fuel": "srf",
    "marine_wave": "marine_wave",
    "marine_tidal": "marine_tidal",
    "marine_current": "marine_current",
    "marine_otec": "marine_otec",
    "marine_salinity": "marine_salinity",
    "hydrogen_green": "hydrogen_green",
    "hydrogen_blue": "hydrogen_blue",
    "hydrogen_grey": "hydrogen_grey",
    "hydrogen_turquoise": "hydrogen_turquoise",
    "hydrogen_pink": "hydrogen_pink",
    "ammonia": "ammonia",
    "methanol": "methanol",
    "synthetic_methane": "synthetic_methane",
    "e_fuels": "e_fuels",
    "waste_heat": "waste_heat",
    "ambient_heat": "ambient_heat",
}

# Override puntuali per specificità
_OVERRIDES: dict[str, dict[str, str]] = {
    "coal_coke": {
        "meteo": "Umidità e gelo su trasporto coke; vento dispersione polveri.",
        "ops": "Forni a coke: manutenzione refrattari ogni 20–30 anni; recupero sottoprodotti.",
    },
    "coal_derived_gas": {
        "meteo": "Temperatura gasificazione; umidità carbone feedstock.",
        "legal": "Autorizzazione gasificazione; norme syngas Seveso.",
        "ops": "Manutenzione gassificatore; pulizia gas; integrazione CCS opzionale.",
    },
    "tight_gas": {
        "meteo": "Come gas_field; perforazioni multiple sensibili a gelo.",
        "ops": "Declino rapido → refracturing periodico.",
    },
    "associated_gas": {
        "meteo": "Legato a produzione petrolio; vento su flare offshore.",
        "ops": "Gestione flare/VAM; integrazione con oil workover.",
    },
    "coalbed_methane": {
        "meteo": "Depressione giacimento; acqua di produzione aumenta con pioggia.",
        "ops": "Pompe acqua; manutenzione pozzi CBM; declino graduale.",
    },
}


def build_constraints() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for sid, tpl_key in _ID_MAP.items():
        base = dict(_T[tpl_key])
        if sid in _OVERRIDES:
            base.update(_OVERRIDES[sid])
        out[sid] = {
            "meteo": base["meteo"],
            "legal": base["legal"],
            "ops": base["ops"],
        }
    return out


CONSTRAINTS = build_constraints()
