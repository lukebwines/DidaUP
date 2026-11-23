"use strict";

const workbookExclusion = {
  data: null,
  selected: {},
  saved: {},
  preview: null,
  previewKey: "",
  yearId: null,
  importId: null,
  loading: false,
  hooked: false,
};

const workbookExclusionFacets = [
  {key: "titoli", id: "title", label: "Titolo affidamento", all: "Tutti"},
  {key: "tipologie", id: "type", label: "Tipologia CdS", all: "Tutte"},
  {key: "cds", id: "cds", label: "Corso di studio", all: "Tutti"},
  {key: "sedi", id: "campus", label: "Sede", all: "Tutte"},
  {key: "annualita", id: "year", label: "Annualità", all: "Tutte"},
  {key: "taf", id: "taf", label: "TAF", all: "Tutti"},
];

function workbookExclusionEmptyFilters() {
  return Object.fromEntries(workbookExclusionFacets.map(f => [f.key, new Set()]));
}

function workbookExclusionCloneFilters(filters) {
  return Object.fromEntries(workbookExclusionFacets.map(f => [
    f.key, [...(filters?.[f.key] || [])]
  ]));
}

function workbookExclusionFiltersKey(filters) {
  return JSON.stringify(workbookExclusionCloneFilters(filters));
}

function workbookExclusionNormalize(value) {
  return String(value ?? "").normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("it-IT").trim();
}

function workbookExclusionMarkDirty() {
  workbookExclusion.preview = null;
  workbookExclusion.previewKey = "";
  const save = el("workbook-exclusion-save");
  if (save) save.disabled = true;
  const preview = el("workbook-exclusion-preview");
  if (preview) preview.disabled = !workbookExclusion.data ||
    state.user?.role === "lettura";
  const status = el("workbook-exclusion-status");
  if (status && workbookExclusion.data) {
    status.textContent = "Modifiche non salvate. Calcola l'anteprima e salva i criteri per applicarli alla generazione.";
  }
  workbookExclusionRenderSummary();
}

function workbookExclusionRenderSummary() {
  for (const facet of workbookExclusionFacets) {
    const selected = workbookExclusion.selected[facet.key] || new Set();
    const summary = el("workbook-exclusion-" + facet.id + "-summary");
    if (summary) {
      summary.textContent = facet.label + " · " +
        (selected.size ? selected.size + " selezionati" : facet.all);
    }
  }
  const titleCount = workbookExclusion.selected.titoli?.size || 0;
  const total = workbookExclusionFacets.reduce(
    (sum, facet) => sum + (workbookExclusion.selected[facet.key]?.size || 0), 0
  );
  if (el("workbook-exclusion-selected-count")) {
    el("workbook-exclusion-selected-count").textContent =
      titleCount + " titoli principali · " + total + " valori complessivi selezionati";
  }
}

function workbookExclusionRenderFacet(facet) {
  if (!workbookExclusion.data) return;
  const container = el("workbook-exclusion-" + facet.id + "-options");
  const search = el("workbook-exclusion-" + facet.id + "-search");
  const chosen = workbookExclusion.selected[facet.key];
  const mapped = Boolean(workbookExclusion.data.mapped?.[facet.key]);
  const canWrite = state.user?.role !== "lettura";
  const query = workbookExclusionNormalize(search?.value || "");
  const options = (workbookExclusion.data.choices?.[facet.key] || []).filter(option =>
    !query || workbookExclusionNormalize(option.label).includes(query)
  );
  const fragment = document.createDocumentFragment();
  if (!mapped) {
    const note = document.createElement("span");
    note.className = "muted";
    note.textContent = "Campo non associato nella mappatura del report.";
    fragment.appendChild(note);
  } else {
    for (const option of options) {
      const label = document.createElement("label");
      label.className = "cohort-filter-choice";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = chosen.has(option.value);
      checkbox.disabled = !canWrite;
      checkbox.setAttribute("aria-label", option.label);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) chosen.add(option.value);
        else chosen.delete(option.value);
        if (facet.key === "titoli" && chosen.size === 0) {
          for (const other of workbookExclusionFacets) {
            if (other.key !== "titoli") workbookExclusion.selected[other.key].clear();
          }
        }
        workbookExclusionMarkDirty();
        workbookExclusionRenderAllFacets();
      });
      const text = document.createElement("span");
      text.textContent = option.label + " (" +
        Number(option.count || 0).toLocaleString("it-IT") + ")";
      label.append(checkbox, text);
      fragment.appendChild(label);
    }
    if (!options.length) {
      const note = document.createElement("span");
      note.className = "muted";
      note.textContent = "Nessun valore disponibile o corrispondente alla ricerca.";
      fragment.appendChild(note);
    }
  }
  container.replaceChildren(fragment);
}

