# DidaUP

**Add-on per la predisposizione di file Excel evoluti destinati ai referenti SSD.**

> Stato: **0.1.5-alpha1 (primo nucleo tecnico)**. Nessuna procedura 2027/28 o codifica SSD è considerata approvata o verificata. Non utilizzare dati reali dell'Ateneo durante il collaudo.

## Obiettivo
Partire dall'offerta e dalle coperture storiche **2026/27** per costruire un archivio di riferimento verificabile. Quando saranno disponibili le estrazioni ufficiali, predisporre i fogli di programmazione **2027/28** senza trasporre automaticamente come valide assegnazioni, codici o nominativi precedenti.

## Ambito prioritario
Il primo caso d'uso riguarda i **referenti SSD dell'area medica**, già condivisi con il progetto nei materiali del procedimento 2026/27. La lista dei referenti è una fonte di lavoro, non una conferma automatica per il 2027/28; nominativi, competenze e designazioni del nuovo anno sono **[DA VERIFICARE]**. Non trasferire nominativi o allegati originali su GitHub.

## Regolamento per l'attribuzione dei compiti didattici
Il regolamento già fornito è un riferimento essenziale da analizzare durante lo sviluppo: le regole applicabili dovranno essere evidenziate negli Excel dei referenti come **istruzioni, avvertenze e controlli verificabili**, con il riferimento alla disposizione in vigore. Non inventare obblighi, soglie o condizioni, né introdurre blocchi automatici prima di validare le fonti.

## Utilizzatori
- Segreteria: importazione, produzione dei file Excel per SSD, reimport, controlli e riepiloghi.
- Referenti SSD: **solo file .xlsx**, senza accesso all'add-on.

## Vincoli funzionali
1. La scheda Excel presenta i dati identificativi dell'insegnamento e le coperture storiche in **sola lettura**.
2. Solo le colonne espressamente dedicate alla **nuova proposta** sono compilabili.
3. Il reimport verifica i dati storici contro lo snapshot originale, indipendentemente dalla protezione Excel.
4. Si tengono distinti l'SSD dell'insegnamento e l'SSD del docente, anche in caso di incarichi incrociati.
5. Si memorizzano separatamente vecchia e nuova codifica SSD con tabella di corrispondenza verificata; nessuna conversione presunta.
6. La proposta non sostituisce la copertura storica: attività, coperture e proposte sono entità distinte.
7. L'import 2027/28 richiederà un confronto con l'estrazione ufficiale, con segnalazione delle differenze e validazione della Segreteria.
8. Devono essere gestite le versioni dei file restituiti e i conflitti tra proposte.

## Sicurezza
Repository privato **solo per codice e documentazione tecnica priva di dati personali**. Non caricare file dell'Ateneo o fogli compilati, nemmeno in issue, log, workflow o allegati GitHub.

## Primo add-on tecnico disponibile

Nella cartella [`didaup/`](didaup/) è presente la prima versione:
- interfaccia grafica con **selettore multi-A.A.**, archivio iniziale 2026/27 e creazione degli A.A. successivi;
- **modalità chiara/scura**, con preferenza locale nel browser;
- nuova sezione **Importa report**: acquisizione sicura di file .xls/.xlsx nella cartella privata /data/sources, associati all'A.A. e classificati come offerta/coperture o docenti di competenza; lettura della struttura e verifica duplicati;
- **Archivio**: azzeramento dell'A.A. selezionato o dell'intero archivio, solo admin, con password e doppia conferma; gli account sono preservati;
- gestione manuale per collaudo delle annualità dei CdS, con **esclusione/ripristino senza cancellazione**;
- multi-account con ruoli **admin**, **operatore** e **sola lettura**;
- login e sessioni proprie, autorizzazioni lato server, cookie HttpOnly e CSRF;
- accesso sia da **Home Assistant Ingress** sia dalla porta dedicata **8097/tcp**, utilizzabile da Cloudflare Tunnel protetto da Access;
- database SQLite persistente separato dal repository.

**Non implementati in questa versione:** mappatura semantica delle colonne del report importato, generazione e reimportazione XLSX per SSD, gestione dei referenti SSD e avvisi regolamentari. L'importazione attuale archivia il file e ne legge la struttura; **non importa ancora le assegnazioni nel modello didattico**.

I controlli su GitHub includono test sintetici, verifica sintattica Python e build dell'immagine Docker. La riuscita della build **non sostituisce** il collaudo su Home Assistant e sul tunnel.

Vedere [Installazione e sicurezza del tunnel](didaup/DOCS.md), [Decisioni confermate](docs/REQUISITI_2026_2027.md), [Policy privacy](docs/PRIVACY.md), [Architettura](docs/ARCHITETTURA.md) e [Specifiche interfaccia](docs/UI_UX.md).

## Prossimi input
Il report procedurale 2026/27 servirà a validare il tracciato di importazione, i ruoli, i controlli e il layout Excel. Eventuali dati assenti: **[DA VERIFICARE]**.

## Evoluzione 0.1.5-alpha1 — mappatura
- Per ogni Excel importato, la Segreteria può scegliere il foglio, indicare la riga delle intestazioni e associare manualmente le colonne ai campi previsti.
- Si conservano separatamente SSD insegnamento e SSD docente, sia nella vecchia sia nella nuova codifica. Le altre colonne possono rimanere non associate.
- Il sistema memorizza una bozza versionata della mappatura, con avvisi sui campi mancanti e blocco in caso di assegnazioni duplicate della stessa colonna.
- Questa funzione **non acquisisce ancora le coperture come dati validati** e non genera ancora Excel destinati ai referenti.
- Le anteprime restano nell'add-on, riservate agli operatori: nessun contenuto dei documenti viene pubblicato su GitHub.
 
## Riconoscimento automatico 2026/27
Il tracciato a 36 colonne fornito dall'utilizzatore è riconoscibile in **Importa report → Mappa colonne → Riconosci automaticamente**. Il sistema propone foglio, riga delle intestazioni e mappatura senza chiedere l'associazione manuale di tutte le colonne.

**Uniche tre colonne di variazione:** Nuovo docente, Ore, Note. Le altre sono informazioni storiche e di contesto da mantenere non modificabili nei futuri XLSX. La lettura delle intestazioni e il salvataggio della mappatura **non** importano ancora incarichi o generano i file per i referenti.

## Report originale e modello Excel per i referenti
Il report di offerta e coperture è una fonte ampia da mappare e verificare; non ha per forza la stessa struttura del modello Excel ridotto inviato ai referenti. Nella versione 0.1.5 la mappatura automatica distingue questi due tracciati. **Nuovo docente, Ore, Note** sono campi di *output* da compilare per le variazioni, non campi obbligatori di *input* del report ufficiale. La generazione dei nuovi XLSX non è ancora implementata.
