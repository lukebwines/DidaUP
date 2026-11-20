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

Nelle **aggiunte**, è confermato che il campo **Ore** esprime le ore **cedute dal docente storico indicato nella riga**, non le ore residue né un incremento del totale. Nelle **modifiche ore** non collegate a un trasferimento, la semantica rimane **[DA DEFINIRE]**; non applicare interpretazioni automatiche non confermate.

**Esempio di calcolo confermato:** `TOT ORE EFFETTIVE` docente storico A = 20; sostituzione parziale con nuovo docente C e Ore = 12; proposta: A rimane per 8 ore, C assume 12 ore. La riga del docente B, eventualmente presente nello stesso modulo, resta autonoma. Il totale storico deve restare verificabile, senza applicare modifiche al report fonte.

### Aggiunta docente: redistribuzione delle ore, non aumento del totale — CONFERMATO

Decisione esplicita dell'utilizzatore: quando un referente propone di **aggiungere un docente** a un modulo già coperto, le ore assegnate al nuovo docente devono essere **prelevate dalle ore esistenti**; il totale delle ore del modulo **non aumenta**.

Esempio esclusivamente illustrativo (dati fittizi): docente storico A con `TOT ORE EFFETTIVE` = 20; proposta di aggiunta del docente C con `Ore` = 8; se le ore sono prelevate da A, la distribuzione proposta è A=12 e C=8, totale invariato 20. Il dato storico A=20 rimane immutato nella fonte.

Controlli da prevedere per l'elaborazione: ore trasferite positive, non superiori alle ore disponibili nel/i docente/i di origine, saldo delle ore proposte corrispondente al saldo storico dell'attività/modulo, segnalazione di incongruenze o ambiguità prima dell'approvazione. **Regola confermata:** le ore del nuovo docente possono provenire anche da **più docenti storici**. Il referente deve indicare esplicitamente le ore cedute **da ciascun docente di origine**. DidaUP non può scegliere automaticamente i cedenti. La rappresentazione esatta delle cessioni nell'Excel a quattro colonne editabili rimane **[DA CONFERMARE]**.

Per evitare ambiguità terminologiche, `Aggiunta` e `Sostituzione parziale` possono avere lo stesso effetto aritmetico (redistribuzione) ma rappresentare intenzioni amministrative differenti, da conservare nel campo `Tipo variazione` **[DA PRECISARE]**. Nessuna modifica al database degli affidamenti né approvazione automatica discende da questa definizione.


### Aggiunta da più docenti storici — CONFERMATO (regola quantitativa)

La proposta di aggiunta di un docente può raccogliere ore da più righe di copertura storica, nel medesimo modulo/attività identificati dalla fonte. Le ore cedute devono essere attribuite singolarmente a ciascuna riga di origine; sono vietate deduzioni automatiche basate soltanto sul totale del modulo.

**Esempio puramente fittizio:** storico docente A = 20 ore, docente B = 10 ore. Si propone di assegnare al nuovo docente C 12 ore, cedute 8 da A e 4 da B. Esito proposto: A = 12, B = 6, C = 12, totale = 30 ore, identico allo storico. I dati sorgente A = 20 e B = 10 restano intatti e tracciabili.

**Controlli funzionali previsti:** per ciascun cedente, ore cedute ≤ `TOT ORE EFFETTIVE` disponibili; la somma dei trasferimenti verso la stessa nuova copertura deve essere calcolata una sola volta, senza creare duplicati; la somma delle ore proposte deve restare uguale alla somma storica; bloccare o segnalare proposte ambigue, negative o prive di identificazione univoca dell'attività e dei cedenti. Nessuna approvazione automatica.

**Rappresentazione nell'Excel — [DA CONFERMARE]:** possibile compilare `Tipo variazione = Aggiunta`, `Nuovo docente = C`, `Ore = 8` sulla riga storica A e analogamente `Ore = 4` su quella B. DidaUP aggrega il nuovo docente C in un'unica copertura proposta da 12 ore, mantenendo la tracciabilità delle due cessioni. Questa scelta di interfaccia non è stata ancora confermata dall'utente.


## Distribuzione delle proposte 2027/28: CINQUE FILE IDENTICI E COMPLETI — CONFERMATO

**Decisione esplicita dell'utilizzatore (rettifica della versione precedente):** DidaUP deve generare **cinque copie inizialmente identiche dello stesso Excel completo**, una da condividere online con i referenti di ciascuno dei cinque dipartimenti. **Non effettuare alcun filtro, partizionamento o attribuzione delle attività didattiche ai dipartimenti durante la generazione.** Ogni file contiene **tutte le attività didattiche, per tutti i CdS e tutti gli SSD**, indipendentemente dal dipartimento, con le stesse righe e nello stesso ordine. Le copie diventano differenti soltanto per le proposte compilate dai rispettivi referenti.

