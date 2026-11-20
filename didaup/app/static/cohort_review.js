"use strict";

const cohortReview = {
  data: null,
  selected: new Set(),
  saved: new Set(),
  filters: {courses: new Set(), campuses: new Set(), years: new Set(), types: new Set(), assignments: new Set()},
  sourceYear: null,
  loading: false,
};

function cohortKey(row) {
  // Encode an unambiguous stable key. Never use a row number as a CdS identity.
  return JSON.stringify([row.course_code, row.campus, Number(row.study_year)]);
}

function normalizeCohortSearch(value) {
  return String(value ?? "").normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("it-IT").trim();
}

function pendingCohortChanges() {
  if (!cohortReview.data) return {exclude: 0, restore: 0};
  let exclude = 0, restore = 0;
  for (const item of cohortReview.data.cohorts) {
    const key = cohortKey(item);
    if (cohortReview.selected.has(key) && !cohortReview.saved.has(key)) exclude++;
    if (!cohortReview.selected.has(key) && cohortReview.saved.has(key)) restore++;
  }
  return {exclude, restore};
}

function cohortFacetOptions(kind) {
  if (!cohortReview.data) return [];
  const values = new Map();
  for (const item of cohortReview.data.cohorts) {
    if (kind === "courses") {
      if (!values.has(item.course_code)) {
        values.set(item.course_code, item.course_name + " · " + item.course_code);
      }
    } else if (kind === "campuses") {
      values.set(item.campus, item.campus);
    } else if (kind === "years") {
      values.set(String(item.study_year), item.study_year + "° anno");
    } else if (kind === "types") {
      for (const type of (item.course_types || [""])) {
        values.set(type, type || "Non indicata nel report");
      }
    } else if (kind === "assignments") {
      for (const title of (item.assignment_titles || [""])) {
        values.set(title, title || "Non indicato nel report");
      }
    }
  }
  return [...values].map(([value, label]) => ({value, label})).sort(
    (a, b) => kind === "years"
      ? Number(a.value) - Number(b.value)
      : a.label.localeCompare(b.label, "it")
  );
}

function renderCohortFacet(kind) {
  const ids = {courses: "cds", campuses: "campus", years: "year", types: "type", assignments: "assignment"};
  const id = ids[kind], container = el("cohort-" + id + "-options");
  const chosen = cohortReview.filters[kind];
  const terms = kind === "courses"
    ? normalizeCohortSearch(el("cohort-cds-search").value)
    : kind === "assignments"
      ? normalizeCohortSearch(el("cohort-assignment-search").value) : "";
  const items = cohortFacetOptions(kind).filter(x =>
    !terms || normalizeCohortSearch(x.label).includes(terms)
  );
  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const label = document.createElement("label");
    label.className = "cohort-filter-choice";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = chosen.has(item.value);
    checkbox.setAttribute("aria-label", item.label);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) chosen.add(item.value);
      else chosen.delete(item.value);
      updateFacetSummary(kind);
      renderCohortChecklist();
    });
    const name = document.createElement("span");
    name.textContent = item.label;
    label.append(checkbox, name);
    fragment.appendChild(label);
  }
  container.replaceChildren(fragment);
  if (!items.length) {
    const empty = document.createElement("span");
    empty.className = "muted";
    empty.textContent = "Nessuna corrispondenza";
    container.appendChild(empty);
  }
  updateFacetSummary(kind);
}

function updateFacetSummary(kind) {
  const ids = {courses: "cds", campuses: "campus", years: "year", types: "type", assignments: "assignment"};
  const singular = {courses: "CdS", campuses: "Sedi", years: "Anni", types: "Tipologie", assignments: "Titolo affidamento"};
  const all = {courses: "Tutti", campuses: "Tutte", years: "Tutti", types: "Tutte", assignments: "Tutti"};
  const count = cohortReview.filters[kind].size;
  setText("cohort-" + ids[kind] + "-summary",
    singular[kind] + " · " + (count ? count + " selezionati" : all[kind]));
}

