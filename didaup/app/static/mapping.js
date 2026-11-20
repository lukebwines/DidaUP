"use strict";

async function openMapping(importId) {
  const data = await api("imports/" + importId + "/mapping");
  state.mapping = data;
  state.preview = null;
  state.suggestion = null;
  el("mapping-save").disabled = state.user?.role === "lettura";
  setText("mapping-source-name", data.original_name);
  setText("mapping-source-kind", data.kind === "offerta"
    ? "Offerta didattica e coperture storiche" : "Elenco dei docenti di competenza");
  const picker = el("mapping-sheet");
  picker.replaceChildren();
  for (const sheet of data.sheets) {
    const opt = document.createElement("option");
    opt.value = sheet.name;
    opt.textContent = sheet.name + " · " + sheet.rows + " righe";
    picker.appendChild(opt);
  }
  picker.value = data.mapping?.sheet_name || data.sheets[0]?.name || "";
  el("mapping-header-row").value = data.mapping?.header_row || 1;
  switchView("mapping");
  if (!data.mapping) await autoMap();
  else {
    setText("mapping-auto-status", "Mappatura salvata in precedenza. Puoi rivederla o usare il riconoscimento automatico senza modificare l'originale.");
    await loadMappingPreview();
  }
}

async function loadMappingPreview() {
  if (!state.mapping) return;
  const sheetName = el("mapping-sheet").value;
  const rowNumber = Number(el("mapping-header-row").value);
  if (!Number.isInteger(rowNumber) || rowNumber < 1 || rowNumber > 40) {
    showNotice("Selezionare una riga intestazioni tra 1 e 40", true);
    return;
  }
  const previewData = await api(
    "imports/" + state.mapping.id + "/preview?sheet_name=" +
    encodeURIComponent(sheetName) + "&header_row=" + rowNumber
  );
  state.preview = previewData;
  setText("mapping-info", previewData.row_count + " righe · " +
    previewData.column_count + " colonne disponibili. " +
    "La mappatura sarà salvata solo con la tua conferma.");

  const fields = el("mapping-fields");
  fields.replaceChildren();
  const previous = state.mapping.mapping;
  const reuse = previous && previous.sheet_name === sheetName &&
    previous.header_row === rowNumber;
  const suggestion = state.suggestion;
  const suggestHere = suggestion && suggestion.sheet_name === sheetName &&
    suggestion.header_row === rowNumber;
  for (const field of state.mapping.available_fields) {
    const label = document.createElement("label");
    label.className = "mapping-field";
    const title = document.createElement("span");
    title.textContent = field.label;
    label.appendChild(title);
    const select = document.createElement("select");
    select.dataset.fieldKey = field.key;
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "— Non associata —";
    select.appendChild(none);
    for (const column of previewData.columns) {
      const option = document.createElement("option");
      option.value = String(column.index);
      option.textContent = (column.index + 1) + " · " +
        (column.label || "[senza intestazione]");
      select.appendChild(option);
    }
    if (suggestHere && Object.prototype.hasOwnProperty.call(suggestion.assigned, field.key)) {
      select.value = String(suggestion.assigned[field.key]);
    } else if (reuse && Object.prototype.hasOwnProperty.call(previous.assigned, field.key)) {
      select.value = String(previous.assigned[field.key]);
    }
    if (field.key.startsWith("proposta_")) label.classList.add("proposal-field");
    label.appendChild(select);
    fields.appendChild(label);
  }

  const head = el("mapping-preview-table").querySelector("thead");
  const body = el("mapping-preview-table").querySelector("tbody");
  head.replaceChildren();
  body.replaceChildren();
  const header = document.createElement("tr");
  // Full set of columns is available above; table shows a bounded preview.
  for (const column of previewData.columns.slice(0, 12)) {
    const cell = document.createElement("th");
    cell.textContent = (column.index + 1) + " · " + (column.label || "Senza intestazione");
    header.appendChild(cell);
  }
  head.appendChild(header);
  for (const sample of previewData.sample) {
    const row = document.createElement("tr");
    sample.slice(0, 12).forEach(value => {
      const cell = document.createElement("td");
      cell.textContent = value || "—";
      row.appendChild(cell);
    });
    body.appendChild(row);
  }
  renderMappingWarnings(reuse ? previous.warnings || [] : []);
  if (suggestHere) el("mapping-advanced").open = false;
}

