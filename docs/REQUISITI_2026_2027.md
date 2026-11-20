# DidaUP — Decisioni funzionali confermate

Fonte: decisioni esplicitamente comunicate dall'utilizzatore. Documento di progetto, **senza dati amministrativi reali**.

## Scelte
1. **Anno accademico**: più annualità consultabili e modificabili separatamente, con selettore A.A. globale. L'archivio 2026/27 costituisce il punto di partenza. Il 2027/28 sarà importato/confrontato quando l'estrazione ufficiale sarà disponibile.
2. **Distribuzione**: un solo Excel per SSD dell'insegnamento, per tutta l'area medica; non uno per Dipartimento.
3. **Layout del file**: unico foglio principale, con filtri e sezioni.
4. **Compilazione**: i referenti indicano **solo le variazioni**. Le coperture storiche e le colonne informative dell'insegnamento non sono modificabili. L'assenza di variazioni non costituisce approvazione amministrativa.
5. **Nuovo docente**: scelta da elenco verificato, con possibilità di testo libero segnalato per la verifica della Segreteria.
6. **SSD incrociati**: preservare il dato storico dell'insegnamento SSD X coperto dal docente SSD Y; segnalarlo in fase di controllo senza duplicare la proposta e senza considerarlo automaticamente un errore.
7. **Ritorno file**: ammettere XLSX restituiti sia da email sia da SharePoint/OneDrive. Il gestionale non accede agli account dei referenti.
8. **Collaudo**: solo dati completamente sintetici su Home Assistant domestico; dati istituzionali reali solo in ambiente autorizzato.

## Dettagli aggiuntivi confermati
- Il report 2026/27 condiviso è l'unico report di partenza indicato.
- Prima dell'elaborazione, consentire l'**esclusione non distruttiva** di specifiche annualità dei CdS non più di competenza.
- Gestire **più docenti e ripartizioni di ore** sulla stessa attività didattica.
- Gli SSD di competenza dei referenti sono gli stessi nella vecchia/nuova codifica secondo l'indicazione dell'utilizzatore; l'effettiva tabella codici deve derivare dalla fonte ufficiale, senza conversioni ipotetiche.
- In caso di restituzione successiva di un XLSX, **la nuova proposta sostituisce quella precedente**, conservando lo storico e producendo un riepilogo evidente delle differenze.
- **Regolamento affidamenti**: nella fase di sviluppo tradurre le regole effettive in note e segnalazioni nell'Excel, con fonti e controlli verificati.
- Interfaccia add-on: grafica moderna, funzionalità accessibili con pochi passaggi.

## Accesso applicazione
- L'add-on serve soltanto la Segreteria con **multi-account**, ruoli amministratore, operatore e sola lettura.
- Disponibili accesso tramite Home Assistant Ingress e **porta per Cloudflare Tunnel**.
- Per accesso remoto sono obbligatori HTTPS, accessi autorizzati tramite Cloudflare Access e autenticazione individuale nell'applicazione.
- I referenti SSD **non accedono all'add-on** e compilano gli XLSX offline/nei canali autorizzati.

## Stato implementazione iniziale
Versione `0.1.0-alpha1`: predisposti selettore A.A., archivio degli anni, censimento manuale sintetico delle annualità CdS, esclusione/ripristino con motivazione, account multiutente e accesso su porta dedicata. **Non sono ancora implementati** import del report .xls, gestione referenti SSD, esportazione XLSX, reimportazione e confronto delle differenze, motore regolamentare e approvazioni.

La logica di inclusione/esclusione nell'alpha riguarda le annualità censite nell'applicazione, senza modificare il report esterno.
