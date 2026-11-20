# DidaUP — Installazione e collaudo (0.1.5-alpha1)

> Versione iniziale di sviluppo **non collaudata su una specifica istanza di Home Assistant**. Usare soltanto dati sintetici. Non caricare file reali dell'Ateneo.

## Installazione locale da repository privato

Il repository GitHub è **privato**. Non trattarlo come un repository pubblico per l'Add-on Store di Home Assistant.

1. Sul proprio PC, ottenere il codice con accesso GitHub autorizzato. **Non incorporare un token nell'URL del repository**.
2. Copiare **solo il contenuto della cartella `didaup/`** nella cartella dei componenti aggiuntivi locali di Home Assistant, per esempio `/addons/didaup/`. Nella cartella deve esserci `config.yaml` insieme a `Dockerfile`, `run.sh` e `app/`.
3. Aggiornare l'elenco dei componenti aggiuntivi locali tramite Home Assistant.
4. Aprire la configurazione DidaUP e impostare `bootstrap_username` e una `bootstrap_password` **unica di almeno 12 caratteri**. La password viene usata solo per la prima creazione dell'utente amministratore.
5. Avviare DidaUP. Dopo il primo accesso, aggiornare la password dall'area Sicurezza e **rimuovere `bootstrap_password` dalle opzioni**. La rimozione non elimina gli utenti già presenti.
6. Usare il selettore in alto per cambiare A.A.; il database viene mantenuto sotto la directory persistente `/data`.

Le operazioni amministrative e l'archivio non vengono esportati in GitHub.


## Recupero dell'account amministratore senza cancellare i dati

Se DidaUP risponde **Credenziali non valide** anche usando la password iniziale:

1. Accedere in Home Assistant come amministratore e aprire **DidaUP → Configurazione**.
2. Inserire temporaneamente una password nuova e robusta nel campo `admin_recovery_password` (almeno 12 caratteri). **Non** modificare `bootstrap_password` come metodo di recupero: viene usato soltanto quando il database non contiene utenti.
3. Salvare la configurazione e **riavviare l'add-on**. La procedura di recupero reimposta soltanto l'account specificato da `bootstrap_username`, revoca le sessioni di quell'account e cancella i tentativi di accesso falliti. Non elimina il database, le annualità o altri utenti.
4. Accedere con `bootstrap_username` e la nuova password.
5. Dopo aver verificato l'accesso, **rimuovere `admin_recovery_password` dalla configurazione e salvare**. È una credenziale amministrativa temporanea e non deve restare salvata nelle opzioni dell'add-on.
6. Dalla sezione Sicurezza di DidaUP cambiare la password con una definitiva e non riutilizzata.

Il sistema conserva una verifica salata dell'ultima password di recupero, così la stessa richiesta **non viene ripetuta ai riavvii successivi**. Per una nuova procedura di recupero è necessario usare una password diversa.

La password e il suo valore non vanno inseriti in GitHub, messaggi, screenshot o issue. Se si utilizza un backup precedente alla correzione, verificare la versione e seguire nuovamente questa procedura.


## Porta e tunnel

- Porta TCP interna dell'applicazione: **8097**.
- Porta host preimpostata nella configurazione dell'add-on: **8097**, modificabile nella scheda **Rete** di Home Assistant in caso di conflitto.
- Accesso tramite Ingress: rimane disponibile nella barra laterale di Home Assistant.
- Per Cloudflare Tunnel, configurare nel tunnel un hostname protetto con origine HTTP **all'indirizzo LAN di Home Assistant e alla porta host configurata**, senza aprire port forwarding sul router.
- Nella configurazione Cloudflare attivare **Access / Zero Trust** con utenti o gruppi autorizzati e autenticazione forte. Un semplice hostname pubblico senza Access non è sufficiente.
- Abilitare HTTPS lato browser; mantenere `secure_cookies: true` per qualsiasi accesso remoto.
- Se si collauda **esclusivamente in HTTP su una LAN isolata, senza tunnel**, si può impostare temporaneamente `secure_cookies: false`. Riportare il valore a true prima di usare HTTPS o il tunnel.

**Non creare un URL pubblico anonimo per DidaUP.** L'applicazione richiede comunque il proprio login, anche quando il browser passa da Ingress o da Cloudflare Access.

