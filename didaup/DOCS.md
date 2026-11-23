# DidaUP — Installazione e collaudo (0.1.10-alpha19)

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

## Azzeramento sicuro delle elaborazioni (0.1.9-alpha1)

Menu **Archivio** (solo amministratore): la funzione **Azzera soltanto le elaborazioni** è un'operazione limitata ai file di lavoro rigenerabili registrati nella tabella `working_artifacts` e conservati separatamente sotto `/data/working`.

Per **uno specifico anno** oppure per **tutti gli anni**, vengono sempre conservati:
- le annualità censite e gli stati **inclusa / esclusa**, con le relative motivazioni e versioni;
- i file XLS/XLSX di origine in `/data/sources`, i relativi metadati e le **mappature salvate**;
- la cronologia delle selezioni/esclusioni, gli anni accademici, gli utenti e il registro tecnico.

Il reset richiede la password amministrativa e una nuova conferma testuale: `AZZERA LAVORAZIONE 2026/27` per l'A.A. indicato (il codice effettivo è mostrato dall'interfaccia), oppure `AZZERA LAVORAZIONI` per tutte le annualità. Le **vecchie formule di conferma non sono più valide**, per prevenire azzeramenti accidentali effettuati da vecchie schermate.

Nella versione corrente vengono prodotti pacchetti ZIP dei cinque Excel identici: l'azzeramento rimuove questi output rigenerabili, **non** i report sorgenti né le mappature. È comunque registrato nell'audit. La conservazione delle impostazioni è verificata anche da test che simulano un riavvio dell'app.

**Non è un backup:** cancellazione dell'add-on o del suo volume `/data`, danni al database e ripristini di backup precedenti possono comunque far perdere dati. Prima di aggiornare l'add-on, verificare di avere un backup Home Assistant recente; la copia dovrebbe includere database e file locali dell'add-on.

## Utenti e ruoli

- **Amministratore**: crea account, modifica ruoli e abilita/disabilita gli utenti, gestisce gli A.A. e i dati di lavoro.
- **Operatore**: seleziona l'A.A., censisce e include/esclude annualità dei CdS.
- **Sola lettura**: consulta gli anni accademici e le annualità senza modificarli.
- **Referenti SSD**: non vengono registrati come utenti, perché lavoreranno esclusivamente sugli XLSX.

Il backend applica i permessi agli endpoint, indipendentemente dagli elementi mostrati nella pagina. Password con hash salato PBKDF2, sessioni casuali archiviate tramite hash, cookie HttpOnly/SameSite, token CSRF, limitazione dei tentativi di accesso e log tecnici degli eventi privi di contenuto amministrativo.

## Limiti attuali

La versione 0.1 è ancora un **ambiente di collaudo**, non l'applicazione finale:
- acquisisce, ispeziona e mappa le colonne dei file `.xls`/`.xlsx`, senza validare automaticamente gli affidamenti;
- **genera cinque XLSX completi e identici** in ZIP e dispone di un controllo preliminare dei cinque XLSX restituiti, senza ancora registrarli come proposte definitivamente acquisite;
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

## 0.1.7-alpha1 — associazioni duplicate dopo il riconoscimento

In alcune mappature salvate in precedenza, dopo **Riconosci automaticamente** rimanevano impostati anche campi non riconosciuti dal tracciato, perché l'interfaccia combinava la vecchia bozza con il nuovo suggerimento. Questo poteva far associare la stessa colonna contemporaneamente a più campi (es. SSD originale e SSD precedente).

**Correzione:** il riconoscimento automatico ora sostituisce completamente la selezione della bozza corrente. I campi non riconosciuti rimangono vuoti; un campo con un'etichetta generica non viene attribuito arbitrariamente alla codifica vecchia o nuova. Non è necessario eliminare i report acquisiti e il file sorgente rimane integro.

Al salvataggio, il controllo segnala ora la colonna e i nomi dei campi in conflitto, prima di inviare la modifica al server; il server mantiene un'ulteriore verifica indipendente. I vecchi abbinamenti vengono modificati solo quando l'operatore sceglie **Salva mappatura in bozza**.