async function autoMap() {
  if (!state.mapping) return;
  const trigger = el("mapping-auto");
  trigger.disabled = true;
  try {
    const result = await api("imports/" + state.mapping.id + "/autodetect");
    if (!result.recognized) {
      state.suggestion = null;
      el("mapping-advanced").open = true;
      setText("mapping-auto-status", result.message || "Tracciato non riconosciuto: usa la mappatura manuale.");
      await loadMappingPreview();
      return;
    }
    state.suggestion = result;
    el("mapping-sheet").value = result.sheet_name;
    el("mapping-header-row").value = result.header_row;
    await loadMappingPreview();
    const missing = result.missing_proposal_fields || [];
    const complete = missing.length === 0;
    const warnings = Object.keys(result.ambiguous || {}).length;
    setText("mapping-auto-status", "Riconosciute " + result.matched +
      " colonne dalla struttura dichiarata; " +
      (complete ? "tutti i 3 campi di variazione individuati." :
        "campi di variazione mancanti: " + missing.length + ".") +
      (warnings ? " Colonne ambigue: " + warnings + "." : "") +
      " Controlla l'anteprima e salva come bozza.");
    if (warnings || !complete) el("mapping-advanced").open = true;
  } finally {
    trigger.disabled = false;
  }
}

function renderMappingWarnings(warnings) {
  const node = el("mapping-warnings");
  node.hidden = !warnings.length;
  node.replaceChildren();
  if (!warnings.length) return;
  const heading = document.createElement("strong");
  heading.textContent = "Informazioni da verificare prima di elaborare gli incarichi:";
  node.appendChild(heading);
  const list = document.createElement("ul");
  for (const warning of warnings) {
    const item = document.createElement("li");
    item.textContent = warning;
    list.appendChild(item);
  }
  node.appendChild(list);
}

async function saveMapping() {
  if (!state.mapping || !state.preview) return;
  if (state.preview.sheet !== el("mapping-sheet").value ||
      state.preview.header_row !== Number(el("mapping-header-row").value)) {
    showNotice("Il foglio o la riga intestazioni è cambiato: premi prima Leggi colonne.", true);
    return;
  }
  const assigned = {};
  for (const field of el("mapping-fields").querySelectorAll("select[data-field-key]")) {
    if (field.value !== "") assigned[field.dataset.fieldKey] = Number(field.value);
  }
  const result = await api("imports/" + state.mapping.id + "/mapping", "PUT", {
    sheet_name: el("mapping-sheet").value,
    header_row: Number(el("mapping-header-row").value),
    assigned,
    expected_version: state.mapping.mapping?.version || 0,
  });
  state.mapping.mapping = {
    sheet_name: el("mapping-sheet").value,
    header_row: Number(el("mapping-header-row").value),
    assigned,
    version: result.version,
    warnings: result.warnings,
  };
  renderMappingWarnings(result.warnings);
  showNotice("Mappatura salvata come bozza. Le corrispondenze devono essere verificate prima dell'elaborazione.");
}

document.addEventListener("DOMContentLoaded", () => {
  const markOutdated = () => {
    state.preview = null;
    state.suggestion = null;
    setText("mapping-info", "La scelta delle colonne è cambiata: premi Leggi colonne prima di salvare.");
  };
  el("mapping-sheet").addEventListener("change", markOutdated);
  el("mapping-header-row").addEventListener("change", markOutdated);
  el("back-to-imports").addEventListener("click", () => switchView("imports"));
  el("mapping-auto").addEventListener("click", () =>
    autoMap().catch(error => showNotice(error.message, true)));
  el("mapping-load").addEventListener("click", () =>
    loadMappingPreview().catch(error => showNotice(error.message, true)));
  el("mapping-save").addEventListener("click", () =>
    saveMapping().catch(error => showNotice(error.message, true)));
});