## Importazione Excel e tema

1. Aprire DidaUP e selezionare **2026/27** o un altro A.A. nel selettore superiore.
2. Aprire **Importa report** dal menu laterale.
3. Selezionare **Offerta didattica e coperture storiche** per il report principale, oppure **Docenti di competenza** per il report carichi.
4. Caricare il file in formato `.xls` o `.xlsx`, massimo **32 MB**. Al termine compaiono l'elenco dei fogli, numero di righe e colonne e stato **Acquisito · Da mappare**.
5. L'importazione registra hash, data, anno e categoria; se il file identico è già stato acquisito nella medesima categoria/A.A., il sistema lo segnala e non lo duplica.

L'importazione **non ha ancora una mappatura semantica** dei docenti, SSD o incarichi. Conserva l'originale nel volume privato dell'add-on e rende disponibili i metadati; i successivi controlli amministrativi saranno introdotti dopo la verifica del tracciato effettivo. Non caricare file dell'Ateneo nel laboratorio domestico, anche se protetto da password.

La modalità chiara/scura si cambia dal pulsante **Tema** in alto (anche sulla schermata di accesso). La preferenza è memorizzata nel browser, non nel database o su GitHub.

## Azzeramento archivio

Menu **Archivio** (solo amministratore):
- **Solo anno selezionato**: elimina le annualità censite e i report archiviati per l'A.A. corrente, senza cambiare altri anni.
- **Tutto l'archivio**: elimina dati e report di tutti gli anni e ripristina il contenitore iniziale vuoto 2026/27.
- Entrambe le modalità richiedono **conferma testuale esatta**, **password amministratore** e una finestra di conferma finale.
- **Account, permessi e registro tecnico** non vengono cancellati.

**Attenzione:** azzeramento irreversibile, non sostituisce una strategia di backup. Salvare eventuali copie necessarie su un sistema autorizzato prima di procedere. Eliminare il file sorgente dall'app non modifica l'originale conservato altrove (es. OneDrive/SharePoint).

## Utenti e ruoli

- **Amministratore**: crea account, modifica ruoli e abilita/disabilita gli utenti, gestisce gli A.A. e i dati di lavoro.
- **Operatore**: seleziona l'A.A., censisce e include/esclude annualità dei CdS.
- **Sola lettura**: consulta gli anni accademici e le annualità senza modificarli.
- **Referenti SSD**: non vengono registrati come utenti, perché lavoreranno esclusivamente sugli XLSX.

Il backend applica i permessi agli endpoint, indipendentemente dagli elementi mostrati nella pagina. Password con hash salato PBKDF2, sessioni casuali archiviate tramite hash, cookie HttpOnly/SameSite, token CSRF, limitazione dei tentativi di accesso e log tecnici degli eventi privi di contenuto amministrativo.

## Limiti attuali

La versione 0.1 è un **primo nucleo tecnico**, non l'applicazione finale:
- acquisisce e ispeziona il file `.xls`, ma **non mappa ancora gli incarichi e le assegnazioni**;
- non genera né acquisisce XLSX dei referenti SSD;
- non automatizza la distribuzione via email o SharePoint;
- non integra ancora regole e avvertenze del regolamento;
- non dispone ancora di test di sicurezza end-to-end e collaudo su tunnel reale.

Prima di utilizzare dati dell'Ateneo sono necessari autorizzazioni, revisione della sicurezza, verifica del trattamento dei dati e collaudo sull'infrastruttura appropriata.

## Mappatura delle colonne: 0.1.5-alpha1

Dopo aver acquisito un report sintetico, aprire **Importa report → Mappa colonne**. Selezionare il foglio e la riga delle intestazioni (da 1 a 40), poi premere **Leggi colonne**. Associare le colonne del report ai campi proposti e scegliere **Salva mappatura in bozza**.

La mappatura distingue codifica precedente e nuova dell'SSD dell'insegnamento e dell'SSD del docente; il report dei docenti ha campi separati. Le colonne non pertinenti possono restare non associate. Sono segnalate informazioni mancanti e associazioni non valide. Il file originario resta immutato e la mappatura è versionata.

