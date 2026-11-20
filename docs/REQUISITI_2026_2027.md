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

## Seconda fonte 2026/27: docenti di competenza
- Il report `carichi_docenti_Scuola di medicina_2026_2027.xls`, condiviso dall'utilizzatore, rappresenta l'**elenco dei docenti di competenza** per l'area medica.
- Va trattato come **fonte distinta** dal report unico dell'offerta/coperture 2026/27: il primo identifica i docenti di competenza, il secondo le attività e le assegnazioni storiche.
- Usare l'elenco per popolare, dopo verifica della struttura e delle chiavi, la selezione guidata dei docenti nei futuri XLSX; resta possibile proporre un docente non presente mediante inserimento libero, da sottoporre a verifica.
- **Non assumere** che l'SSD di competenza, l'SSD dell'insegnamento e l'SSD del docente coincidano. Un docente può essere assegnato a più insegnamenti o SSD.
- L'elenco del 2026/27 **non dimostra da solo** competenze o afferenze valide per il 2027/28: per il nuovo anno occorrerà verificare aggiornamenti e fonte ufficiale.
- Non copiare contenuto, nominativi, codici o file originali nel repository GitHub, neppure se privato.
- **[DA VERIFICARE]**: intestazioni/chiavi effettive, campi SSD e carichi presenti nel file; la denominazione del report non basta per dedurne la struttura.

## Evoluzione 0.1.3-alpha1 — mappatura
- Per ogni Excel importato, la Segreteria può scegliere il foglio, indicare la riga delle intestazioni e associare manualmente le colonne ai campi previsti.
- Si conservano separatamente SSD insegnamento e SSD docente, sia nella vecchia sia nella nuova codifica. Le altre colonne possono rimanere non associate.
- Il sistema memorizza una bozza versionata della mappatura, con avvisi sui campi mancanti e blocco in caso di assegnazioni duplicate della stessa colonna.
- Questa funzione **non acquisisce ancora le coperture come dati validati** e non genera ancora Excel destinati ai referenti.
- Le anteprime restano nell'add-on, riservate agli operatori: nessun contenuto dei documenti viene pubblicato su GitHub.

## Tracciato XLSX referenti 2026/27 — conferma dell'utilizzatore

Nel file Excel distribuito ai referenti nell'annualità precedente, **le uniche tre colonne compilabili per le variazioni erano `Nuovo docente`, `Ore`, `Note`**. Tutte le altre colonne avevano valore informativo, inclusi dati dell'insegnamento e dati delle coperture già assegnate, e devono rimanere **non modificabili** nella futura generazione XLSX.

Regole funzionali:
- `Nuovo docente`: propone il docente in sostituzione o aggiunta, da contestualizzare rispetto alla copertura esistente.
- `Ore`: indica le ore **della proposta**, da non confondere con `OREPREVLEZ`, `TOT ORE PREVISTE`, `TOT ORE EFFETTIVE`.
- `Note`: motivazioni e osservazioni sulla variazione; anche una nota senza modifica docente/ore deve essere acquisita come comunicazione.
- Tutte e tre le celle vuote: **nessuna variazione comunicata**; non rappresenta approvazione formale.
- L'assenza di una nuova assegnazione non cancella né invalida la copertura storica. La rimozione intenzionale di un incarico richiederà un'azione esplicita nel futuro flusso **[DA DEFINIRE]**.
- Il report può contenere incarichi in SSD diversi da quello del docente. La divergenza deve essere segnalata, ma senza alterare la copertura.
- `SSD INSEGNAMENTO` non dichiara da sola la codifica vecchia/nuova: non attribuire tale qualificazione senza fonte.
- `CODICE SSD DOCENTE NUOVO` è un attributo informativo del **docente storico**, non un campo della nuova proposta (omonimia della parola «NUOVO» da evitare).

### Automatizzazione della mappatura
Il software può proporre associazioni in modo deterministico **solo quando trova le etichette esatte del tracciato condiviso** (tollerando maiuscole e spazi); non deve dedurre corrispondenze per semplice somiglianza nei nomi. Se il tracciato non corrisponde, si mantiene la mappatura manuale. La proposta automatica non sovrascrive i dati e deve essere confermata dall'operatore.

## Chiarimento sul report sorgente da schermata DidaUP
La schermata ricevuta mostra un import Excel per 2026/27 con 11.735 righe e 110 colonne, mentre le 36 intestazioni fornite per il file distribuito ai referenti descrivono un **tracciato di output** più compatto. La futura elaborazione non deve imporre la stessa mappatura ai due tracciati. La distinzione tra dati fonte e campi di proposta è stata recepita nell'alpha 0.1.5.

