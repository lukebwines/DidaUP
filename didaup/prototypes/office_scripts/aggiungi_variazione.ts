/**
 * DidaUP — prototipo Office Scripts, SOLO DATI SINTETICI.
 * Selezionare una cella su una riga storica o di variazione,
 * quindi eseguire lo script "Aggiungi variazione" o il relativo pulsante.
 *
 * Il foglio e' protetto SENZA password per impedire modifiche accidentali.
 * Non e' una misura di sicurezza: le identita' dei dati vanno controllate
 * dal backend DidaUP, confrontando con la fonte storica originale.
 *
 * Il prototipo non effettua alcuna chiamata di rete.
 */
function main(workbook: ExcelScript.Workbook) {
  const SHEET = "Proposte SSD";
  const FIRST_DATA_ROW_INDEX = 6; // Riga 7 di Excel.
  const WIDTH = 13;               // Colonne A:M.
  const sheet = workbook.getWorksheet(SHEET);
  if (!sheet) {
    throw new Error("Foglio 'Proposte SSD' non trovato.");
  }
  const selection = workbook.getSelectedRange();
  if (selection.getWorksheet().getName() !== SHEET) {
    throw new Error("Selezionare una cella nella riga da duplicare su 'Proposte SSD'.");
  }
  const rowIndex = selection.getRowIndex();
  if (rowIndex < FIRST_DATA_ROW_INDEX) {
    throw new Error("Selezionare una riga di copertura, non l'intestazione.");
  }

  const protection = sheet.getProtection();
  const wasProtected = protection.getProtected();
  if (wasProtected && protection.getIsPasswordProtected()) {
    throw new Error(
      "Il prototipo non puo' modificare un foglio protetto da password. " +
      "Non inserire password nello script condiviso."
    );
  }
  const previousOptions = protection.getSavedOptions();
  if (wasProtected) protection.unprotect();

  try {
    const used = sheet.getUsedRange(true);
    if (!used) throw new Error("Nessun dato presente nel foglio.");
    const lastRowIndex = used.getRowIndex() + used.getRowCount() - 1;
    if (rowIndex > lastRowIndex) {
      throw new Error("La riga selezionata non contiene una copertura.");
    }
    const selected = sheet.getRangeByIndexes(rowIndex, 0, 1, WIDTH).getValues()[0];
    const rowType = String(selected[10] ?? "").trim();
    if (rowType !== "STORICO" && rowType !== "VARIAZIONE") {
      throw new Error("La riga selezionata non e' una copertura o variazione valida.");
    }
    const historyId = String(selected[11] ?? "").trim();
    if (!historyId) throw new Error("Riferimento alla riga storica assente.");

    // Recupera SEMPRE il record storico: una duplicazione di una variazione
    // non deve propagare le sue proposte o cambiare l'identita' della fonte.
    let historicalRowIndex = -1;
    let maxSequence = 0;
    for (let i = FIRST_DATA_ROW_INDEX; i <= lastRowIndex; i++) {
      const row = sheet.getRangeByIndexes(i, 0, 1, WIDTH).getValues()[0];
      const itemType = String(row[10] ?? "").trim();
      const id = String(row[1] ?? "").trim();
      const parent = String(row[11] ?? "").trim();
      const proposedId = String(row[12] ?? "").trim();
      if (itemType === "STORICO" && id === historyId && parent === historyId) {
        if (historicalRowIndex !== -1) {
          throw new Error("Identificativo storico duplicato: interrompere e verificare.");
        }
        historicalRowIndex = i;
      }
      const match = /^DIDAUP-VAR-(\d+)$/.exec(proposedId);
      if (match) {
        maxSequence = Math.max(maxSequence, Number(match[1]));
      }
    }
    if (historicalRowIndex < 0) {
      throw new Error("Riga storica associata non trovata: impossibile duplicare.");
    }
    if (maxSequence >= 999999) {
      throw new Error("Limite identificativi di prova raggiunto.");
    }

    const historical = sheet.getRangeByIndexes(
      historicalRowIndex, 0, 1, 6
    ).getValues()[0];
    if (String(historical[0] ?? "").trim() !== String(selected[0] ?? "").trim()) {
      throw new Error("La variazione selezionata non appartiene all'attivita' storica.");
    }

    // La riga nuova viene inserita sotto quella selezionata. In Excel il
    // formato viene copiato, ma le colonne di proposta saranno svuotate.
    const insertIndex = rowIndex + 1;
    sheet.getRangeByIndexes(insertIndex, 0, 1, WIDTH)
      .insert(ExcelScript.InsertShiftDirection.down);
    const originalSelected = sheet.getRangeByIndexes(rowIndex, 0, 1, WIDTH);
    const newRow = sheet.getRangeByIndexes(insertIndex, 0, 1, WIDTH);
    newRow.copyFrom(originalSelected, ExcelScript.RangeCopyType.all);

    sheet.getRangeByIndexes(insertIndex, 0, 1, 6).setValues([historical]);
    sheet.getRangeByIndexes(insertIndex, 6, 1, 4).setValues([["", "", "", ""]]);
    sheet.getRangeByIndexes(insertIndex, 10, 1, 3).setValues([[
      "VARIAZIONE",
      historyId,
      "DIDAUP-VAR-" + String(maxSequence + 1).padStart(6, "0")
    ]]);

    // Colonne storiche e metadati bloccati. Solo G:J modificabili.
    newRow.getFormat().getProtection().setLocked(true);
    sheet.getRangeByIndexes(insertIndex, 6, 1, 4)
      .getFormat().getProtection().setLocked(false);
    newRow.getFormat().getFill().setColor("#EAF3FD");
    sheet.getRangeByIndexes(insertIndex, 6, 1, 4)
      .getFormat().getFill().setColor("#FFF0BF");

    sheet.getRangeByIndexes(insertIndex, 7, 1, 1).select();
    console.log(
      "Variazione creata e collegata alla riga storica " +
      historyId + ". Compilare soltanto le colonne G:J."
    );
  } finally {
    // Ripristina la protezione anche quando si verifica un errore.
    if (!protection.getProtected()) {
      const options = wasProtected ? previousOptions : {
        allowAutoFilter: true,
        allowInsertRows: false,
        allowDeleteRows: false,
        allowSort: false,
        selectionMode: ExcelScript.ProtectionSelectionMode.normal
      };
      protection.protect(options);
    }
  }
}