**Importante:** la mappatura non importa ancora incarichi e docenti nelle tabelle didattiche e non genera gli Excel per i referenti. Occorreranno riconciliazione del report, controlli e verifica amministrativa.

Non condividere screenshot di anteprime con nominativi o dati reali. Il collaudo domestico resta riservato a dati sintetici.
 
## 0.1.5-alpha1 — riconoscimento automatico del tracciato referenti

In **Importa report → Mappa colonne**, DidaUP prova a riconoscere automaticamente foglio e intestazioni del tracciato Excel dei referenti condiviso per il 2026/27. Dopo il riconoscimento sono proposte le corrispondenze; la verifica manuale si trova in una sezione ripiegabile, da utilizzare soltanto quando occorre.

La struttura dichiarata prevede **36 intestazioni**, delle quali **soltanto tre erano destinate a variazioni: `Nuovo docente`, `Ore`, `Note`**. Nella futura generazione degli XLSX tutte le altre colonne dovranno rimanere informative e protette; la protezione va accompagnata da controllo al reimport.

Per evitare interpretazioni sbagliate, `SSD INSEGNAMENTO` rimane una codifica non qualificata fino a verifica. La colonna `CODICE SSD DOCENTE NUOVO` è informativa sul docente storico e **non** corrisponde al nuovo docente proposto. `Ore` della proposta è distinta dalle ore previste ed effettive.

Il riconoscimento avviene **solo quando le intestazioni corrispondono esattamente** al modello dichiarato (maiuscole/spazi normalizzati), senza inventare equivalenze. Non registra automaticamente la proposta: è necessario **Salva mappatura in bozza**. Se la corrispondenza non è affidabile, si utilizza la mappatura manuale.

Le coperture storiche e i dati personali restano nell'archivio privato dell'add-on, non sono riportati su GitHub. La mappatura non crea ancora i nuovi Excel né normalizza le coperture.

## 0.1.5-alpha1 — distinzione report sorgente / Excel referenti

Il report originale contiene un tracciato più ampio (nella schermata di collaudo: 110 colonne) rispetto all'Excel ridotto distribuito ai referenti. **Non devono essere mappate tutte le colonne del report sorgente su un elenco ridotto**; è sufficiente identificare con certezza le informazioni necessarie a ricostruire l'attività.

La mappatura automatica riconosce anche le intestazioni `DIPARTIMENTO DI RIFERIMENTO`, `SCUOLA` e `TIPOLOGIA` osservate nell'origine. L'identificazione avviene soltanto per corrispondenza esatta dell'etichetta, normalizzando maiuscole e spazi. I campi non riconosciuti rimangono disponibili per la correzione manuale.

**`Nuovo docente`, `Ore`, `Note` non sono campi da ricercare obbligatoriamente nel report sorgente.** Sono invece le tre colonne di proposta che DidaUP dovrà aggiungere nel futuro Excel per i referenti e lasciare modificabili. Tutte le altre colonne dell'Excel distribuito sono informative e protette; la verifica contro lo storico dovrà avvenire anche al reimport.

La mappatura attuale è ancora una **bozza**, non una normalizzazione definitiva degli incarichi. Le righe del report e la deduplicazione delle coperture devono essere verificate prima di generare un nuovo Excel.

## 0.1.6-alpha1 — identificativo tecnico delle righe importate

Nel report originale potrebbe **non esistere** una colonna che contenga un ID ufficiale univoco per ogni copertura. Il precedente avviso `ID copertura storica: da verificare prima della riconciliazione` era quindi fuorviante ed è stato rimosso; eventuali mappature già salvate visualizzano immediatamente gli avvisi ricalcolati, senza obbligare a rifare l'importazione.

Se disponibile, un ID ufficiale potrà essere associato come campo opzionale. La funzione `source_row_id` prepara un identificativo tecnico univoco **all'interno del singolo report importato**, calcolato da hash del file, nome foglio e numero di riga originale. Non costituisce identificativo UGOV e **non è ancora applicato ai dati storici** nell'attuale alpha.

Per identificare le *coperture* e riconciliarle tra estrazioni differenti sarà necessaria una fase successiva di validazione delle chiavi effettive del report (attività, modulo, discriminanti, docenti, ore). Le righe identiche o le coperture multiple non devono essere unite automaticamente. Nessun identificativo ufficiale viene inventato.
