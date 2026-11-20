# DidaUP — Regole privacy e sicurezza

## Regola inderogabile
**Nessun dato reale dell'Ateneo nel repository GitHub**, anche se privato:
- nominativi, codici fiscali, contatti, identificativi di docenti e dipendenti;
- assegnazioni e prospetti autentici, Excel, PDF, email, delibere;
- credenziali, token, cookie, URL firmati, file .env, dump, database e backup;
- estratti anche parziali di log che possano contenere dati identificativi.

Usare esclusivamente dati *interamente sintetici* per test, screenshot, issue e documentazione. Non considerare sufficiente la pseudonimizzazione.

## Protezioni del sistema da implementare
- Dati operativi conservati in un archivio persistente **fuori dall'albero del codice Git**.
- Accessi amministrativi autorizzati, autenticazione e controllo dei ruoli.
- Importazione in area temporanea isolata; validazione dimensione, tipo e struttura, limitando macro, file esterni e formule pericolose.
- Generazione XLSX con colonne storiche protette **e controllo server-side al reimport**; la password di protezione del foglio non è una misura di sicurezza dei dati.
- Audit degli eventi amministrativi senza dati personali superflui.
- Backup cifrati, gestione delle chiavi fuori dal codice, politiche di conservazione da definire.
- Nessun invio di dati a servizi AI o cloud esterni senza base autorizzativa e verifica preventiva.
- Evitare URL pubblici per file contenenti dati reali; condivisioni ai referenti attraverso canali autorizzati.
- Prima dell'uso con dati reali: verifica dell'ambiente di esecuzione, autorizzazione dell'Ateneo e delle misure organizzative richieste.

## Barriere Git
Il file `.gitignore` esclude i formati documentali e le directory operative più comuni. **Non è un controllo completo**: `git add -f`, file rinominati, file già tracciati e testi incollati in commit/issue possono aggirarlo. È necessaria una verifica preventiva di ogni commit e, nelle fasi successive, scansione automatica dei segreti e controllo dei dati sensibili.

## Materiale sorgente
I documenti 2026/27 possono essere analizzati nell'ambiente di lavoro autorizzato; il repository conterrà solo descrizioni generali e regole tecniche, non copie o estratti identificativi.

## Importazione e azzeramento nella versione 0.1.2-alpha1
- Il file caricato è memorizzato con nome casuale e permessi riservati in `/data/sources`; originale e metadati non sono inclusi nei commit GitHub.
- Le anteprime dei fogli sono accessibili solo a utenti autenticati dell'applicazione. Non renderle pubbliche in screenshot o issue.
- Un azzeramento elimina i riferimenti nel database e prova a rimuovere i file locali associati; un eventuale errore di rimozione deve essere segnalato e verificato dall'amministratore.
- Repository privato non significa ambiente operativo autorizzato: su Home Assistant domestico usare **solo dati sintetici**.
