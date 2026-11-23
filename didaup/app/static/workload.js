"use strict";

/* DidaUP: annual workload rules are private administrative configuration. */
const workloadUI = (() => {
  const stateLocal = {year: null, version: 0, rules: [], dirty: false, editing: -1, choices: null};

  const criteria = ["typologia", "cds", "taf"];
  const fieldNames = {typologia: "tipologia", cds: "cds", taf: "taf"};
  const defaultLabels = {
    typologia: "Tutte le tipologie", cds: "Tutti i CdS", taf: "Tutte le TAF"
  };
  const groups = Object.fromEntries(criteria.map(key => [
    key, {options: [], selected: new Set(), filter: ""}
  ]));

  function asArray(value) {
    if (Array.isArray(value)) return value.filter(x => typeof x === "string" && x.trim());
    return typeof value === "string" && value.trim() ? [value] : [];
  }
  function criterionSummary(value, fallback, max = 3) {
    const selections = asArray(value);
    if (!selections.length) return fallback;
    const shown = selections.slice(0, max).join(", ");
    return selections.length > max ? shown + " (+" + (selections.length - max) + ")" : shown;
  }
  function labelOf(rule) {
    const labels = [
      criterionSummary(rule.tipologia, "Tutte"),
      criterionSummary(rule.cds, "Tutti"),
      criterionSummary(rule.taf, "Tutte")
    ];
    return labels.join(" · ") + " · " +
      (rule.mode === "non_disponibile" ? "N.D. (non disponibile)" :
       rule.value + (rule.mode === "percentuale" ? "%" : " ore"));
  }
  function multiElement(key, suffix) {
    return document.getElementById("workload-" + key + "-" + suffix);
  }
  function filteredOptions(key) {
    const {options, filter} = groups[key];
    const query = filter.toLocaleLowerCase("it").trim();
    if (!query) return options;
    return options.filter(option =>
      (option.label + " " + option.value).toLocaleLowerCase("it").includes(query)
    );
  }
  function closeMulti(key) {
    multiElement(key, "panel").hidden = true;
    multiElement(key, "toggle").setAttribute("aria-expanded", "false");
  }
  function refreshMulti(key) {
    const group = groups[key];
    const count = group.selected.size;
    const toggle = multiElement(key, "toggle");
    toggle.textContent = count ? count + " selezionat" + (count === 1 ? "o" : "i") : defaultLabels[key];
    toggle.title = count ? [...group.selected].join(", ") : defaultLabels[key];
    multiElement(key, "count").textContent = count
      ? count + " selezionati · " + filteredOptions(key).length + " opzioni visibili"
      : "Nessuna selezione: " + defaultLabels[key].toLowerCase();
    const choices = multiElement(key, "options");
    choices.replaceChildren();
    const visible = filteredOptions(key);
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "Nessuna corrispondenza per la ricerca.";
      choices.append(empty);
    }
    for (const option of visible) {
      const label = document.createElement("label");
      label.className = "workload-multi-option";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = option.value;
      input.checked = group.selected.has(option.value);
      input.addEventListener("change", () => {
        if (input.checked) group.selected.add(option.value);
        else group.selected.delete(option.value);
        // Update counters without recreating focused checkbox rows.
        const n = group.selected.size;
        toggle.textContent = n ? n + " selezionat" + (n === 1 ? "o" : "i") : defaultLabels[key];
        toggle.title = n ? [...group.selected].join(", ") : defaultLabels[key];
        multiElement(key, "count").textContent = n
          ? n + " selezionati · " + visible.length + " opzioni visibili"
          : "Nessuna selezione: " + defaultLabels[key].toLowerCase();
      });
      const title = document.createElement("span");
      title.textContent = option.label;
      label.append(input, title);
      choices.append(label);
    }
    // A saved rule may reference a course that was excluded AFTER saving.
    // Show that stale value only as a warning with a remove action; NEVER
    // reinsert it among the selectable courses, typologies or TAF values.
    const available = new Set(group.options.map(option => option.value));
    const stale = [...group.selected].filter(value => !available.has(value));
    if (stale.length) {
      const container = document.createElement("div");
      container.className = "workload-multi-stale";
      const heading = document.createElement("strong");
      heading.textContent = "Valori della regola non presenti nelle righe incluse:";
      container.append(heading);
      for (const value of stale) {
        const line = document.createElement("div");
        line.textContent = value + " ";
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "secondary";
        remove.textContent = "Rimuovi";
        remove.addEventListener("click", () => {
          group.selected.delete(value);
          refreshMulti(key);
        });
        line.append(remove);
        container.append(line);
      }
      choices.append(container);
    }
  }
  function setMulti(key, values) {
    const group = groups[key];
    const restored = asArray(values);
    group.selected = new Set(restored);
    group.filter = "";
    multiElement(key, "search").value = "";
    refreshMulti(key);
  }
  function configureMulti(key, options) {
    groups[key].options = options;
    setMulti(key, []);
    closeMulti(key);
  }
  function initializeMulti() {
    for (const key of criteria) {
      multiElement(key, "toggle").addEventListener("click", () => {
        const panel = multiElement(key, "panel");
        const opening = panel.hidden;
        criteria.forEach(closeMulti);
        if (opening) {
          panel.hidden = false;
          multiElement(key, "toggle").setAttribute("aria-expanded", "true");
          multiElement(key, "search").focus();
        }
      });
      multiElement(key, "search").addEventListener("input", event => {
        groups[key].filter = event.target.value;
        refreshMulti(key);
      });
      // Enter inside the search box must not submit the whole workload rule.
      multiElement(key, "search").addEventListener("keydown", event => {
        if (event.key === "Enter") event.preventDefault();
      });
      multiElement(key, "all").addEventListener("click", () => {
        for (const option of filteredOptions(key)) groups[key].selected.add(option.value);
        refreshMulti(key);
      });
      multiElement(key, "clear").addEventListener("click", () => {
        groups[key].selected.clear();
        refreshMulti(key);
      });
    }
    document.addEventListener("click", event => {
      if (!event.target.closest(".workload-multi"))
        criteria.forEach(closeMulti);
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") criteria.forEach(closeMulti);
    });
  }
  function drawRules() {
    const body = document.getElementById("workload-rules");
    body.replaceChildren();
    for (const [index, rule] of stateLocal.rules.entries()) {
      const row = body.insertRow();
      row.insertCell().textContent = String(index + 1);
      // Saved rules are preserved, but flagged if their selections no longer
      // occur in any included row. This is NOT a selectable course.
      const currentValues = stateLocal.choices && {
        tipologia: new Set(stateLocal.choices.tipologie),
        cds: new Set(stateLocal.choices.cds.map(item => item.code)),
        taf: new Set(stateLocal.choices.taf)
      };
      const outOfScope = currentValues ? criteria.flatMap(key =>
        asArray(rule[fieldNames[key]])
          .filter(value => !currentValues[fieldNames[key]].has(value))
      ) : [];
      if (outOfScope.length) {
        row.classList.add("workload-rule-out-of-scope");
        row.title = "Regola storica con valori fuori dalle annualità incluse";
      }
      for (const value of [
        criterionSummary(rule.tipologia, "Tutte"),
        criterionSummary(rule.cds, "Tutti"),
        criterionSummary(rule.taf, "Tutte"),
        rule.mode === "non_disponibile" ? "N.D. (non disponibile)" :
          (rule.mode === "percentuale" ? "Percentuale" : "Quota fissa"),
        rule.mode === "non_disponibile" ? "N.D." :
          rule.value + (rule.mode === "percentuale" ? " %" : " ore")
      ]) {
        const cell = row.insertCell();
        cell.textContent = value;
      }
      const actions = row.insertCell();
      if (outOfScope.length) {
        const warning = document.createElement("small");
        warning.className = "workload-rule-warning";
        warning.textContent = "Fuori dalle righe incluse: " + outOfScope.join(", ") +
          ". La regola resta salvata ma questi valori non sono selezionabili.";
        actions.append(warning);
      }
      if (state.user?.role === "admin") {
        const edit = document.createElement("button");
        edit.className = "secondary"; edit.type = "button";
        edit.textContent = "Modifica";
        edit.addEventListener("click", () => editRule(index));
        actions.append(edit);
        const remove = document.createElement("button");
        remove.className = "secondary"; remove.type = "button";
        remove.textContent = "Elimina";
        remove.addEventListener("click", () => {
          stateLocal.rules.splice(index, 1);
          stateLocal.dirty = true;
          resetForm();
          drawRules();
        });
        actions.append(remove);
      } else actions.textContent = "Sola lettura";
    }
    if (!stateLocal.rules.length) {
      const row = body.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 7;
      cell.textContent = "Nessuna regola: TOT ORE EFFETTIVE sarà uguale a TOT ORE PREVISTE (se disponibile).";
    }
    const status = document.getElementById("workload-save-status");
    status.textContent = stateLocal.dirty
      ? "Modifiche non salvate: salva le regole prima di generare i file o calcolare l'anteprima."
      : stateLocal.rules.length + " regole salvate nell'anno selezionato · versione " + stateLocal.version;
    document.getElementById("workload-results").hidden = true;
  }
  function resetForm() {
    stateLocal.editing = -1;
    document.getElementById("workload-rule-form").reset();
    criteria.forEach(key => setMulti(key, []));
    criteria.forEach(closeMulti);
    document.getElementById("workload-add").textContent = "Aggiungi regola";
    document.getElementById("workload-cancel").hidden = true;
    updateLimit();
  }
  function editRule(index) {
    const rule = stateLocal.rules[index];
    stateLocal.editing = index;
    for (const key of criteria) setMulti(key, rule[fieldNames[key]]);
    document.getElementById("workload-mode").value = rule.mode;
    document.getElementById("workload-value").value =
      rule.mode === "non_disponibile" ? "" : rule.value;
    document.getElementById("workload-add").textContent = "Aggiorna regola";
    document.getElementById("workload-cancel").hidden = false;
    updateLimit();
  }
  function updateLimit() {
    const mode = document.getElementById("workload-mode").value;
    const input = document.getElementById("workload-value");
    const unavailable = mode === "non_disponibile";
    document.getElementById("workload-value-wrapper").hidden = unavailable;
    input.disabled = unavailable;
    input.required = !unavailable;
    input.max = mode === "percentuale" ? "1000" : "999999";
    if (unavailable) input.value = "";
  }
  function sourceId() {
    return Number(document.getElementById("workload-source").value);
  }
  async function choices() {
    const source = sourceId();
    if (!Number.isInteger(source) || source < 1) return;
    const result = await api(
      "years/" + state.selected + "/workload/choices?import_id=" + encodeURIComponent(source)
    );
    stateLocal.choices = result;
    configureMulti("typologia", result.tipologie.map(value => ({value, label: value})));
    configureMulti("cds", result.cds.map(item => ({
      value: item.code, label: item.code + (item.name ? " · " + item.name : "")
    })));
    configureMulti("taf", result.taf.map(value => ({value, label: value})));
    const missing = [];
    if (!result.mapped.tot_ore_previste) missing.push("TOT ORE PREVISTE");
    if (!result.mapped.tipologia) missing.push("TIPOLOGIA (necessaria per regole per tipologia)");
    if (!result.mapped.taf) missing.push("TAF (necessaria per regole per TAF)");
    const scope = "Selettori limitati alle " + Number(result.rows_in_scope || 0) +
      " righe incluse nei cinque Excel; " + Number(result.excluded_rows || 0) +
      " righe escluse per CdS, sede e annualità.";
    const scopeWarnings = [];
    if (Number(result.unmatched_exclusion_count || 0)) {
      scopeWarnings.push(result.unmatched_exclusion_count +
        " annualità escluse non trovate nel report associato");
    }
    if (Number(result.mixed_annuality_rows_retained || 0)) {
      scopeWarnings.push(result.mixed_annuality_rows_retained +
        " righe con annualità incluse ed escluse insieme sono state conservate");
    }
    if (Number(result.excluded_course_titles_still_present || 0)) {
      scopeWarnings.push(result.excluded_course_titles_still_present +
        " righe da verificare: denominazioni di CdS esclusi ancora presenti");
    }
    document.getElementById("workload-mapping-status").textContent =
      scope + (missing.length ? " Associazioni da verificare: " + missing.join("; ") + "." :
        " Associazioni per il calcolo presenti.") +
      (scopeWarnings.length ? " ATTENZIONE: " + scopeWarnings.join("; ") + "." : "");
    resetForm();
    drawRules();
    document.getElementById("workload-results").hidden = true;
  }
  async function load() {
    if (!state.selected) return;
    const selectedYear = state.selected;
    const [saved, sources] = await Promise.all([
      api("years/" + selectedYear + "/workload"),
      api("years/" + selectedYear + "/imports"),
    ]);
    if (state.selected !== selectedYear) return;
    stateLocal.year = selectedYear;
    stateLocal.version = saved.version;
    stateLocal.rules = saved.rules.map(rule => ({...rule}));
    stateLocal.dirty = false;
    const pick = document.getElementById("workload-source");
    const previous = pick.value;
    pick.replaceChildren();
    for (const source of sources.filter(item => item.kind === "offerta" && item.mapping_status)) {
      const option = document.createElement("option");
      option.value = String(source.id);
      option.textContent = source.original_name;
      pick.append(option);
    }
    if ([...pick.options].some(option => option.value === previous)) pick.value = previous;
    const available = pick.options.length > 0;
    document.getElementById("workload-preview").disabled = !available;
    document.getElementById("workload-rule-form").querySelectorAll("input,select,button")
      .forEach(control => { control.disabled = !available; });
    document.getElementById("workload-mapping-status").textContent =
      available ? "Caricamento dei valori del report…" : "Mappare un report di offerta prima di configurare le regole.";
    if (available) await choices();
    drawRules();
    if (state.user?.role !== "admin") {
      document.getElementById("workload-save").hidden = true;
      document.getElementById("workload-rule-form").hidden = true;
    } else {
      document.getElementById("workload-save").hidden = false;
      document.getElementById("workload-rule-form").hidden = false;
    }
  }
  function setup() {
    initializeMulti();
    document.getElementById("workload-source").addEventListener("change", () => {
      choices().catch(error => showNotice(error.message, true));
    });
    document.getElementById("workload-mode").addEventListener("change", updateLimit);
    document.getElementById("workload-cancel").addEventListener("click", resetForm);
    document.getElementById("workload-rule-form").addEventListener("submit", event => {
      event.preventDefault();
      const rule = {
        tipologia: [...groups.typologia.selected],
        cds: [...groups.cds.selected],
        taf: [...groups.taf.selected],
        mode: document.getElementById("workload-mode").value,
        value: document.getElementById("workload-mode").value === "non_disponibile"
          ? "N.D." : document.getElementById("workload-value").value.trim()
      };
      if (!rule.value) return;
      if (stateLocal.editing >= 0) stateLocal.rules[stateLocal.editing] = rule;
      else stateLocal.rules.push(rule);
      stateLocal.dirty = true;
      resetForm();
      drawRules();
    });
    document.getElementById("workload-save").addEventListener("click", async () => {
      const button = document.getElementById("workload-save");
      button.disabled = true;
      try {
        const response = await api("years/" + state.selected + "/workload", "PUT", {
          expected_version: stateLocal.version, rules: stateLocal.rules
        });
        stateLocal.rules = response.rules;
        stateLocal.version = response.version;
        stateLocal.dirty = false;
        drawRules();
        showNotice("Regole di carico salvate. La fonte storica non è stata modificata.");
      } catch (error) {
        showNotice(error.message, true);
      } finally { button.disabled = false; }
    });
    document.getElementById("workload-preview").addEventListener("click", async () => {
      if (stateLocal.dirty) {
        showNotice("Salva le modifiche alle regole prima di calcolare l'anteprima.", true);
        return;
      }
      const button = document.getElementById("workload-preview");
      button.disabled = true;
      document.getElementById("workload-preview-status").textContent = "Verifica delle righe incluse in corso…";
      try {
        const result = await api("years/" + state.selected + "/workload/preview?import_id=" +
          encodeURIComponent(sourceId()));
        const counts = [
          ["workload-count-matched", result.rows_calculated],
          ["workload-count-unmatched", result.rows_without_rule],
          ["workload-count-nd", result.rows_not_available || 0],
          ["workload-total", Number(result.total_effective_hours).toLocaleString("it-IT", {
            maximumFractionDigits: 2
          })],
          ["workload-count-missing", result.rows_with_missing_planned_hours || 0],
          ["workload-count-errors", result.error_count ?? result.errors.length]
        ];
        for (const [id, value] of counts) document.getElementById(id).textContent = String(value);
        const issues = result.errors.slice(0, 25).map(
          issue => "Riga " + issue.excel_row + ": " + issue.reason
        );
        const missing = Number(result.rows_with_missing_planned_hours || 0);
        const missingExamples = (result.missing_planned_hours_examples || [])
          .slice(0, 30).map(item => String(item.excel_row));
        document.getElementById("workload-missing-warnings").textContent = missing
          ? "ATTENZIONE: " + missing + " righe con TOT ORE PREVISTE vuoto, " +
            "lasciate a 0 senza applicare la regola. Righe del report (prime " +
            missingExamples.length + "): " + missingExamples.join(", ") +
            ". Verificare che i dati mancanti siano corretti."
          : "Nessuna cella vuota in TOT ORE PREVISTE tra le righe che richiedono un valore numerico.";
        const errorCount = Number(result.error_count ?? result.errors.length);
        document.getElementById("workload-errors").textContent =
          issues.length
            ? errorCount + " errori bloccanti (primi " + issues.length + "): " +
              issues.join("; ")
            : "Nessun errore bloccante di calcolo.";

        const conflictBody = document.getElementById("workload-conflict-pairs");
        const conflictPanel = document.getElementById("workload-conflict-panel");
        conflictBody.replaceChildren();
        const conflictPairs = result.conflict_pairs || [];
        conflictPanel.hidden = conflictPairs.length === 0;
        for (const conflict of conflictPairs) {
          const row = conflictBody.insertRow();
          const descriptions = conflict.rules.map(number => {
            const rule = stateLocal.rules[number - 1];
            return "Regola " + number + ": " +
              (rule ? labelOf(rule) : "non disponibile");
          });
          row.insertCell().textContent = descriptions.join("  ↔  ");
          row.insertCell().textContent = Number(conflict.rows).toLocaleString("it-IT");
          row.insertCell().textContent = (conflict.examples || []).join(", ");
        }

        const table = document.getElementById("workload-rule-summary");
        table.replaceChildren();
        for (let index = 0; index < stateLocal.rules.length; index++) {
          const row = table.insertRow();
          row.insertCell().textContent = "Regola " + (index + 1) + ": " + labelOf(stateLocal.rules[index]);
          row.insertCell().textContent = String(result.per_rule_rows[index] || 0);
        }
        document.getElementById("workload-results").hidden = false;
        document.getElementById("workload-preview-status").textContent =
          result.included_rows + " righe incluse; " + result.excluded_rows +
          " righe escluse dai file. " + (result.blocked
            ? "Calcolo BLOCCATO: correggere i valori non numerici/negativi, i conflitti e le quote fisse eccedenti prima di generare gli Excel."
            : "Anteprima completata: il calcolo sarà replicato nei cinque Excel." +
              (missing ? " ATTENZIONE: " + missing + " righe senza ore previste restano a 0 e richiedono verifica." : ""));
      } catch (error) {
        document.getElementById("workload-preview-status").textContent = error.message;
        showNotice(error.message, true);
      } finally { button.disabled = false; }
    });
  }
  return {load, setup};
})();
window.DidaUPWorkload = workloadUI;
document.addEventListener("DOMContentLoaded", () => workloadUI.setup());