function workbookExclusionRenderAllFacets() {
  for (const facet of workbookExclusionFacets) {
    workbookExclusionRenderFacet(facet);
  }
  workbookExclusionRenderSummary();
}

function workbookExclusionSelectedPayload() {
  return workbookExclusionCloneFilters(workbookExclusion.selected);
}

function workbookExclusionSnapshotPayload() {
  const data = workbookExclusion.data;
  return {
    import_id: Number(workbookExclusion.importId),
    expected_version: Number(data.version || 0),
    source_sha256: data.source_sha256,
    mapping_version: Number(data.mapping_version),
    cohort_revision: data.cohort_revision,
    filters: workbookExclusionSelectedPayload(),
  };
}

function workbookExclusionSetStatus(message, bad = false) {
  const node = el("workbook-exclusion-status");
  node.textContent = message;
  node.classList.toggle("bad", bad);
}

function workbookExclusionClear() {
  workbookExclusion.data = null;
  workbookExclusion.selected = workbookExclusionEmptyFilters();
  workbookExclusion.saved = workbookExclusionEmptyFilters();
  workbookExclusion.preview = null;
  workbookExclusion.previewKey = "";
  workbookExclusion.yearId = state.selected;
  workbookExclusion.importId = null;
  for (const facet of workbookExclusionFacets) {
    el("workbook-exclusion-" + facet.id + "-options").replaceChildren();
    el("workbook-exclusion-" + facet.id + "-search").value = "";
    el("workbook-exclusion-" + facet.id + "-filter").open = false;
  }
  el("workbook-exclusion-save").disabled = true;
  el("workbook-exclusion-preview").disabled = true;
  el("workbook-exclusion-status").textContent =
    "Seleziona un report mappato per caricare i valori disponibili.";
  el("workbook-exclusion-preview-result").textContent = "";
  workbookExclusionRenderSummary();
}

