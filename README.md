# DidaUP

**Add-on per la predisposizione di file Excel evoluti destinati ai referenti SSD.**

> Stato: impostazione iniziale del progetto. Nessuna procedura 2027/28 o codifica SSD è considerata approvata o verificata.

## Obiettivo
Partire dall'offerta e dalle coperture storiche **2026/27** per costruire un archivio di riferimento verificabile. Quando saranno disponibili le estrazioni ufficiali, predisporre i fogli di programmazione **2027/28** senza trasporre automaticamente come valide assegnazioni, codici o nominativi precedenti.

## Utilizzatori
- Segreteria: importazione, produzione dei file Excel per SSD, reimport, controlli e riepiloghi.
- Referenti SSD: **solo file .xlsx**, senza accesso all'add-on.

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

Vedere [Policy privacy](docs/PRIVACY.md) e [Architettura](docs/ARCHITETTURA.md).

## Prossimi input
Il report procedurale 2026/27 servirà a validare il tracciato di importazione, i ruoli, i controlli e il layout Excel. Eventuali dati assenti: **[DA VERIFICARE]**.
