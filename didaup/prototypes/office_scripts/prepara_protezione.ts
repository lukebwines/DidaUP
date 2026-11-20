/**
 * DidaUP · solo ripristino straordinario della protezione su file di prova.
 *
 * Il prototipo corretto viene gia' consegnato protetto.
 * Il normale flusso richiede SOLTANTO "aggiungi_variazione.ts".
 */
function main(workbook: ExcelScript.Workbook) {
  const sheet = workbook.getWorksheet("Proposte SSD");
  if (!sheet) throw new Error("Foglio Proposte SSD assente.");
  const head = sheet.getRange("AC6:AG6").getTexts()[0];
  const expected = ["TOT ORE EFFETTIVE", "Tipo variazione", "Nuovo docente", "Ore", "Note"];
  for (let i = 0; i < expected.length; i++) {
    if (head[i] !== expected[i]) {
      throw new Error("Formato non coerente: " + expected[i] + " mancante.");
    }
  }
  const p = sheet.getProtection();
  if (p.getProtected()) {
    console.log("Protezione gia' presente. Nessuna modifica.");
    return;
  }
  sheet.getRange("A1:AO500").getFormat().getProtection().setLocked(true);
  sheet.getRange("AD7:AG500").getFormat().getProtection().setLocked(false);
  sheet.getRange("AL:AO").setColumnHidden(true);
  p.protect({
    allowAutoFilter: true,
    allowInsertRows: false,
    allowDeleteRows: false,
    allowSort: false,
    selectionMode: ExcelScript.ProtectionSelectionMode.normal
  });
  console.log("Protezione ripristinata: solo AD:AG editabili.");
}
