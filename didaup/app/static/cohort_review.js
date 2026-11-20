"use strict";

const cohortReview = {
  data: null,
  selected: new Set(),
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

function clearCohortReview() {
  cohortReview.data = null;
  cohortReview.selected.clear();
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
  clearCohortReview();
  const select = el("cohort-source-select");
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
  el("cohort-review-load").disabled = false;
}

function visibleCohortCandidates() {
  if (!cohortReview.data) return [];
  const q = normalizeCohortSearch(el("cohort-review-search").value);
  const filter = el("cohort-review-filter").value;
  return cohortReview.data.cohorts.filter(item => {
    const selected = cohortReview.selected.has(cohortKey(item));
    if (filter === "excluded" && !selected) return false;
    if (filter === "included" && selected) return false;
    if (!q) return true;
    return normalizeCohortSearch(
      [item.course_name, item.course_code, item.campus,
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
    for (const value of [entry.course_code, entry.campus, entry.study_year, entry.source_rows]) {
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
  setText("cohort-review-selected", cohortReview.selected.size + " da escludere");
}

async function loadCohortCandidates() {
  if (cohortReview.loading || !state.selected) return;
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
    el("cohort-review-body").hidden = false;
    el("cohort-review-placeholder").hidden = true;
    const notices = [];
    if (data.anomaly_count) notices.push(
      data.anomaly_count + " righe o gruppi del report richiedono verifica e non sono inclusi nell'elenco."
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
  const preview = "Anno " + (state.years.find(y => y.id === data.year_id)?.code || "") +
    ": saranno censite " + data.cohort_count + " annualità, di cui " +
    excluded.length + " ESCLUSE e " + (data.cohort_count - excluded.length) +
    " incluse. I file originali resteranno invariati." +
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
    // Refresh saved row versions and exclusions while preserving the quick search.
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
  el("cohort-check-visible").addEventListener("click", () => {
    for (const row of visibleCohortCandidates()) {
      cohortReview.selected.add(cohortKey(row));
    }
    renderCohortChecklist();
  });
  el("cohort-uncheck-visible").addEventListener("click", () => {
    for (const row of visibleCohortCandidates()) {
      cohortReview.selected.delete(cohortKey(row));
    }
    renderCohortChecklist();
  });
});