## ID copertura storica — chiarimento funzionale

Nel report 2026/27 l'identificativo ufficiale univoco della singola copertura **non è stato ancora verificato**. L'assenza di una colonna etichettata come tale non deve causare un avviso di incompletezza di mappatura: il campo è **facoltativo** e sarà usato soltanto se effettivamente presente nel tracciato.

Per mantenere distinte le righe senza modificarle si potrà usare un ID tecnico interno, derivato da impronta del file sorgente, foglio e numero di riga originale. Questo ID serve esclusivamente alla tracciabilità nello snapshot; non dimostra che due righe di anni o importazioni differenti si riferiscano alla stessa copertura. La futura riconciliazione dovrà impiegare i riferimenti ufficiali disponibili e rilevare casi ambigui, co-docenze, frazionamenti e duplicazioni.

## Protezione permanente delle impostazioni durante l'azzeramento (conferma utente)
Qualsiasi azzeramento delle lavorazioni deve mantenere tutte le mappature salvate e le associazioni CdS/anno/sede incluse o escluse, con le motivazioni e i riferimenti alle fonti. Per non generare riferimenti orfani, preservare anche i report originali importati, l'A.A. e la cronologia. Implementare un archivio separato per output temporanei rigenerabili; la cancellazione integrale del database o delle fonti **non fa parte** dell'operazione ordinaria di azzeramento. Verificare per test sia il singolo A.A. sia tutti gli A.A., anche dopo un riavvio.


## Regole operative confermate per XLSX referenti 2027/28

Decisioni esplicite dell'utilizzatore (definizioni funzionali; **nessuna modifica automatica agli incarichi prima di approvazione**):

1. Per coperture con più docenti, mantenere **una riga per ciascun docente** dello storico; non accorpare le ore di docenti differenti.
2. Comprendere anche le attività **senza docente assegnato**.
3. Aggiungere **Tipo variazione** come quarta colonna modificabile del futuro Excel, accanto a **Nuovo docente, Ore, Note**. Le categorie definitive e la loro semantica saranno precisate prima dell'implementazione.
4. Per il campo **Ore** lasciato vuoto, è stata concordata l'adozione delle ore storiche nei casi applicabili; **la regola particolare per sostituzione parziale e aggiunta è ancora da definire**.
5. Il criterio di distribuzione ai referenti SSD è l'**SSD dell'insegnamento**, non quello del docente storico.
6. **Nuovo docente**: selezione assistita dall'elenco dei docenti, con possibilità di inserire un nominativo non presente, da verificare.
7. L'assenza di variazioni nel file restituito equivale a **conferma da parte del referente**, non all'approvazione formale dell'affidamento per il nuovo A.A.
8. Esplicitare sempre **storico 2026/27** e **proposta 2027/28** come dati distinti.
9. **Unico riferimento per i calcoli delle ore della copertura storica: `TOT ORE EFFETTIVE`.** Non usare `OREPREVLEZ`, `TOT ORE PREVISTE` o altri campi come base dei trasferimenti/sostituzioni. Tali colonne possono rimanere come dati informativi, ove necessario.

### Sostituzione parziale: significato del campo Ore CONFERMATO

Esempio fittizio: storico A=20 ore, B=10 ore; proposta di trasferire 12 ore da A a C, con risultato A=8, B=10, C=12. Ipotesi di inserimento sul record storico A: **Tipo variazione=Sostituzione parziale, Nuovo docente=C, Ore=12**. In tale ipotesi, il campo Ore indica le **ore trasferite**; per evitare ambiguità dovrebbe essere obbligatorio e maggiore di zero e minore delle ore storiche del docente interessato. **Regola confermata dall'utente:** in sostituzione parziale il campo **Ore indica le ore trasferite al nuovo docente**, non quelle residue del docente storico. I dati storici non vengono modificati. I controlli di coerenza (ore trasferite, ore residue e totale) dovranno essere implementati prima del reimport. Il valore vuoto delle ore nella sostituzione **totale** manterrebbe la regola concordata: assumere `TOT ORE EFFETTIVE` della singola riga docente; non dell'intero modulo.

È ancora da definire la semantica del campo Ore nelle **aggiunte** e nelle **modifiche ore** (ore finali oppure differenza); nessuna assunzione automatica su questi due casi finché non confermata.

**Esempio di calcolo confermato:** `TOT ORE EFFETTIVE` docente storico A = 20; sostituzione parziale con nuovo docente C e Ore = 12; proposta: A rimane per 8 ore, C assume 12 ore. La riga del docente B, eventualmente presente nello stesso modulo, resta autonoma. Il totale storico deve restare verificabile, senza applicare modifiche al report fonte.
