# DidaUP – prototipo corretto Excel SSD (2026/27 → 2027/28)

**Avvertenza:** il primo file dimostrativo con 13 colonne non corrispondeva al tracciato concordato. **Usare solo il nuovo file "DidaUP_Prototipo_SSD_CORRETTO.xlsx"** fornito nella conversazione. Nessun dato dell'Ateneo è incluso nel prototipo.

## Cosa contiene il file corretto

- Un solo foglio **Proposte SSD**.
- Tutte le **36 intestazioni** del foglio precedentemente utilizzato dai referenti, con una nuova colonna **Tipo variazione** davanti a **Nuovo docente, Ore, Note**: **37 colonne visibili** complessive.
- Le **quattro colonne editabili sono AD:AG**: Tipo variazione, Nuovo docente, Ore, Note. Sono colorate in giallo.
- Le altre **33 colonne informative** contengono informazioni storiche e risultano **bloccate già all'apertura** nel file consegnato.
- Quattro colonne tecniche **AL:AO** restano **nascoste e bloccate**: tipo di riga, ID origine, ID proposta, ID attività. Gli identificativi nel collaudo sono fittizi.
- Storico **2026/27** e proposta **2027/28** sono esplicitamente separati.
- **TOT ORE EFFETTIVE** è l'unico valore storico usato per il conteggio delle ore; gli altri campi sulle ore sono solo informativi.
- La protezione è **senza password**, per consentire a Office Scripts di inserire una riga e ripristinare la protezione. Non è una misura contro manipolazioni intenzionali: il reimport in DidaUP dovrà confrontare tutto con la fonte privata.
- Il testo con il simbolo **＋** nella parte alta del foglio è **solo un'indicazione**. **Non è ancora un pulsante funzionante.** Il pulsante reale potrà essere creato soltanto da Excel online, associando al file l'Office Script (vedi sotto).

## Procedura di prova (un solo script necessario)

1. Aprire il file **DidaUP_Prototipo_SSD_CORRETTO.xlsx** in **Excel online** sul OneDrive universitario. Non usare il vecchio prototipo con 13 colonne.
2. Prima di collegare lo script, verificare che **J7 sia bloccata** e **AD7 sia modificabile**: la protezione deve essere già presente nel file.
3. In **Automatizza → Nuovo script**, incollare [aggiungi_variazione.ts](office_scripts/aggiungi_variazione.ts), salvarlo come **DidaUP – Aggiungi variazione**.
4. Selezionare una cella della riga del docente A (ad esempio **J7**), quindi eseguire lo script. Deve comparire una nuova riga immediatamente sotto, con le quattro celle **AD:AG vuote e modificabili**; il contesto storico e l'ID origine non devono cambiare.
5. Se l'esecuzione riesce, nella sezione di condivisione dello script selezionare **Associa alla cartella di lavoro** e quindi **Aggiungi pulsante al foglio**. Posizionare il pulsante dove preferito (ad esempio vicino al testo con il simbolo ＋).
6. Ripetere la prova cliccando il pulsante. Se non funziona su un foglio protetto, verificare la stessa operazione da **Automatizza → Esegui**: il funzionamento dei pulsanti sui fogli protetti è un aspetto **[DA VERIFICARE]** sul tenant dell'Ateneo.
7. Non distribuire ancora il file a referenti reali: servono i controlli sul totale ore, sulle identità docenti, sulle righe duplicate, la validazione del reimport e la verifica dei permessi OneDrive.

Lo script [prepara_protezione.ts](office_scripts/prepara_protezione.ts) è ora una **funzione di ripristino**: non occorre eseguirlo sul nuovo file, che è già protetto.

## Esempio fittizio

Due righe storiche dello stesso modulo: **Docente A = 20 ore**, **Docente B = 10 ore**. I due docenti cedono **8 + 4 ore** al nuovo Docente C, che riceve una sola proposta di **12 ore**. Il totale del modulo rimane **30 ore**. Selezionando la riga del Docente A, il comando «＋» può creare una nuova proposta relativa a quella stessa riga senza copiarne i campi compilabili. Non significa che DidaUP abbia già implementato il ricalcolo: questa è una prova tecnica dell'inserimento righe.

## Limiti da verificare nel tenant

Office Scripts, associazione degli script al file e pulsanti dipendono dai permessi Microsoft 365 e dalle impostazioni del tenant. Microsoft documenta [come associare un pulsante a uno script](https://learn.microsoft.com/en-us/office/dev/scripts/develop/script-buttons) e le [API di protezione](https://learn.microsoft.com/en-us/javascript/api/office-scripts/excelscript/excelscript.worksheetprotection?view=office-scripts). La creazione del pulsante non può essere completata con la sola generazione offline del file XLSX.

L'Excel contenente proposte compilate non deve diventare fonte dei dati ufficiali. La Segreteria dovrà convalidare ogni riga confrontandola con i report ufficiali e segnalare le anomalie prima degli affidamenti.