function resetCohortFacets() {
  for (const filter of Object.values(cohortReview.filters)) filter.clear();
  el("cohort-cds-search").value = "";
  el("cohort-assignment-search").value = "";
  el("cohort-review-search").value = "";
  el("cohort-review-filter").value = "all";
  for (const kind of ["types", "assignments", "courses", "campuses", "years"]) renderCohortFacet(kind);
  renderCohortChecklist();
}

function clearCohortReview() {
  cohortReview.data = null;
  cohortReview.selected.clear();
  cohortReview.saved.clear();
  for (const facet of Object.values(cohortReview.filters)) facet.clear();
  el("cohort-cds-search").value = "";
  el("cohort-assignment-search").value = "";
  for (const id of ["type", "assignment", "cds", "campus", "year"]) {
    el("cohort-" + id + "-filter").open = false;
    el("cohort-" + id + "-options").replaceChildren();
  }
  cohortReview.sourceYear = state.selected;
  el("cohort-review-body").hidden = true;
  el("cohort-review-placeholder").hidden = false;
  el("cohort-review-search").value = "";
  el("cohort-review-filter").value = "all";
  el("cohort-review-rows").replaceChildren();
  setText("cohort-review-placeholder",
    "Seleziona un report mappato e premi «Ricava elenco dal report».");
}

async function refreshCohortSourcePicker() {
  const yearId = state.selected;
  const select = el("cohort-source-select");
  const currentSource = select.value;
  // Returning to this view must NOT silently delete unsaved checkbox changes.
  const keep = Boolean(cohortReview.data &&
    cohortReview.sourceYear === yearId &&
    String(cohortReview.data.import_id) === currentSource);
  if (!keep) clearCohortReview();
  select.replaceChildren();
  if (!yearId) return;
  const sources = await api("years/" + yearId + "/imports");
  if (yearId !== state.selected) return;
  const candidates = sources.filter(s => s.kind === "offerta" && s.mapping_status);
  if (!candidates.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "Nessun report dell'offerta con mappatura salvata";
    select.appendChild(option);
    el("cohort-review-load").disabled = true;
    return;
  }
  for (const source of candidates) {
    const option = document.createElement("option");
    option.value = String(source.id);
    option.textContent = source.original_name + " · " +
      source.sheets.map(s => s.name).join(", ");
    select.appendChild(option);
  }
  if (keep && candidates.some(x => String(x.id) === currentSource)) {
    select.value = currentSource;
  } else if (keep) {
    clearCohortReview();
  }
  el("cohort-review-load").disabled = false;
}

function visibleCohortCandidates() {
  if (!cohortReview.data) return [];
  const q = normalizeCohortSearch(el("cohort-review-search").value);
  const filter = el("cohort-review-filter").value;
  const {courses, campuses, years, types, assignments} = cohortReview.filters;
  return cohortReview.data.cohorts.filter(item => {
    const key = cohortKey(item);
    const selected = cohortReview.selected.has(key);
    const saved = cohortReview.saved.has(key);
    if (filter === "excluded" && !selected) return false;
    if (filter === "included" && selected) return false;
    if (filter === "changed" && selected === saved) return false;
    if (courses.size && !courses.has(item.course_code)) return false;
    if (campuses.size && !campuses.has(item.campus)) return false;
    if (years.size && !years.has(String(item.study_year))) return false;
    if (types.size && !(item.course_types || [""]).some(t => types.has(t))) return false;
    if (assignments.size && !(item.assignment_titles || [""]).some(t => assignments.has(t))) return false;
    if (!q) return true;
    return normalizeCohortSearch(
      [item.course_name, item.course_code, item.campus,
       ...(item.course_types || []), ...(item.assignment_titles || []),
       item.study_year, item.study_year + " anno"].join(" ")
    ).includes(q);
  });
}