async function loadWorkbookExclusions(force = false) {
  const yearId = state.selected;
  const importId = Number(el("workbook-import-id").value);
  if (!yearId || !Number.isInteger(importId) || importId < 1) {
    workbookExclusionClear();
    return;
  }
  if (workbookExclusion.loading) return;
  const sameSource = workbookExclusion.yearId === yearId &&
    workbookExclusion.importId === importId && workbookExclusion.data;
  if (sameSource && !force) return;
  if (sameSource && force && workbookExclusion.previewKey &&
      workbookExclusionFiltersKey(workbookExclusion.selected) !==
      workbookExclusionFiltersKey(workbookExclusion.saved) &&
      !window.confirm("Sono presenti modifiche non salvate ai filtri. Ricaricare e perderle?")) {
    return;
  }
  workbookExclusion.loading = true;
  el("workbook-exclusion-status").textContent = "Lettura dei valori del report in corso…";
  try {
    const data = await api(
      "years/" + yearId + "/department-workbooks/exclusions?import_id=" + importId
    );
    if (yearId !== state.selected ||
        importId !== Number(el("workbook-import-id").value)) return;
    workbookExclusion.data = data;
    workbookExclusion.yearId = yearId;
    workbookExclusion.importId = importId;
    workbookExclusion.selected = workbookExclusionEmptyFilters();
    workbookExclusion.saved = workbookExclusionEmptyFilters();
    if (!data.stale) {
      for (const facet of workbookExclusionFacets) {
        workbookExclusion.selected[facet.key] = new Set(data.filters?.[facet.key] || []);
        workbookExclusion.saved[facet.key] = new Set(data.filters?.[facet.key] || []);
      }
    }
    workbookExclusion.preview = null;
    workbookExclusion.previewKey = "";
    for (const facet of workbookExclusionFacets) {
      el("workbook-exclusion-" + facet.id + "-search").value = "";
      el("workbook-exclusion-" + facet.id + "-filter").open = false;
    }
    workbookExclusionRenderAllFacets();
    el("workbook-exclusion-preview-result").textContent = "";
    const notices = [];
    if (!data.mapped?.titoli) {
      notices.push("Il campo «Titolo affidamento storico» non è associato: completare la mappatura per attivare questa funzione.");
    }
    if (data.stale) {
      notices.push("I criteri salvati si riferiscono a una precedente mappatura o selezione delle annualità. Non verranno applicati finché non saranno verificati e salvati di nuovo.");
    } else if (data.filters?.titoli?.length) {
      notices.push("Criteri salvati: " + data.filters.titoli.length +
        " titoli principali. Saranno applicati soltanto alle righe che superano le esclusioni per annualità.");
    } else {
      notices.push("Nessuna esclusione per titolo salvata. Tutti gli incarichi che superano le esclusioni per annualità restano inclusi.");
    }
    notices.push("I conteggi tra parentesi indicano le righe del report attualmente incluse nell'ambito dei cinque Excel.");
    workbookExclusionSetStatus(notices.join(" "));
    el("workbook-exclusion-preview").disabled =
      state.user?.role === "lettura" || !data.mapped?.titoli;
    el("workbook-exclusion-save").disabled = true;
  } catch (error) {
    workbookExclusionSetStatus(error.message, true);
    el("workbook-exclusion-preview").disabled = true;
    el("workbook-exclusion-save").disabled = true;
  } finally {
    workbookExclusion.loading = false;
  }
}

async function previewWorkbookExclusions() {
  if (!workbookExclusion.data || workbookExclusion.loading) return;
  const button = el("workbook-exclusion-preview");
  button.disabled = true;
  el("workbook-exclusion-preview-result").textContent =
    "Calcolo delle righe corrispondenti ai filtri in corso…";
  try {
    const payload = workbookExclusionSnapshotPayload();
    const result = await api(
      "years/" + state.selected + "/department-workbooks/exclusions/preview",
      "POST", payload
    );
    workbookExclusion.preview = result;
    workbookExclusion.previewKey = workbookExclusionFiltersKey(workbookExclusion.selected);
    const examples = (result.examples || []).slice(0, 12).map(item =>
      "riga " + item.excel_row + " · " + item.assignment_title +
      " · " + item.course + " (" + item.course_code + ", " + item.campus + ")"
    );
    el("workbook-exclusion-preview-result").textContent =
      "Righe che saranno escluse in aggiunta alle esclusioni per annualità: " +
      Number(result.matched_rows || 0).toLocaleString("it-IT") +
      (examples.length ? ". Esempi: " + examples.join("; ") : ".") +
      (Number(result.matched_rows || 0) === 0
        ? " Nessuna riga aggiuntiva corrisponde ai criteri selezionati."
        : "");
    el("workbook-exclusion-save").disabled =
      state.user?.role === "lettura";
    workbookExclusionSetStatus(
      "Anteprima aggiornata. Le esclusioni per titolo non sono ancora attive: salva i criteri per applicarli alla generazione."
    );
  } catch (error) {
    workbookExclusion.preview = null;
    workbookExclusion.previewKey = "";
    el("workbook-exclusion-preview-result").textContent = "";
    workbookExclusionSetStatus(error.message, true);
  } finally {
    button.disabled = state.user?.role === "lettura";
  }
}

