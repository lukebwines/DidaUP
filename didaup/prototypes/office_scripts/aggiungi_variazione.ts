/**
 * DidaUP · Aggiungi variazione
 * Prototipo con dati FINTI, schema referenti 2026/27 + Tipo variazione.
 *
 * Prima di eseguire: selezionare una qualsiasi cella della riga
 * storica o della variazione da estendere. Collega questo script
 * al pulsante "+" da Automatizza > Associa alla cartella di lavoro.
 *
 * L'XLSX corretto e' gia' protetto (senza password). Lo script
 * disattiva temporaneamente la protezione, inserisce una riga di
 * proposta distinta e ripristina la protezione in ogni caso.
 * La protezione del file non sostituisce la verifica DidaUP al reimport.
 *
 * Nessuna richiesta di rete; nessuna password incorporata.
 */
function main(workbook: ExcelScript.Workbook) {
  const NAME = "Proposte SSD";
  const HEADER_ROW = 5;         // Riga Excel 6 (zero-based).
  const START_ROW = 6;          // Prima riga di dati Excel 7.
  const VISIBLE_COLS = 37;      // 36 storiche + Tipo variazione.
  const FULL_COLS = 41;         // + 4 colonne tecniche nascoste.
  const EDIT_START = 29;        // AD, zero-based.
  const EDIT_COUNT = 4;         // AD:AG.
  const TYPE_COL = 37;          // AL.
  const ORIGIN_COL = 38;        // AM.
  const PROPOSAL_COL = 39;      // AN.
  const ACTIVITY_COL = 40;      // AO.
  const sheet = workbook.getWorksheet(NAME);
  if (!sheet) throw new Error("Foglio 'Proposte SSD' non trovato.");

  const headers = sheet.getRangeByIndexes(HEADER_ROW, 0, 1, FULL_COLS).getTexts()[0];
  const mustMatch: [number, string][] = [
    [0, "SEDE CORSO"],
    [28, "TOT ORE EFFETTIVE"],
    [29, "Tipo variazione"],
    [30, "Nuovo docente"],
    [31, "Ore"],
    [32, "Note"],
    [36, "TITOLO AFFIDAMENTO"],
    [37, "DIDAUP_TIPO_RIGA"],
    [38, "DIDAUP_ID_ORIGINE"],
    [39, "DIDAUP_ID_PROPOSTA"],
    [40, "DIDAUP_ID_ATTIVITA"]
  ];
  for (const [index, label] of mustMatch) {
    if (headers[index] !== label) {
      throw new Error("Schema non corrispondente, colonna " + (index + 1) +
        ": attesa '" + label + "'. Nessuna riga inserita.");
    }
  }

  const chosen = workbook.getSelectedRange();
  if (chosen.getWorksheet().getName() !== NAME) {
    throw new Error("Selezionare una cella nel foglio 'Proposte SSD'.");
  }
  const selectedIndex = chosen.getRowIndex();
  if (selectedIndex < START_ROW) {
    throw new Error("Selezionare una riga dati, non le istruzioni o le intestazioni.");
  }

  const used = sheet.getUsedRange(true);
  if (!used) throw new Error("Foglio senza dati.");
  const last = used.getRowIndex() + used.getRowCount() - 1;
  if (selectedIndex > last) throw new Error("Riga selezionata fuori dai dati.");

  const chosenRow = sheet.getRangeByIndexes(selectedIndex, 0, 1, FULL_COLS).getValues()[0];
  const chosenType = String(chosenRow[TYPE_COL] ?? "").trim();
  const originId = String(chosenRow[ORIGIN_COL] ?? "").trim();
  const activityId = String(chosenRow[ACTIVITY_COL] ?? "").trim();
  if (!["STORICO", "VARIAZIONE"].includes(chosenType) || !originId || !activityId) {
    throw new Error("Riga senza collegamento storico valido: nessuna modifica effettuata.");
  }

  let historicalRow = -1;
  let maxCounter = 0;
  for (let i = START_ROW; i <= last; i++) {
    const r = sheet.getRangeByIndexes(i, 0, 1, FULL_COLS).getValues()[0];
    const rowType = String(r[TYPE_COL] ?? "").trim();
    const rowOrigin = String(r[ORIGIN_COL] ?? "").trim();
    const rowProposal = String(r[PROPOSAL_COL] ?? "").trim();
    const rowActivity = String(r[ACTIVITY_COL] ?? "").trim();
    if (rowType === "STORICO" && rowOrigin === originId &&
        rowProposal === originId && rowActivity === activityId) {
      if (historicalRow !== -1) throw new Error("Riga storica duplicata: verifica necessaria.");
      historicalRow = i;
    }
    const match = /^DIDAUP-VAR-(\d+)$/.exec(rowProposal);
    if (match) maxCounter = Math.max(maxCounter, Number(match[1]));
  }
  if (historicalRow < 0) {
    throw new Error("Riga storica corrispondente non trovata: nessuna modifica.");
  }
  if (maxCounter >= 999999) throw new Error("Limite massimo di variazioni raggiunto.");

  const protection = sheet.getProtection();
  if (!protection.getProtected()) {
    throw new Error("Foglio non protetto: ripristinare la protezione prima di procedere.");
  }
  if (protection.getIsPasswordProtected()) {
    throw new Error("La protezione con password richiede una procedura autorizzata.");
  }
  const savedOptions = protection.getSavedOptions();

  protection.unprotect();
  try {
    const insertAt = selectedIndex + 1;
    // Inserisce una riga INTERA; non sposta solo le 41 colonne dell'area dati.
    sheet.getRangeByIndexes(insertAt, 0, 1, 1)
      .getEntireRow().insert(ExcelScript.InsertShiftDirection.down);

    const hist = sheet.getRangeByIndexes(historicalRow, 0, 1, FULL_COLS);
    const dest = sheet.getRangeByIndexes(insertAt, 0, 1, FULL_COLS);
    dest.copyFrom(hist, ExcelScript.RangeCopyType.all);
    dest.getFormat().getProtection().setLocked(true);

    // Le quattro celle compilabili partono vuote; mai copiare una proposta precedente.
    const proposal = sheet.getRangeByIndexes(insertAt, EDIT_START, 1, EDIT_COUNT);
    proposal.setValues([["", "", "", ""]]);
    proposal.getFormat().getProtection().setLocked(false);
    proposal.getFormat().getFill().setColor("#FFF0BF");
    sheet.getRangeByIndexes(insertAt, EDIT_START + 2, 1, 1)
      .setNumberFormat("0.##");

    sheet.getRangeByIndexes(insertAt, TYPE_COL, 1, 4).setValues([[
      "VARIAZIONE", originId,
      "DIDAUP-VAR-" + String(maxCounter + 1).padStart(6, "0"),
      activityId
    ]]);
    dest.getFormat().getFill().setColor("#EAF3FD");
    proposal.getFormat().getFill().setColor("#FFF0BF");
    proposal.getCell(0, 0).select();
    console.log(
      "Riga di variazione aggiunta. Origine storica: " + originId +
      ". Compilare Tipo variazione, Nuovo docente, Ore e Note."
    );
  } finally {
    // Anche un errore dopo l'inserimento non deve lasciare il foglio sprotetto.
    if (!protection.getProtected()) {
      protection.protect(savedOptions);
    }
  }
}