Questa regola **sostituisce** la precedente ipotesi di un file per SSD e la successiva ipotesi, non confermata, di filtrare le attività per dipartimento di competenza. **Non serve una tabella di attribuzione degli insegnamenti ai dipartimenti per creare i cinque file.** La colonna `DIPARTIMENTO AFFERENZA DOCENTE` rimane informativa e **non** deve essere usata come criterio di suddivisione dei record.

### Struttura e compilazione

- **Un unico modello/master** e **cinque file con lo stesso identico contenuto iniziale**: tutto lo storico 2026/27; proposte 2027/28 distinte dallo storico.
- Mantenere le **36 colonne del tracciato referenti esistente** e aggiungere **Tipo variazione** accanto alle tre proposte editabili esistenti: **Nuovo docente, Ore, Note**. Soltanto queste quattro colonne sono modificabili.
- **`TOT ORE EFFETTIVE`** rimane l'unica base per i calcoli storici; valgono le regole confermate per le redistribuzioni tra uno o più cedenti, senza aumento delle ore complessive.
- Referenti del medesimo dipartimento lavorano contemporaneamente **nel proprio file condiviso su OneDrive d'Ateneo**, applicando i filtri personali (preferibilmente *Visualizzazioni foglio*) per trovare CdS/SSD di interesse.
- Proteggere dati storici e identificativi delle righe; mantenere un pulsante **«+ Aggiungi variazione»** per le proposte multiple, **solo dopo effettivo collaudo** dell'associazione Office Scripts/pulsante su un master dell'ambiente d'Ateneo. Un testo con il simbolo + non costituisce un pulsante funzionante.
- DidaUP dovrà creare e pubblicare le cinque copie e acquisire le proposte; **generazione integrata, pubblicazione e reimport OneDrive non sono ancora implementati**.

### Controlli nella raccolta dei cinque file

- Ogni copia ripete **intenzionalmente tutte le stesse coperture storiche**: non scambiare questa duplicazione per cinque incarichi distinti. Gli ID origine devono essere coerenti e derivati dalla medesima fonte ufficiale.
- Acquisire le **sole variazioni effettivamente compilate**, registrando il file dipartimentale di provenienza; **non** considerare le righe rimaste senza proposte come cinque conferme individuali. La semantica della chiusura senza modifiche per ciascun dipartimento/referente rimane **[DA DEFINIRE]**.
- Se la **stessa copertura storica** è stata modificata in più file, DidaUP deve **segnalare la sovrapposizione**, confrontare le proposte ed esigere una gestione esplicita prima di applicarle. Non sommare automaticamente proposte ripetute, non scegliere arbitrariamente il file prevalente, non sostituire in silenzio una proposta con un'altra.
- Distinguere chiaramente i **cinque file dipartimentali** (nomi/identificativi dei dipartimenti **[DA ACQUISIRE]**); mantenere cronologia, revisione, data di acquisizione e stato di raccolta per ciascuno.
- Condivisione di modifica del file: il diritto di editare la cartella di lavoro **non limita automaticamente** un referente alle sole righe di un SSD. L'identità del compilatore di una singola cella non è dimostrata dal solo XLSX: se richiesto, introdurre controllo di autorizzazione/attribuzione e approvazione in DidaUP.
- Reimport: ricostruire ogni proposta confrontando gli identificativi e i valori storici con lo snapshot originale nel database privato DidaUP; rilevare duplicazioni, trasferimenti eccedenti le ore disponibili, assenza di dati obbligatori, proposte sovrapposte e altre incoerenze.
- I cinque file sono **proposte di lavoro**, non atti di affidamento né approvazioni formali. Nessuna assegnazione reale o condivisione OneDrive è stata effettuata con questa modifica alle specifiche.

**Da chiarire più avanti:** criterio amministrativo di risoluzione delle proposte sovrapposte su file dipartimentali diversi, attribuzione/autorizzazione dei referenti e chiusura dei file senza proposte. Non introdurre automaticamente una suddivisione per dipartimento come soluzione a tali problemi.


## Convenzione anno accademico Scuole di specializzazione — CONFERMATO

Per le **Scuole di specializzazione** l'A.A. presente nell'estrazione è **per convenzione l'anno accademico precedente** rispetto all'A.A. corrente di riferimento. Esempio illustrativo della regola: rispetto al **2026/27**, per una Scuola di specializzazione è conforme un valore **2025/26** nel report. Tale scostamento **non è una difformità né un'anomalia da bloccare**.

