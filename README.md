# DidaUP

**Add-on per la programmazione didattica 2027/28 con cinque Excel completi e identici destinati ai dipartimenti.**

> Stato: **0.1.10-alpha12 (filtro Tipologia e riconoscimento denominazioni CdS estese)**. Nessuna procedura 2027/28 o codifica SSD è considerata approvata o verificata. **Solo dati sintetici** durante il collaudo.

## Obiettivo
Partire dall'offerta e dalle coperture storiche **2026/27** per costruire un archivio di riferimento verificabile. Quando saranno disponibili le estrazioni ufficiali, predisporre i fogli di programmazione **2027/28** senza trasporre automaticamente come valide assegnazioni, codici o nominativi precedenti.

## Ambito prioritario
Il primo caso d'uso riguarda i **referenti SSD dell'area medica**, già condivisi con il progetto nei materiali del procedimento 2026/27. La lista dei referenti è una fonte di lavoro, non una conferma automatica per il 2027/28; nominativi, competenze e designazioni del nuovo anno sono **[DA VERIFICARE]**. Non trasferire nominativi o allegati originali su GitHub.

## Regolamento per l'attribuzione dei compiti didattici
Il regolamento già fornito è un riferimento essenziale da analizzare durante lo sviluppo: le regole applicabili dovranno essere evidenziate negli Excel dei referenti come **istruzioni, avvertenze e controlli verificabili**, con il riferimento alla disposizione in vigore. Non inventare obblighi, soglie o condizioni, né introdurre blocchi automatici prima di validare le fonti.

## Utilizzatori
- Segreteria: importazione, produzione di cinque file Excel identici, revisione preliminare dei cinque file, controlli e riepiloghi.
- Referenti SSD: **solo i file .xlsx condivisi sul OneDrive d'Ateneo**, senza accesso all'add-on. La pubblicazione automatica su OneDrive resta [DA IMPLEMENTARE].

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
- **Archivio**: azzeramento dei soli file di lavorazione rigenerabili, mai delle mappature, delle esclusioni CdS, dei report sorgenti o degli anni accademici; solo admin con password e doppia conferma;
- gestione manuale per collaudo delle annualità dei CdS, con **esclusione/ripristino senza cancellazione**;
- multi-account con ruoli **admin**, **operatore** e **sola lettura**;
- login e sessioni proprie, autorizzazioni lato server, cookie HttpOnly e CSRF;
- accesso sia da **Home Assistant Ingress** sia dalla porta dedicata **8097/tcp**, utilizzabile da Cloudflare Tunnel protetto da Access;
- database SQLite persistente separato dal repository.

**Implementati:** mappatura versionata delle colonne, scelta delle annualità, generazione di cinque file identici e protetti, download ZIP e analisi preliminare delle cinque restituzioni con controllo di sovrapposizioni e integrità dello storico. **Non implementati:** condivisione OneDrive automatica, «+» realmente incorporato nei cinque file, acquisizione definitiva/versionata delle proposte, gestione autorizzazioni dei referenti, esito amministrativo e approvazioni.

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

**Quattro colonne modificabili concordate:** Tipo variazione, Nuovo docente, Ore, Note. Le altre sono informazioni storiche e di contesto da mantenere non modificabili nei futuri XLSX. La lettura delle intestazioni e il salvataggio della mappatura non approvano incarichi; i cinque file completi si generano separatamente nella sezione **Genera Excel**.

## Report originale e modello Excel per i referenti
Il report di offerta e coperture è una fonte ampia da mappare e verificare; non ha per forza la stessa struttura del modello Excel ridotto inviato ai referenti. Nella versione 0.1.5 la mappatura automatica distingue questi due tracciati. **Nuovo docente, Ore, Note** sono campi di *output* da compilare per le variazioni, non campi obbligatori di *input* del report ufficiale. La generazione delle cinque copie identiche è implementata; non include ancora la pubblicazione automatica su OneDrive.

## Selezione annualità CdS (0.1.8-alpha1)
La schermata **Annualità CdS** propone un elenco a spunte ricavato dal report mappato: ricerca rapida per codice/nome/sede/anno, selezione limitata ai risultati visibili, riepilogo di tutte le esclusioni, motivazione e conferma finale. Un raggruppamento rappresenta una combinazione codice CdS + sede + anno di corso. Le esclusioni non cancellano righe né modificano il report originale. Questo passaggio è preliminare alla futura generazione degli Excel per SSD.