async function saveWorkbookExclusions() {
  if (!workbookExclusion.data || workbookExclusion.loading) return;
  const currentKey = workbookExclusionFiltersKey(workbookExclusion.selected);
  if (!workbookExclusion.preview || workbookExclusion.previewKey !== currentKey) {
    showNotice("Calcolare una nuova anteprima prima di salvare i criteri.", true);
    return;
  }
  const count = Number(workbookExclusion.preview.matched_rows || 0);
  const titleCount = workbookExclusion.selected.titoli.size;
  const message = count
    ? "Saranno escluse " + count + " righe aggiuntive dai cinque Excel e riportate nel sesto file interno. Confermi il salvataggio di " + titleCount + " titoli principali?"
    : "La selezione non individua righe aggiuntive. Confermi il salvataggio dei criteri?";
  if (!window.confirm(message)) return;
  const button = el("workbook-exclusion-save");
  button.disabled = true;
  try {
    const payload = workbookExclusionSnapshotPayload();
    const result = await api(
      "years/" + state.selected + "/department-workbooks/exclusions",
      "PUT", payload
    );
    workbookExclusion.data.version = result.version;
    workbookExclusion.data.filters = result.filters;
    workbookExclusion.data.stale = false;
    workbookExclusion.saved = workbookExclusionEmptyFilters();
    for (const facet of workbookExclusionFacets) {
      workbookExclusion.saved[facet.key] = new Set(result.filters?.[facet.key] || []);
    }
    workbookExclusion.preview = result;
    workbookExclusion.previewKey = workbookExclusionFiltersKey(workbookExclusion.selected);
    workbookExclusionSetStatus(
      "Criteri salvati (versione " + result.version + "). Saranno applicati alla prossima generazione dei cinque Excel."
    );
    showNotice(
      "Criteri di esclusione incarichi salvati. Righe aggiuntive individuate: " +
      Number(result.matched_rows || 0) + "."
    );
  } catch (error) {
    workbookExclusionSetStatus(error.message, true);
    showNotice(error.message, true);
  } finally {
    button.disabled = state.user?.role === "lettura";
  }
}

function clearWorkbookExclusionSelections() {
  if (!workbookExclusion.data || state.user?.role === "lettura") return;
  workbookExclusion.selected = workbookExclusionEmptyFilters();
  workbookExclusionMarkDirty();
  workbookExclusionRenderAllFacets();
  el("workbook-exclusion-preview-result").textContent =
    "Tutti i filtri sono stati azzerati. Calcola l'anteprima e salva per rimuovere le esclusioni per titolo già registrate.";
}

function hookWorkbookExclusions() {
  if (workbookExclusion.hooked) return;
  workbookExclusion.hooked = true;
  el("workbook-import-id").addEventListener("change", () => {
    loadWorkbookExclusions(true).catch(error => workbookExclusionSetStatus(error.message, true));
  });
  for (const facet of workbookExclusionFacets) {
    el("workbook-exclusion-" + facet.id + "-search").addEventListener("input", () => {
      workbookExclusionRenderFacet(facet);
    });
    el("workbook-exclusion-" + facet.id + "-pick").addEventListener("click", () => {
      if (state.user?.role === "lettura") return;
      const query = workbookExclusionNormalize(
        el("workbook-exclusion-" + facet.id + "-search").value
      );
      for (const option of workbookExclusion.data?.choices?.[facet.key] || []) {
        if (!query || workbookExclusionNormalize(option.label).includes(query)) {
          workbookExclusion.selected[facet.key].add(option.value);
        }
      }
      workbookExclusionMarkDirty();
      workbookExclusionRenderAllFacets();
    });
    el("workbook-exclusion-" + facet.id + "-clear").addEventListener("click", () => {
      if (state.user?.role === "lettura") return;
      workbookExclusion.selected[facet.key].clear();
      if (facet.key === "titoli") {
        for (const other of workbookExclusionFacets) {
          if (other.key !== "titoli") workbookExclusion.selected[other.key].clear();
        }
      }
      workbookExclusionMarkDirty();
      workbookExclusionRenderAllFacets();
    });
  }
  el("workbook-exclusion-preview").addEventListener("click", () =>
    previewWorkbookExclusions().catch(error => workbookExclusionSetStatus(error.message, true))
  );
  el("workbook-exclusion-save").addEventListener("click", () =>
    saveWorkbookExclusions().catch(error => workbookExclusionSetStatus(error.message, true))
  );
  el("workbook-exclusion-clear").addEventListener("click", clearWorkbookExclusionSelections);
}

window.DidaUPWorkbookExclusions = {
  load: loadWorkbookExclusions,
  hook: hookWorkbookExclusions,
};