Per ripartire da una mappatura che visualizza il conflitto:
1. aggiornare l'add-on alla **0.1.7-alpha1**;
2. aprire **Importa report → Mappa colonne** sul report già acquisito;
3. selezionare **Riconosci automaticamente**;
4. verificare che i campi non supportati siano **Non associata**, poi premere **Salva mappatura in bozza**.

L'aggiornamento non genera ancora incarichi né Excel per SSD: corregge esclusivamente la preparazione delle colonne.

## 0.1.8-alpha1 — selezione annualità con spunte e ricerca rapida

La funzione **Annualità CdS** dispone ora di una procedura di selezione massiva con ricerca istantanea:

1. Selezionare l'**anno accademico** e aprire **Annualità CdS**.
2. Nel riquadro **Seleziona le annualità da escludere**, scegliere il report dell'offerta già importato e mappato.
3. Premere **Ricava elenco dal report**: le righe vengono raggruppate per **codice CdS, sede e anno di corso**, senza perdere il documento originale; le righe duplicate del medesimo gruppo sono conteggiate.
4. Usare **Ricerca rapida** per filtrare per codice, denominazione, sede oppure anno. Le spunte significano **DA ESCLUDERE**.
5. I comandi **Spunta risultati visibili** e **Togli spunta ai risultati visibili** agiscono soltanto sui risultati filtrati; le spunte delle voci nascoste sono conservate.
6. Inserire una motivazione per le nuove esclusioni e premere **Salva le esclusioni selezionate**. DidaUP riepiloga il totale e richiede la conferma prima di intervenire.

Prima del salvataggio, la schermata è una **sola anteprima**: nessun archivio cambia. Al salvataggio vengono censite le annualità riconosciute e registrate le esclusioni con motivazione, senza alterare il file Excel originale. Le annualità non più presenti nel report selezionato sono preservate. I precedenti motivi di esclusione non vengono riscritti quando l'annualità resta esclusa.

**Verifiche di sicurezza:** mismatch dell'anno accademico, mappatura incompleta, codici/anni non validi, denominazioni CdS discordanti, anomalie nelle righe sorgente, cambiamenti concorrenti e abbinamenti provenienti da un altro report. Le anomalie sono mostrate come conteggio e non vengono incluse automaticamente nell'elenco: la conferma è esplicita.

L'identificazione non stabilisce ancora gli affidamenti o gli SSD e non genera Excel per i referenti. Nel laboratorio domestico devono continuare a essere utilizzati soltanto file sintetici.

## Correzione di sicurezza 0.1.9-alpha1
La vecchia funzione di azzeramento era distruttiva anche per le mappature e le esclusioni. Dalla versione 0.1.9-alpha1 il reset è espressamente ristretto agli output temporanei. Non utilizzare versioni precedenti per operazioni di azzeramento; aggiornare l'add-on prima di provare la funzione.


## Cinque file identici per dipartimento — collaudo 0.1.10-alpha1