La deroga vale **esclusivamente** per righe riconoscibili come Scuole di specializzazione mediante una denominazione/tipologia esplicita nella fonte. Per gli altri corsi, o quando la natura della riga non è riconoscibile con sufficiente certezza, resta attivo il controllo normale sull'A.A.; non ipotizzare classificazioni sulla base di codici non verificati. Non riscrivere il valore storico originale nel foglio Excel generato.

La regola è applicata sia all'estrazione delle annualità sia alla generazione dei cinque file dipartimentali completi e identici. La presenza e l'associazione corretta del campo che permette di riconoscere la scuola nell'estrazione concreta restano **[DA VERIFICARE]**. Nessuna disposizione normativa è stata presunta: è una convenzione operativa comunicata espressamente dall'utente.

## Persistenza della mappatura — CORREZIONE TECNICA

La mappatura salvata è associata all'ID del report e persistita nel database privato. **Rileggere l'anteprima, tornare alla schermata precedente o cambiare vista non deve resettare scelte già salvate**. Le correzioni non ancora salvate sono mantenute quando si torna allo stesso report durante la sessione corrente; al salvataggio viene eseguita una nuova lettura dal database per verificarne la persistenza. Le modifiche non salvate non sono equivalenti a una mappatura persistente: prima di uscire dall'app occorre esplicitamente salvarle.


## Rettifica successiva: A.A. del report prevalente sui singoli valori di riga — CONFERMATO

L'utente ha chiarito che, **per direttiva**, tutte le attività presenti nel report ufficiale identificato come offerta **2026/27** sono da gestire come attività dell'A.A. **2026/27**, anche se nella singola riga compare un A.A. diverso (incluso il caso convenzionale delle Scuole di specializzazione). **Non è quindi necessario né corretto bloccare singole righe in base alla corrispondenza dell'A.A.**

DidaUP deve usare come riferimento l'**anno accademico dell'archivio/report selezionato all'importazione**; il campo A.A. originale di ciascuna riga resta visibile e **immutato** quale dato storico. Il controllo sull'archivio di appartenenza del report resta attivo: il report scelto per la generazione deve appartenere all'A.A. selezionato e al corretto tipo di fonte. Non introdurre interpretazioni per tipologia di corso e non applicare il precedente blocco differenziato sulle Scuole di specializzazione. Questa regola **sostituisce la precedente verifica dell'A.A. per singola riga**, mantenendo integra la fonte.


## Generazione non bloccante per annualità incomplete — CONFERMATO

Una riga del report con codice CdS, sede oppure anno di corso assente/non interpretabile **non deve fermare la generazione delle cinque copie**. Quando esistono annualità esplicitamente escluse, DidaUP applica l'esclusione **solo in caso di corrispondenza certa** di codice CdS + sede + anno; tutte le altre righe sono **mantenute** nel file, senza attribuzioni presunte. Il riepilogo comunica il **numero di righe mantenute con identificativo di annualità incompleto** e riporta esempi dei numeri di riga del report, così l'operatore può esaminarle in seguito. Il report sorgente non viene modificato.

La regola riguarda le anomalie amministrative classificatorie delle annualità. Rimangono distinti gli errori di integrità tecnica della fonte (es. hash diverso, tracciato/associazioni incompatibili), da non occultare perché impedirebbero di ricostruire correttamente i dati.


## Generazione non bloccante in assenza dei codici di insegnamento — CONFERMATO

Se una riga del report non contiene né **CODICE INS** né **CODICE UGOV**, DidaUP **non blocca la generazione dei cinque Excel** e non scarta la riga. La mantiene e le attribuisce esclusivamente un **identificativo tecnico derivato dall'ID univoco della riga dello snapshot storico** (stabile fra le cinque copie e al reimport, ma non equivalente a un codice ufficiale di insegnamento). Non inventa né completa i codici mancanti.

Il riepilogo dell'esportazione mostra quante righe sono state mantenute senza codici e alcuni numeri di riga sorgente, da verificare in sede istruttoria. **Non aggregare automaticamente** tra loro più righe senza codici, nemmeno se denominazione, SSD o docente sono simili. La loro eventuale appartenenza allo stesso modulo/attività è **[DA VERIFICARE]** prima di una riconciliazione amministrativa. La validazione di identificativi e dati storici al reimport resta obbligatoria. Questa scelta riguarda la generazione, non autorizza la ricostruzione automatica di coperture dubbie.


## Correzione esclusioni effettive nell'export — confermata dall'utente