function renderCohortChecklist() {
  const body = el("cohort-review-rows");
  body.replaceChildren();
  const data = cohortReview.data;
  if (!data) return;
  const visible = visibleCohortCandidates();
  const writable = state.user?.role !== "lettura";
  const fragment = document.createDocumentFragment();
  for (const entry of visible) {
    const tr = document.createElement("tr");
    const choice = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "cohort-exclude-checkbox";
    checkbox.checked = cohortReview.selected.has(cohortKey(entry));
    checkbox.disabled = !writable;
    checkbox.setAttribute("aria-label",
      "Escludi " + entry.course_name + ", " + entry.campus + ", anno " + entry.study_year);
    checkbox.addEventListener("change", () => {
      const key = cohortKey(entry);
      if (checkbox.checked) cohortReview.selected.add(key);
      else cohortReview.selected.delete(key);
      renderCohortChecklist();
    });
    choice.appendChild(checkbox);
    tr.appendChild(choice);
    const name = document.createElement("td");
    name.textContent = entry.course_name;
    if (entry.exclusion_reason) {
      const detail = document.createElement("small");
      detail.textContent = "Motivazione precedente: " + entry.exclusion_reason;
      name.appendChild(detail);
    }
    tr.appendChild(name);
    for (const value of [
      (entry.course_types || [""]).map(t => t || "Non indicata").join(" · "),
      (entry.assignment_titles || [""]).map(t => t || "Non indicato").join(" · "),
      entry.course_code, entry.campus, entry.study_year, entry.source_rows
    ]) {
      const cell = document.createElement("td");
      cell.textContent = String(value);
      tr.appendChild(cell);
    }
    if (checkbox.checked) tr.classList.add("cohort-excluded-row");
    fragment.appendChild(tr);
  }
  body.appendChild(fragment);
  el("cohort-review-empty").hidden = visible.length !== 0;
  setText("cohort-review-count", visible.length + " visibili / " +
    data.cohort_count + " annualità");
  setText("cohort-review-selected", cohortReview.selected.size + " da escludere (bozza)");
  setText("cohort-review-saved", cohortReview.saved.size + " escluse già salvate");
  const diff = pendingCohortChanges();
  setText("cohort-review-pending", (diff.exclude + diff.restore) +
    " modifiche non salvate (+" + diff.exclude + " esclusioni, " +
    diff.restore + " ripristini)");
}

async function loadCohortCandidates() {
  if (cohortReview.loading || !state.selected) return;
  const pending = pendingCohortChanges();
  if ((pending.exclude || pending.restore) &&
      !window.confirm("Sono presenti modifiche non salvate alle esclusioni. " +
        "Ricaricare dal report e perdere la bozza?")) return;
  const importId = Number(el("cohort-source-select").value);
  if (!Number.isInteger(importId) || importId < 1) {
    showNotice("Selezionare prima un report dell'offerta già mappato.", true);
    return;
  }
  const yearId = state.selected;
  cohortReview.loading = true;
  el("cohort-review-load").disabled = true;
  setText("cohort-review-placeholder", "Lettura delle annualità dal report in corso…");
  try {
    const data = await api("years/" + yearId + "/cohort-candidates?import_id=" + importId);
    if (yearId !== state.selected) return;
    cohortReview.data = data;
    cohortReview.sourceYear = yearId;
    cohortReview.selected = new Set(
      data.cohorts.filter(c => c.excluded).map(cohortKey)
    );
    cohortReview.saved = new Set(cohortReview.selected);
    for (const facet of Object.values(cohortReview.filters)) facet.clear();
    el("cohort-cds-search").value = "";
    el("cohort-assignment-search").value = "";
    el("cohort-review-search").value = "";
    el("cohort-review-filter").value = "all";
    for (const kind of ["types", "courses", "campuses", "years"]) {
      renderCohortFacet(kind);
    }
    el("cohort-review-body").hidden = false;
    el("cohort-review-placeholder").hidden = true;
    const notices = [];
    if (!data.typology_mapped) notices.push(
      "Tipologia non associata nella mappatura del report: associa il campo CdS · tipologia per attivare il filtro."
    );
    if (!data.assignment_title_mapped) notices.push(
      "Titolo affidamento non associato: mappa il campo «Titolo affidamento storico» prima di utilizzare il relativo filtro."
    );
    if (data.anomaly_count) notices.push(
      data.anomaly_count + " righe o gruppi del report richiedono verifica e non sono inclusi nell'elenco."
    );
    if (data.assignment_title_mapped && data.cohorts.some(
      item => (item.assignment_titles || []).length > 1
    )) notices.push(
      "Alcune annualità comprendono più titoli affidamento. Il filtro serve a trovarle: escluderle elimina tutte le attività di quell'annualità, non soltanto il titolo selezionato."
    );
    if (data.conflicts?.length) notices.push(
      data.conflicts.length + " annualità hanno denominazioni discordanti rispetto al registro: non salvare prima di risolverle."
    );
    if (data.existing_outside_report) notices.push(
      data.existing_outside_report + " annualità già censite non sono presenti nel report selezionato e resteranno invariate."
    );
    if (!notices.length) notices.push(
      "Elenco ottenuto dal report. Spuntare soltanto le annualità non più in gestione."
    );
    setText("cohort-review-notice", notices.join(" "));
    el("cohort-review-save").disabled =
      !data.cohort_count || Boolean(data.conflicts?.length) || state.user?.role === "lettura";
    renderCohortChecklist();
  } catch (error) {
    if (yearId === state.selected) {
      showNotice(error.message, true);
      el("cohort-review-body").hidden = true;
      el("cohort-review-placeholder").hidden = false;
      setText("cohort-review-placeholder",
        "Controlla la mappatura e il formato dei dati nel report.");
    }
  } finally {
    cohortReview.loading = false;
    el("cohort-review-load").disabled = !el("cohort-source-select").value;
  }
}

