# DidaUP — Architettura funzionale preliminare

## Ambito iniziale
Referenti SSD dell'area medica della Facoltà di Medicina e Chirurgia, secondo il materiale già condiviso; riconferma delle designazioni nel 2027/28 **[DA VERIFICARE]**.

## Regolamento
Il regolamento sull'attribuzione dei compiti didattici è fonte da usare per evidenziare nell'XLSX le regole pertinenti e i casi che richiedono verifica. La mappatura regola -> riferimento ufficiale -> avviso nel file -> controllo al reimport sarà svolta in fase di sviluppo, non dedotta dai fac-simile.

## Flusso anno accademico
1. Importare le estrazioni ufficiali 2026/27 in archivio privato.
2. Verificare struttura, codici, identificativi, coperture multiple, SSD e differenze.
3. Costruire uno **snapshot storico immutabile** dell'anno base.
4. Quando disponibili i dati ufficiali 2027/28, riconciliare attività e codifiche con lo storico 2026/27; non considerare valida una copertura per sola eredità.
5. Generare **cinque file XLSX identici e completi** dallo stesso snapshot, **senza filtri o suddivisioni di attività per dipartimento**. Conservare attribuzioni e coperture storiche in sola lettura e distinguere le quattro colonne di proposta.
6. Condividere, quando sarà disponibile l'integrazione autorizzata, una copia per dipartimento su OneDrive d'Ateneo; i referenti filtrano personalmente CdS e SSD nel proprio file. **La pubblicazione automatica non è ancora implementata.**
7. Acquisire i cinque XLSX compilati, riconciliare le proposte confrontando gli identificativi con la fonte storica privata e **segnalare ogni sovrapposizione sullo stesso insegnamento presente in più file, senza fondere automaticamente le modifiche**.
8. Esportare prospetti di istruttoria. Ogni approvazione potrà essere registrata solo sulla base di un atto ufficiale; l'anteprima attuale non approva nulla.

## Modello logico (da convalidare sul report)
- `AnnoAccademico`: periodo e provenienza.
- `AttivitaDidattica`: corso, sede, anno, insegnamento, modulo, identificativi ufficiali, SSD insegnamento.
- `CoperturaStorica`: assegnazione e ore riferite all'attività, docente, SSD docente, riferimento allo snapshot.
- `PropostaCopertura`: nuovo esito, nuovo docente, ore, motivazione, versione e provenienza del file.
- `SSD`: codice precedente, codice nuovo, fonte e data della corrispondenza, eventuali ambiguità.
- `ReferenteSSD`: competenza su SSD / dipartimento / facoltà, stato di validazione.
- `Importazione` e `Anomalia`: hash, nome logico, origine, esito del controllo.

Un insegnamento può avere più coperture. Lo stesso docente può avere carichi su SSD differenti. L'SSD dell'attività è utile per filtrare le attività durante la compilazione, **non per dividere preventivamente i cinque file per dipartimento**. L'SSD del docente va mantenuto separato e controllato, non usato per duplicare le proposte.

## Requisiti XLSX
- Dati informativi e storici non modificabili.
- Colonne nuove proposte modificabili e distinte dalle note.
- Identificativi tecnici stabili non modificabili, validati server-side.
- Menu a tendina solo dove appropriati; campi obbligatori e controlli coerenti.
- Protezione delle formule, dei riferimenti e dei fogli di supporto.
- Gestione file rettificati e reimportazioni ripetute con idempotenza/versioni.

## Non assumere
- Che i codici SSD vecchi/nuovi siano sempre in corrispondenza biunivoca.
- Che il settore dell'insegnamento coincida con quello del docente.
- Che una riga Excel equivalga a un singolo insegnamento o incarico.
- Che il file esportato precedente contenga già i dati definitivi del nuovo anno.
- Che la struttura del file 2026/27 sia invariata nel 2027/28.

Campi, stati, responsabilità e regole di computo da verificare tramite il report e le fonti ufficiali: **[DA VERIFICARE]**.