1. Selezionare l'A.A. storico nel selettore e importare un report di **offerta didattica** esclusivamente sintetico.
2. Salvare la mappatura del report. Sono necessari codice CdS, sede e anno di corso; per applicare le regole di carico associare **TOT ORE PREVISTE** e i criteri effettivamente usati (**TIPOLOGIA**, **TAF**, codice CdS). **TOT ORE EFFETTIVE è un campo di output calcolato**: non deve essere associato. Le righe senza docente rimangono nell'export.
3. Aprire **Calcolo carico**, selezionare il report, configurare e salvare le regole per l'A.A. scelto, quindi usare **Calcola anteprima**. Ogni criterio (**Tipologia**, **CdS**, **TAF**) dispone di multiselettore con ricerca, spunte, **Seleziona visibili** e **Deseleziona tutte**. Più scelte nello stesso criterio sono alternative (OR); i criteri compilati sono combinati (AND); nessuna spunta significa «Tutti». **I multiselettori mostrano solo Tipologie CdS, codici CdS e TAF effettivamente presenti nelle righe mantenute nei cinque Excel**, applicando le medesime esclusioni per CdS, sede e annualità della generazione. Le annualità miste, mantenute nell'Excel, restano disponibili nei selettori. Se una regola già salvata fa riferimento a un CdS successivamente escluso, il valore non ricompare tra le opzioni: durante la modifica della regola viene evidenziato separatamente, con possibilità di rimuoverlo. Il testo sotto al report indica quante righe sono comprese nei selettori e quante escluse. Una sola regola prevale per riga: la più specifica tra Tipologia, CdS e TAF. Senza regola le ore effettive coincidono con **TOT ORE PREVISTE**, quando sono valide; il dato vuoto resta a 0 con avviso. È disponibile il terzo metodo **N.D. (non disponibile)**: la cella TOT ORE EFFETTIVE conterrà esattamente il testo **N.D.**, senza imputare ore né conteggiare la riga nel totale delle ore. La sigla è una scelta esplicita, distinta dal valore numerico zero. Ambiguità tra regole e quote fisse oltre le ore previste bloccano la generazione. Poi aprire **Prepara Excel** e premere **Genera 5 Excel + righe escluse**.
4. Scaricare lo ZIP: contiene cinque copie inizialmente identiche per i referenti, `Dipartimento_01` … `Dipartimento_05`, e un **sesto Excel riservato al controllo interno** delle righe effettivamente escluse. Non inviare il registro ai referenti. Le ore effettive nei cinque file iniziano sempre da 0 e vengono valorizzate soltanto attraverso le regole, senza alterare la fonte storica.
5. I file generati hanno 37 colonne visibili: 33 informative di storico e quattro compilabili (**Tipo variazione, Nuovo docente, Ore, Note**). Le colonne tecniche nascoste servono al controllo di integrità. La protezione senza password previene modifiche accidentali ma non sostituisce la validazione sul server.
6. L'apertura e la condivisione sul **OneDrive istituzionale** sono ancora operazioni manuali: l'add-on **non** pubblica automaticamente. **Non** caricare file veri nel laboratorio finché la destinazione e la sicurezza non sono state autorizzate.
7. Al rientro, caricare esattamente cinque XLSX compilati nella sezione **Controllo delle proposte restituite**. Il sistema esegue una **sola anteprima di verifica** su fonte, ID, ore e sovrapposizioni tra file e non salva alcun affidamento proposto o approvato. L'esito viene mostrato senza modificare gli archivi storici.

### Verifica di completezza dei cinque Excel

Ad ogni generazione DidaUP confronta **tutte le righe non vuote del foglio di offerta selezionato** con i due insiemi di destinazione: le righe mantenute in ciascuno dei cinque Excel per i referenti e le righe rimosse, presenti soltanto nel sesto Excel riservato al controllo interno. L'identità si basa sull'hash del report, sul foglio e sul numero di riga originale; due righe con contenuto identico sono comunque due record distinti.

La quadratura deve rispettare **righe sorgente = righe presenti in ciascuno dei cinque Excel + righe escluse**; nessuna riga può apparire in entrambi o più volte. Il generatore riapre inoltre l'XLSX effettivamente prodotto e il registro interno, verificando che tutti gli ID attesi siano stati scritti una sola volta e nello stesso ordine. In caso di riga mancante, extra o duplicata, l'archivio non viene consegnato e compare un errore. Il riepilogo della generazione e il sesto Excel riportano il conteggio delle righe.

Le righe con annualità composta, in cui soltanto alcuni anni risultano esclusi, **rimangono intere** nei file: DidaUP le segnala come da verificare, senza attribuirle automaticamente ai soli anni conservati. Il controllo di completezza riguarda la presenza delle righe: non sostituisce la verifica istruttoria dell'esattezza di codice CdS, annualità e associazioni, né certifica dati di produzione finché non viene effettuato un collaudo istituzionale.