async function saveCohortSelections() {
  if (!cohortReview.data || cohortReview.loading) return;
  const data = cohortReview.data;
  if (data.year_id !== state.selected || cohortReview.sourceYear !== state.selected) {
    showNotice("L'anno accademico è cambiato: ricaricare l'elenco.", true);
    return;
  }
  const reason = el("cohort-review-reason").value.trim();
  if (cohortReview.selected.size && reason.length < 3) {
    showNotice("Inserire una motivazione per le esclusioni.", true);
    return;
  }
  if (data.conflicts?.length) {
    showNotice("Risolvere le denominazioni CdS discordanti prima di salvare.", true);
    return;
  }
  const excluded = data.cohorts.filter(r => cohortReview.selected.has(cohortKey(r)))
    .map(r => ({
      course_code: r.course_code, campus: r.campus, study_year: r.study_year,
    }));
  const delta = pendingCohortChanges();
  const preview = "Anno " + (state.years.find(y => y.id === data.year_id)?.code || "") +
    ": saranno censite " + data.cohort_count + " annualità, di cui " +
    excluded.length + " ESCLUSE e " + (data.cohort_count - excluded.length) +
    " incluse. Rispetto alle scelte già salvate: " +
    delta.exclude + " nuove esclusioni e " + delta.restore +
    " ripristini. I file originali resteranno invariati." +
    (data.anomaly_count
      ? " ATTENZIONE: " + data.anomaly_count +
        " righe/gruppi anomali non verranno acquisiti e dovranno essere verificati."
      : "") +
    " Confermi il salvataggio?";
  if (!window.confirm(preview)) return;
  cohortReview.loading = true;
  el("cohort-review-save").disabled = true;
  try {
    const result = await api("years/" + data.year_id + "/cohort-candidates/apply", "POST", {
      import_id: data.import_id, mapping_version: data.mapping_version,
      expected_revision: data.expected_revision,
      excluded, reason, acknowledge_anomalies: data.anomaly_count > 0,
    });
    showNotice("Ambito salvato: " + result.total + " annualità censite, " +
      result.excluded + " escluse, " + result.added + " nuove voci.");
    await refreshYears(data.year_id);
    await refreshCohorts();
    // The server has just acknowledged this exact selection: refresh without
    // warning that the newly saved choices are still unsaved edits.
    cohortReview.saved = new Set(cohortReview.selected);
    cohortReview.loading = false;
    await loadCohortCandidates();
  } catch (error) {
    showNotice(error.message + " Nessuna modifica parziale è stata salvata.", true);
  } finally {
    cohortReview.loading = false;
    el("cohort-review-save").disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  el("cohort-source-select").addEventListener("change", clearCohortReview);
  el("cohort-review-save").addEventListener("click", () =>
    saveCohortSelections().catch(error => showNotice(error.message, true)));
  el("cohort-review-load").addEventListener("click", () =>
    loadCohortCandidates().catch(e => showNotice(e.message, true)));
  el("cohort-review-search").addEventListener("input", renderCohortChecklist);
  el("cohort-review-filter").addEventListener("change", renderCohortChecklist);
  el("cohort-cds-search").addEventListener("input", () => renderCohortFacet("courses"));
  el("cohort-assignment-search").addEventListener("input", () => renderCohortFacet("assignments"));
  el("cohort-assignment-pick").addEventListener("click", () => {
    const term = normalizeCohortSearch(el("cohort-assignment-search").value);
    if (!term) {
      showNotice("Inserisci prima un testo per selezionare i titoli affidamento.", true);
      return;
    }
    for (const item of cohortFacetOptions("assignments")) {
      if (normalizeCohortSearch(item.label).includes(term)) {
        cohortReview.filters.assignments.add(item.value);
      }
    }
    renderCohortFacet("assignments");
    renderCohortChecklist();
  });
  el("cohort-cds-pick").addEventListener("click", () => {
    const term = normalizeCohortSearch(el("cohort-cds-search").value);
    if (!term) {
      showNotice("Scrivi prima parte del nome o del codice CdS da selezionare.", true);
      return;
    }
    for (const item of cohortFacetOptions("courses")) {
      if (normalizeCohortSearch(item.label).includes(term)) {
        cohortReview.filters.courses.add(item.value);
      }
    }
    renderCohortFacet("courses");
    renderCohortChecklist();
  });
  for (const [kind, id] of [
    ["types", "type"], ["assignments", "assignment"],
    ["courses", "cds"], ["campuses", "campus"], ["years", "year"]
  ]) {
    el("cohort-" + id + "-clear").addEventListener("click", () => {
      cohortReview.filters[kind].clear();
      if (kind === "courses") el("cohort-cds-search").value = "";
      if (kind === "assignments") el("cohort-assignment-search").value = "";
      renderCohortFacet(kind);
      renderCohortChecklist();
    });
  }
  el("cohort-clear-filters").addEventListener("click", resetCohortFacets);
  el("cohort-discard-pending").addEventListener("click", () => {
    const pending = pendingCohortChanges();
    if (!pending.exclude && !pending.restore) return;
    if (!window.confirm("Annullare le modifiche non ancora salvate? " +
      "Le esclusioni registrate nel database resteranno invariate.")) return;
    cohortReview.selected = new Set(cohortReview.saved);
    renderCohortChecklist();
  });
  el("cohort-check-visible").addEventListener("click", () => {
    const visible = visibleCohortCandidates();
    const changed = visible.filter(row =>
      !cohortReview.selected.has(cohortKey(row)));
    if (!changed.length) return;
    const partialTitles = cohortReview.filters.assignments.size && changed.some(row =>
      (row.assignment_titles || []).some(t => !cohortReview.filters.assignments.has(t))
    );
    if (!window.confirm("Escludere " + changed.length + " annualità tra le " +
        visible.length + " visualizzate? Le altre annualità non saranno modificate. " +
        (partialTitles
          ? "ATTENZIONE: alcune annualità comprendono titoli affidamento differenti dai valori filtrati; verranno escluse per INTERO. "
          : "") +
        "La conferma NON salva ancora nel database.")) return;
    for (const row of changed) cohortReview.selected.add(cohortKey(row));
    renderCohortChecklist();
  });
  el("cohort-uncheck-visible").addEventListener("click", () => {
    const visible = visibleCohortCandidates();
    const changed = visible.filter(row =>
      cohortReview.selected.has(cohortKey(row)));
    if (!changed.length) return;
    if (!window.confirm("Ripristinare " + changed.length + " annualità tra le " +
        visible.length + " visualizzate? Le altre annualità non saranno modificate. " +
        "La conferma NON salva ancora nel database.")) return;
    for (const row of changed) cohortReview.selected.delete(cohortKey(row));
    renderCohortChecklist();
  });
});
