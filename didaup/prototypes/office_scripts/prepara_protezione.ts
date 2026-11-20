/**
 * DidaUP — INIZIALIZZAZIONE UNA TANTUM del foglio sintetico.
 *
 * Lanciare UNA volta dal pannello Automatizza prima di distribuire il file.
 * Blocca A:F e K:M, lascia editabili SOLO G:J. Imposta protezione contro
 * errori accidentali senza password: NON e' un controllo di sicurezza.
 * Non aggiungere password nel codice Office Scripts condiviso.
 *
 * La conferma dei dati resta responsabilita' dell'importazione in DidaUP:
 * mai fidarsi di ID/metadati copiati da un Excel editato dall'esterno.
 */
function main(workbook: ExcelScript.Workbook) {
  const sheet = workbook.getWorksheet("Proposte SSD");
  if (!sheet) throw new Error("Foglio 'Proposte SSD' inesistente.");
  const guard = sheet.getProtection();
  if (guard.getProtected() && guard.getIsPasswordProtected()) {
    throw new Error("Foglio gia' protetto da password; non rimuovere la protezione.");
  }
  if (guard.getProtected()) guard.unprotect();

  try {
    const used = sheet.getUsedRange(true);
    if (!used || used.getRowIndex() + used.getRowCount() < 7) {
      throw new Error("Non esistono righe storiche nel foglio.");
    }
    if (sheet.getRange("A6").getText() !== "ID ATTIVITÀ" ||
        sheet.getRange("F6").getText() !== "TOT ORE EFFETTIVE" ||
        sheet.getRange("G6").getText() !== "TIPO VARIAZIONE" ||
        sheet.getRange("M6").getText() !== "ID PROPOSTA") {
      throw new Error("Schema DidaUP non compatibile: protezione non applicata.");
    }
    // Numero di righe ampiamente superiore al collaudo sintetico.
    sheet.getRange("A1:M1000").getFormat().getProtection().setLocked(true);
    sheet.getRange("G7:J1000").getFormat().getProtection().setLocked(false);
    console.log("Storico e metadati bloccati; proposte G:J modificabili.");
  } finally {
    guard.protect({
      allowAutoFilter: true,
      allowInsertRows: false,
      allowDeleteRows: false,
      allowSort: false,
      selectionMode: ExcelScript.ProtectionSelectionMode.normal
    });
  }
}
