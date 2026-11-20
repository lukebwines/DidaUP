# DidaUP · prova Office Scripts su Excel online (solo dati sintetici)

Questa prova **non contiene dati dell'Università di Verona** e non modifica il database DidaUP. Il file Excel va usato esclusivamente per collaudare il flusso e l'ambiente Microsoft 365 autorizzato.

## Obiettivo del test

Un solo foglio **Proposte SSD**, con una riga per ogni copertura storica e quattro campi editabili: **Tipo variazione, Nuovo docente, Ore, Note**.

- I riferimenti storici A:F provengono dalla fonte di riferimento e rimangono immutati.
- `TOT ORE EFFETTIVE` è l'unico valore usato come base per le ore storiche.
- Il comando **Aggiungi variazione** duplica il contesto storico della riga selezionata, ma crea un **identificativo diverso per la proposta**, senza copiare i contenuti dei quattro campi editabili.
- `ID ORIGINE` conserva un collegamento alla singola riga storica; `ID PROPOSTA` identifica la riga aggiunta.
- L'aggiunta di docenti non aumenta le ore complessive: occorre assegnare esplicitamente le ore cedute da ogni riga di origine.
- La stessa persona destinataria può ricevere quote da più cedenti, ma l'identità deve essere confermata sulla base dell'elenco docenti e non per sola somiglianza del nominativo.

## File disponibili

- `DidaUP_Prototipo_SSD_OneDrive.xlsx`: file dimostrativo da scaricare dalla conversazione, **non** presente nel repository.
- `office_scripts/prepara_protezione.ts`: prima esecuzione per bloccare le colonne storiche.
- `office_scripts/aggiungi_variazione.ts`: comando per aggiungere una riga di variazione dopo la riga selezionata.

## Collaudo in Microsoft 365 dell'Ateneo

1. Scaricare il file dimostrativo e caricarlo **manualmente nel OneDrive d'Ateneo**, non nel OneDrive personale.
2. Aprirlo in **Excel per il Web** e verificare che sia visibile la scheda **Automatizza**. Se non è presente, la prova con Office Scripts non è disponibile su quell'account senza intervento IT.
3. In **Automatizza → Nuovo script**, copiare il contenuto di `prepara_protezione.ts` e premere **Esegui** una sola volta. Il foglio viene protetto: le colonne G:J restano modificabili.
4. Creare un secondo script con il codice `aggiungi_variazione.ts` e chiamarlo **DidaUP — Aggiungi variazione**.
5. Selezionare una cella della riga del **Docente A** e avviare il secondo script dalla scheda **Automatizza**. Una nuova riga, collegata a `SYN-HIST-001`, deve apparire sotto la riga selezionata. **G:J devono essere vuote; A:F e K:M non devono essere editabili.**
6. Nella nuova riga inserire ad esempio Tipo variazione = **Aggiunta**, Nuovo docente = **Docente D**, Ore = **2**. Le 20 ore storiche del Docente A devono rimanere 20. La cessione complessiva del Docente A diventa 8 + 2 = 10 e le sue ore residue proposte diventano 10; il Docente B cede ancora 4 ore a C.
7. **Solo se il primo test è riuscito**, aprire i dettagli dello script, abilitare **Associa alla cartella di lavoro** e scegliere **Aggiungi pulsante al foglio**. Verificare il pulsante anche dopo la protezione e con un secondo account autorizzato, prima di decidere se distribuirlo ai referenti.
8. Se il pulsante non risponde, utilizzare la scheda **Automatizza → Esegui**: questa è la procedura alternativa per il collaudo. Non disattivare indiscriminatamente la protezione per farlo funzionare.
9. Non condividere il prototipo con referenti reali e non importare dati ufficiali finché l'intero procedimento (controlli ore, identità, autorizzazioni, reimport, versioni) non è stato validato.

## Sicurezza e limiti da non ignorare

- La protezione del foglio è **senza password** nel collaudo perché lo script condiviso deve temporaneamente sospenderla per inserire righe; **non costituisce una barriera di sicurezza**. Una password inserita nel codice sarebbe visibile a chi può leggere lo script.
- I dati storici di un Excel **non sono affidabili come fonte** durante il reimport: DidaUP dovrà confrontarli con lo snapshot originale custodito nell'archivio privato, usare gli ID interni solo per collegamenti e bloccare contenuti alterati, duplicati o ambigui.
- Nel prototipo sono implementate soltanto la struttura dimostrativa, la protezione anti-errore e l'aggiunta di righe. **Non** sono ancora implementati il controllo automatico del totale ore, la rubrica assistita dei docenti, il reimport o l'approvazione.
- Microsoft segnala restrizioni organizzative all'associazione degli script ai file, e nel 2026 si sono registrati malfunzionamenti dei pulsanti Office Scripts nei fogli protetti. La compatibilità con la specifica configurazione del tenant **[DA VERIFICARE]**.
- Le formule/ore di esempio non sono dati amministrativi e non devono entrare negli atti.

## Fonti Microsoft

- [Pulsanti per eseguire Office Scripts](https://learn.microsoft.com/en-us/office/dev/scripts/develop/script-buttons)
- [Protezione foglio con Office Scripts](https://learn.microsoft.com/en-us/javascript/api/office-scripts/excelscript/excelscript.worksheetprotection?view=office-scripts)
- [Opzioni protezione: inserimento righe](https://learn.microsoft.com/en-us/javascript/api/office-scripts/excelscript/excelscript.worksheetprotectionoptions?view=office-scripts)
- [Segnalazione Microsoft Q&A sui pulsanti e i fogli protetti](https://learn.microsoft.com/en-us/answers/questions/5987197/excel-online-functionality-of-office-script-button)
