"use strict";

/* DidaUP: annual workload rules are private administrative configuration. */
const workloadUI = (() => {
  const stateLocal = {year: null, version: 0, rules: [], dirty: false, editing: -1, choices: null};

  function choose(id, values, placeholder, getValue, getLabel) {
    const select = document.getElementById(id);
    select.replaceChildren();
    const wildcard = document.createElement("option");
    wildcard.value = "";
    wildcard.textContent = placeholder;
    select.append(wildcard);
    for (const item of values) {
      const option = document.createElement("option");
      option.value = getValue(item);
      option.textContent = getLabel(item);
      select.append(option);
    }
  }
  function labelOf(rule) {
    const labels = [rule.tipologia || "Tutte", rule.cds || "Tutti", rule.taf || "Tutte"];
    return labels.join(" · ") + " · " + rule.value +
      (rule.mode === "percentuale" ? "%" : " ore");
  }
  function drawRules() {
    const body = document.getElementById("workload-rules");
    body.replaceChildren();
    for (const [index, rule] of stateLocal.rules.entries()) {
      const row = body.insertRow();
      for (const value of [
        rule.tipologia || "Tutte", rule.cds || "Tutti", rule.taf || "Tutte",
        rule.mode === "percentuale" ? "Percentuale" : "Quota fissa",
        rule.value + (rule.mode === "percentuale" ? " %" : " ore")
      ]) row.insertCell().textContent = value;
      const actions = row.insertCell();
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
      cell.colSpan = 6;
      cell.textContent = "Nessuna regola: tutte le TOT ORE EFFETTIVE resteranno a 0.";
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
    document.getElementById("workload-add").textContent = "Aggiungi regola";
    document.getElementById("workload-cancel").hidden = true;
    updateLimit();
  }
  function editRule(index) {
    const rule = stateLocal.rules[index];
    stateLocal.editing = index;
    for (const [field, selector] of [
      ["tipologia", "workload-typologia"], ["cds", "workload-cds"], ["taf", "workload-taf"],
      ["mode", "workload-mode"], ["value", "workload-value"]
    ]) document.getElementById(selector).value = rule[field];
    document.getElementById("workload-add").textContent = "Aggiorna regola";
    document.getElementById("workload-cancel").hidden = false;
    updateLimit();
  }
  function updateLimit() {
    document.getElementById("workload-value").max =
      document.getElementById("workload-mode").value === "percentuale" ? "1000" : "999999";
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
    choose("workload-typologia", result.tipologie, "Tutte le tipologie", x => x, x => x);
    choose("workload-cds", result.cds, "Tutti i CdS", x => x.code,
      x => x.code + (x.name ? " · " + x.name : ""));
    choose("workload-taf", result.taf, "Tutte le TAF", x => x, x => x);
    const missing = [];
    if (!result.mapped.tot_ore_previste) missing.push("TOT ORE PREVISTE");
    if (!result.mapped.tipologia) missing.push("TIPOLOGIA (necessaria per regole per tipologia)");
    if (!result.mapped.taf) missing.push("TAF (necessaria per regole per TAF)");
    document.getElementById("workload-mapping-status").textContent = missing.length
      ? "Associazioni da verificare: " + missing.join("; ") + "."
      : "Associazioni per il calcolo presenti.";
    resetForm();
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
    document.getElementById("workload-source").addEventListener("change", () => {
      choices().catch(error => showNotice(error.message, true));
    });
    document.getElementById("workload-mode").addEventListener("change", updateLimit);
    document.getElementById("workload-cancel").addEventListener("click", resetForm);
    document.getElementById("workload-rule-form").addEventListener("submit", event => {
      event.preventDefault();
      const fields = [
        ["tipologia", "workload-typologia"], ["cds", "workload-cds"], ["taf", "workload-taf"],
        ["mode", "workload-mode"], ["value", "workload-value"]
      ];
      const rule = {};
      for (const [key, selector] of fields)
        rule[key] = document.getElementById(selector).value.trim();
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
          ["workload-total", Number(result.total_effective_hours).toLocaleString("it-IT", {
            maximumFractionDigits: 2
          })],
          ["workload-count-errors", result.errors.length]
        ];
        for (const [id, value] of counts) document.getElementById(id).textContent = String(value);
        const issues = result.errors.slice(0, 25).map(
          issue => "Riga " + issue.excel_row + ": " + issue.reason
        );
        document.getElementById("workload-errors").textContent =
          issues.length ? "Anomalie da correggere: " + issues.join("; ") : "Nessuna anomalia di calcolo.";
        const table = document.getElementById("workload-rule-summary");
        table.replaceChildren();
        for (let index = 0; index < stateLocal.rules.length; index++) {
          const row = table.insertRow();
          row.insertCell().textContent = labelOf(stateLocal.rules[index]);
          row.insertCell().textContent = String(result.per_rule_rows[index] || 0);
        }
        document.getElementById("workload-results").hidden = false;
        document.getElementById("workload-preview-status").textContent =
          result.included_rows + " righe incluse; " + result.excluded_rows +
          " righe escluse dai file. " + (result.blocked
            ? "Calcolo BLOCCATO: risolvere i conflitti prima di generare gli Excel."
            : "Anteprima completata: il calcolo sarà replicato nei cinque Excel.");
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