Le annualità che sono già registrate come **Escluse** nell'archivio dell'A.A. non devono comparire nei cinque Excel generati. La selezione è fatta confrontando **codice CdS, sede e anno di corso**, con normalizzazione non semantica di maiuscole e spazi. Non basta che l'interfaccia delle annualità mostri «Esclusa»: l'export deve verificare che le relative righe siano state realmente filtrate, e riportare il numero di **righe escluse**.

Per una riga che non riporta l'anno di corso, DidaUP può escluderla tramite codice CdS e sede **soltanto se tutte le annualità registrate per quello stesso CdS e sede sono escluse**; se almeno una annualità è inclusa, la riga va mantenuta con avviso. Questo evita di recuperare indiscriminatamente corsi esclusi senza rischiare di cancellare annualità ancora in gestione. Le esclusioni presenti nell'archivio ma che non trovano alcuna corrispondenza certa nel report sono elencate nel riepilogo per controllo amministrativo.

La fonte importata e le esclusioni registrate non vengono modificate. Le copie Excel già esportate non si aggiornano da sole e devono essere rigenerate dopo la correzione del generatore. Dati e nominativi del caso concreto non sono stati replicati nei test; le verifiche sono esclusivamente sintetiche.


## TAF nel tracciato storico — mappatura confermata

L'utente ha verificato che il campo **TAF** risultava **non associato nella mappatura**: non si trattava di un valore TAF da inventare, ma dell'assenza di una corrispondenza con la colonna del report. La soluzione operativa è selezionare la colonna **TAF** nella mappatura e salvare, quindi rigenerare i cinque Excel. Il report storico non viene modificato.

Per proteggere anche i precedenti mapping incompleti, il generatore può recuperare il TAF dalla fonte **soltanto se trova un'unica intestazione esatta \"TAF\"**; segnala se la colonna manca, è ambigua, oppure quanti valori di riga sono effettivamente disponibili. Non attribuisce classificazioni TAF per analogia o interpretazione. Questa funzionalità non sostituisce la verifica esplicita della mappatura da parte dell'operatore.


## Maschera delle esclusioni: filtri combinabili e multiselezione — revisione UI

Per la selezione delle annualità da escludere viene introdotto un pannello dedicato con **ricerca libera** e filtri multiselezione indipendenti per **CdS (nome e codice), sede e anno di corso**. Il filtro di stato distingue tutte le annualità, quelle spuntate per esclusione, quelle non spuntate e le **sole modifiche non ancora salvate**.

Le azioni massive di esclusione/ripristino incidono **soltanto sulle annualità effettivamente visualizzate in base ai filtri in uso**, richiedono conferma e non modificano il database fino alla pressione del pulsante di salvataggio. Le righe nascoste conservano la loro spunta e i filtri non hanno valore amministrativo. La maschera mostra in modo distinto: totale visibile, spunte in bozza, **esclusioni già registrate** e differenze (nuove esclusioni/ripristini). È possibile annullare la bozza e azzerare i filtri separatamente.

Il **registro delle annualità già salvate** mantiene il suo stato effettivo, separato dalla selezione guidata, e può essere filtrato per testo e inclusione/esclusione. I controlli server di concorrenza, integrità della fonte, tracciabilità e motivazione restano attivi. Nessun elenco realmente amministrativo viene pubblicato come fixture di test.

Per distinguere un Excel storico da una nuova generazione, i cinque XLSX nel pacchetto hanno un **identificativo di revisione nel nome file**. Le cinque copie restano identiche nel contenuto. La data/ID di revisione non altera lo storico né determina uno stato di approvazione.


## Filtro multiselezione TITOLO AFFIDAMENTO — confermato

Nella selezione guidata **Annualità CdS** è disponibile anche il filtro **Titolo affidamento**: il menu ricava i valori esclusivamente dalla colonna del report esplicitamente mappata come `titolo_affidamento`, con ricerca testuale e scelta contemporanea di più valori. Può essere combinato con i filtri già presenti per tipologia CdS, codice/denominazione CdS, sede e anno di corso.

Lo stesso CdS/sede/anno può comprendere attività con più titoli affidamento: la maschera visualizza **tutti i valori rilevati nello storico**. Il filtro seleziona le annualità che hanno **almeno un'attività** corrispondente al titolo, ma **non crea esclusioni di singoli insegnamenti o incarichi**. Anche con questo filtro, il salvataggio riguarda l'intera annualità; in presenza di titoli misti l'interfaccia avvisa l'operatore prima di applicare le spunte in blocco.

Il campo deve essere presente nella mappatura del report. Se manca, il sistema avvisa senza attribuire alcun titolo presunto. I filtri non cambiano il database, le esclusioni precedenti restano intatte e sono necessari il salvataggio esplicito e il controllo delle anteprime prima di generare gli Excel.