## Protezione delle mappature e delle esclusioni (0.1.9-alpha1)
L'azione **Azzera soltanto le elaborazioni** non cancella le annualità censite, gli stati di inclusione/esclusione e le motivazioni, le mappature, i documenti Excel importati, la cronologia e gli account. Cancella esclusivamente eventuali output di lavoro rigenerabili; **attualmente non esistono ancora output generati** e l'operazione può non eliminare alcun elemento. Usare un backup recente Home Assistant per proteggere il database e i file sorgenti da danni o disinstallazioni.


## Evoluzione 0.1.10-alpha1 — Cinque Excel completi e controllo delle sovrapposizioni

La sezione **Prepara Excel** crea un **ZIP con cinque copie identiche per i referenti e un sesto Excel interno con le righe escluse**. I cinque file per i referenti contengono le attività incluse nel perimetro storico selezionato. **Nessun criterio dipartimentale filtra le righe**: la suddivisione per file riguarda soltanto il canale di compilazione da parte dei referenti. Eventuali annualità già esplicitamente escluse nell'archivio non sono reintrodotte automaticamente. I file contengono **37 colonne visibili** (33 informazioni storiche più **Tipo variazione, Nuovo docente, Ore, Note**), identificativi interni nascosti, protezione per evitare modifiche accidentali e filtro di foglio. La colonna **`TOT ORE EFFETTIVE` è calcolata**: i precedenti valori del report non vengono riutilizzati. Nella sezione **Calcolo carico**, per ciascun A.A. l'amministratore configura regole a percentuale o a quota fissa delle **`TOT ORE PREVISTE`**, selettive per tipologia, CdS e TAF. Le righe senza regola partono da zero; conflitti e dati non validi bloccano l'esportazione. Le cinque copie ricevono gli stessi valori, verificati anche al reimport.

Dopo la compilazione, è disponibile un endpoint e una schermata per una **revisione preliminare di cinque XLSX**: il sistema confronta ogni riga con lo storico privato, rileva trasferimenti di ore in eccesso e segnala attività modificate da più dipartimenti, **anche se riguardano docenti storici differenti**. Le sovrapposizioni non vengono sommate, risolte o approvate automaticamente. Gli XLSX caricati per la revisione sono file temporanei cancellati a fine analisi, e non sono acquisiti come proposte approvate.

**Limiti della versione:** i cinque XLSX sono attualmente distribuiti in ZIP e devono essere pubblicati manualmente sull'account universitario autorizzato; non vi è un pulsante Excel «+» già operativo nel file esportato. È presente uno script Office Scripts sperimentale per aggiungere variazioni, ma va ancora associato e verificato nell'ambiente Microsoft 365 dell'Ateneo. L'applicazione continua a consentire **soltanto dati sintetici** per importazione e revisione.


## Nuova selezione multipla delle annualità (0.1.10-alpha11)

Nella maschera **Annualità CdS** puoi combinare ricerca, selezione multipla di più CdS, più sedi e più anni di corso. Il filtro di stato include **Solo modifiche non salvate**. I filtri non cambiano le esclusioni nel database: i pulsanti per escludere/includere in blocco modificano solo le spunte delle righe **visualizzate**, dopo conferma; il salvataggio effettivo avviene con il pulsante dedicato. Puoi cancellare i filtri senza perdere le spunte e annullare la bozza senza modificare le esclusioni registrate.

Il riquadro **Registro delle annualità già salvate** dispone di ricerca e filtro per incluse/escluse e mostra esclusivamente lo stato persistito. I cinque Excel generati mantengono lo stesso contenuto in tutte le copie ma ora comprendono nel **nome del file** una revisione diversa a ogni generazione, per non confonderli con quelli già caricati su OneDrive. Nessun documento già caricato viene automaticamente sostituito.

Attenzione: una riga originale con annualità multiple oppure con identificativi ambigui non deve essere interpretata come certezza di appartenenza; verificare gli avvisi di generazione prima di distribuire i file.