Il tasto Excel **«+ Aggiungi variazione» non è ancora incorporato** nei file generati: è disponibile un Office Script sperimentale in `prototypes/office_scripts/aggiungi_variazione.ts`, da collaudare e associare al file master nel tenant Microsoft 365 dell'Ateneo. I cinque file non devono essere distribuiti per uso amministrativo definitivo prima di questa verifica e prima dell'implementazione delle autorizzazioni e del controllo istituzionale delle proposte.


## Nuova selezione multipla delle annualità (0.1.10-alpha11)

Nella maschera **Annualità CdS** puoi combinare ricerca, selezione multipla di più CdS, più sedi e più anni di corso. Il filtro di stato include **Solo modifiche non salvate**. I filtri non cambiano le esclusioni nel database: i pulsanti per escludere/includere in blocco modificano solo le spunte delle righe **visualizzate**, dopo conferma; il salvataggio effettivo avviene con il pulsante dedicato. Puoi cancellare i filtri senza perdere le spunte e annullare la bozza senza modificare le esclusioni registrate.

Il riquadro **Registro delle annualità già salvate** dispone di ricerca e filtro per incluse/escluse e mostra esclusivamente lo stato persistito. I cinque Excel generati mantengono lo stesso contenuto in tutte le copie ma ora comprendono nel **nome del file** una revisione diversa a ogni generazione, per non confonderli con quelli già caricati su OneDrive. Nessun documento già caricato viene automaticamente sostituito.

Attenzione: una riga originale con annualità multiple oppure con identificativi ambigui non deve essere interpretata come certezza di appartenenza; verificare gli avvisi di generazione prima di distribuire i file.


## 0.1.10-alpha19 — Diagnostica dei conflitti tra regole di carico

L'anteprima del carico identifica le regole che si sovrappongono con la stessa specificità. Il messaggio di errore riporta i numeri delle regole; la tabella diagnostica raggruppa ogni coppia di regole, conta le righe coinvolte e mostra alcune righe del report come esempio. La tabella delle regole è numerata per consentire di individuare immediatamente le configurazioni da correggere. Nessuna regola viene modificata o eliminata automaticamente: la precedenza tra regole di pari specificità deve essere decisa dall'amministratore.


## 0.1.10-alpha19 — Limite massimo delle ore effettive

Per ogni regola numerica (percentuale o quota fissa), **TOT ORE PREVISTE costituisce il tetto massimo** di TOT ORE EFFETTIVE. Se il risultato matematico, arrotondato a due decimali, supera le ore previste, il valore effettivo viene automaticamente ricondotto alle ore previste. La situazione non è più un errore bloccante. L'anteprima mostra il numero di righe su cui è stato applicato il limite e alcuni esempi con riga sorgente, numero della regola, ore previste e ore effettive. Il comportamento non si applica a N.D.; le celle previste vuote continuano a essere segnalate separatamente e mantenute a zero. Valori previsti non numerici o negativi e conflitti tra regole restano bloccanti.


## 0.1.10-alpha19 — Esclusione incarichi con filtri multipli

In **Prepara Excel** è presente una maschera di esclusione mirata per singolo incarico. Il Titolo affidamento è il criterio principale; Tipologia CdS, CdS, Sede, Annualità e TAF sono filtri facoltativi di restringimento. Le selezioni multiple all'interno di un filtro sono combinate con OR; filtri differenti sono combinati con AND. I valori disponibili sono estratti dalle righe che rimangono nel perimetro dopo le esclusioni per annualità. L'utente calcola un'anteprima prima di salvare i criteri. I criteri sono versionati per report e anno accademico e legati a hash della fonte, versione della mappatura e revisione delle annualità. Se uno di questi elementi cambia, la generazione è bloccata fino a nuova verifica e salvataggio. Le righe escluse per i nuovi criteri sono inserite nel registro interno delle esclusioni con motivazione e criteri applicati; i cinque Excel restano identici tra loro. Nessuna riga già esclusa per annualità viene conteggiata due volte.
