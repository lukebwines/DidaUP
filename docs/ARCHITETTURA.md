# DidaUP — Architettura funzionale preliminare

## Flusso anno accademico
1. Importare le estrazioni ufficiali 2026/27 in archivio privato.
2. Verificare struttura, codici, identificativi, coperture multiple, SSD e differenze.
3. Costruire uno **snapshot storico immutabile** dell'anno base.
4. Quando disponibili i dati ufficiali 2027/28, riconciliare attività e codifiche con lo storico 2026/27; non considerare valida una copertura per sola eredità.
5. Generare un file Excel **per SSD dell'insegnamento**, con le assegnazioni precedenti e gli attributi informativi bloccati.
6. I referenti operano sugli XLSX; la Segreteria reimporta i file, convalidando ID, versioni e campi storici.
7. Segnalare differenze, incarichi incrociati SSD, assegnazioni multiple, coperture incomplete e conflitti.
8. Esportare riepiloghi e prospetti di istruttoria. Ogni approvazione è registrata solo sulla base di un atto ufficiale.

## Modello logico (da convalidare sul report)
- `AnnoAccademico`: periodo e provenienza.
- `AttivitaDidattica`: corso, sede, anno, insegnamento, modulo, identificativi ufficiali, SSD insegnamento.
- `CoperturaStorica`: assegnazione e ore riferite all'attività, docente, SSD docente, riferimento allo snapshot.
- `PropostaCopertura`: nuovo esito, nuovo docente, ore, motivazione, versione e provenienza del file.
- `SSD`: codice precedente, codice nuovo, fonte e data della corrispondenza, eventuali ambiguità.
- `ReferenteSSD`: competenza su SSD / dipartimento / facoltà, stato di validazione.
- `Importazione` e `Anomalia`: hash, nome logico, origine, esito del controllo.

Un insegnamento può avere più coperture. Lo stesso docente può avere carichi su SSD differenti. L'SSD dell'attività determina il foglio competente; l'SSD del docente va mantenuto separato e controllato, non usato per duplicare le proposte.

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
