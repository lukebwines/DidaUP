"use strict";

const el = (id) => document.getElementById(id);
const state = {user: null, years: [], selected: null, view: "dashboard", mapping: null, preview: null};
const titles = {
  dashboard: ["PANORAMICA", "Programmazione didattica"],
  cohorts: ["ANNUALITÀ CDS", "Ambito di programmazione"],
  imports: ["IMPORTAZIONE", "Acquisizione report Excel"],
  mapping: ["MAPPATURA", "Riconoscimento colonne"],
  archive: ["ARCHIVIO", "Gestione e azzeramento"],
  workbook: ["GENERA EXCEL", "Cinque file completi per dipartimento"],
  users: ["GESTIONE ACCOUNT", "Utenti autorizzati"],
  security: ["SICUREZZA", "Accesso e credenziali"]
};

function applyTheme(theme) {
  const chosen = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = chosen;
  document.querySelectorAll("[data-theme-toggle]").forEach(btn => {
    btn.textContent = chosen === "dark" ? "☀ Tema chiaro" : "◐ Tema scuro";
    btn.setAttribute("aria-label", chosen === "dark" ? "Attiva modalità chiara" : "Attiva modalità scura");
  });
  try { localStorage.setItem("didaup-theme", chosen); } catch {}
}

function initialTheme() {
  try {
    return localStorage.getItem("didaup-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  } catch { return "light"; }
}

function showNotice(message, bad = false) {
  const node = el("notice");
  node.textContent = message;
  node.classList.toggle("bad", bad);
  node.hidden = false;
}

function hideNotice() { el("notice").hidden = true; }

async function api(path, method = "GET", payload = undefined) {
  const options = {method, credentials: "same-origin", headers: {"Accept": "application/json"}};
  if (payload !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(payload);
  }
  if (method !== "GET" && path !== "login" && state.user) {
    options.headers["X-CSRF-Token"] = state.user.csrf;
  }
  let response;
  try { response = await fetch("api/" + path, options); }
  catch { throw new Error("Impossibile contattare DidaUP"); }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const details = result.detail;
    const message = typeof details === "string" ? details : "Operazione non riuscita";
    if (response.status === 401 && path !== "login") showLogin();
    throw new Error(message);
  }
  return result;
}

function setText(id, value) { el(id).textContent = String(value); }

function showLogin() {
  state.user = null;
  el("login-view").hidden = false;
  el("app-view").hidden = true;
  el("login-password").value = "";
}

async function showApp() {
  state.user = await api("session");
  el("login-view").hidden = true;
  el("app-view").hidden = false;
  setText("user-pill", state.user.username + " · " + state.user.role);
  const admin = state.user.role === "admin";
  const writable = admin || state.user.role === "operatore";
  document.querySelectorAll(".admin-only").forEach(node => node.hidden = !admin);
  document.querySelectorAll(".write-only").forEach(node => node.hidden = !writable);
  if (!admin && ["users", "archive"].includes(state.view)) state.view = "dashboard";
  await refreshYears();
  switchView(state.view);
}

function switchView(view) {
  if (["users", "archive"].includes(view) && state.user?.role !== "admin") return;
  if (!titles[view]) return;
  state.view = view;
  hideNotice();
  document.querySelectorAll(".screen").forEach(node => { node.hidden = node.id !== "view-" + view; });
  document.querySelectorAll(".nav-item").forEach(node => {
    node.classList.toggle("active", node.dataset.view === view);
  });
  setText("breadcrumb", titles[view][0]);
  setText("page-title", titles[view][1]);
  if (view === "users") refreshUsers().catch(e => showNotice(e.message, true));
  if (view === "cohorts") {
    refreshCohorts().catch(e => showNotice(e.message, true));
    refreshCohortSourcePicker().catch(e => showNotice(e.message, true));
  }
  if (view === "imports") refreshImports().catch(e => showNotice(e.message, true));
  if (view === "archive") refreshArchive().catch(e => showNotice(e.message, true));
  if (view === "workbook") refreshWorkbooks().catch(e => showNotice(e.message, true));
}

async function refreshYears(preferred) {
  state.years = await api("years");
  const picker = el("academic-select");
  picker.replaceChildren();
  for (const year of state.years) {
    const option = document.createElement("option");
    option.value = String(year.id);
    option.textContent = year.code;
    picker.appendChild(option);
  }
  const desired = preferred ?? state.selected;
  state.selected = state.years.some(y => y.id === desired) ? desired : state.years[0]?.id ?? null;
  if (state.selected != null) picker.value = String(state.selected);
  const current = state.years.find(y => y.id === state.selected);
  setText("metric-year", current?.code || "—");
  setText("metric-total", current?.total ?? 0);
  setText("metric-excluded", current?.excluded ?? 0);
}

async function refreshImports() {
  const tbody = el("imports-body");
  tbody.replaceChildren();
  if (!state.selected) return;
  const files = await api("years/" + state.selected + "/imports");
  setText("imports-count", files.length + " file");
  el("imports-empty").hidden = files.length > 0;
  for (const file of files) {
    const tr = tbody.insertRow();
    const nameCell = tr.insertCell();
    nameCell.textContent = file.original_name;
    const hash = document.createElement("small");
    hash.textContent = "SHA256: " + file.sha256.slice(0, 12) + "…";
    nameCell.appendChild(hash);
    tr.insertCell().textContent = file.kind === "offerta" ? "Offerta e coperture" : "Docenti di competenza";
    const names = tr.insertCell();
    for (const s of file.sheets) {
      const label = document.createElement("div");
      label.textContent = s.name + " · " + s.rows + " righe · " + s.columns + " colonne";
      names.appendChild(label);
    }
    tr.insertCell().textContent = (file.size_bytes / (1024 * 1024)).toFixed(2) + " MB";
    const status = tr.insertCell();
    status.textContent = file.mapping_status ? "Mappatura in bozza" : "Acquisito · Da mappare";
    status.className = "status off";
    const action = tr.insertCell();
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = file.mapping_status ? "Modifica mappatura" : "Mappa colonne";
    button.addEventListener("click", () => openMapping(file.id).catch(e => showNotice(e.message, true)));
    action.appendChild(button);
  }
}

function updateResetPhrase() {
  const selected = state.years.find(x => x.id === state.selected);
  const phrase = el("reset-scope").value === "all"
    ? "AZZERA LAVORAZIONI" : "AZZERA LAVORAZIONE " + (selected?.code || "AAAA/AA");
  setText("reset-required", phrase);
  return phrase;
}

async function refreshArchive() {
  if (state.user?.role !== "admin") return;
  const summary = await api("admin/archive/summary");
  const body = el("archive-summary-body");
  body.replaceChildren();
  for (const row of summary) {
    const tr = body.insertRow();
    tr.insertCell().textContent = row.code;
    tr.insertCell().textContent = String(row.cohorts);
    tr.insertCell().textContent = String(row.excluded);
    tr.insertCell().textContent = String(row.imports);
    tr.insertCell().textContent = String(row.mappings);
    tr.insertCell().textContent = String(row.working_items);
  }
  updateResetPhrase();
}

async function refreshCohorts() {
  const tbody = el("cohorts-body");
  tbody.replaceChildren();
  if (!state.selected) return;
  const items = await api("years/" + state.selected + "/cohorts");
  setText("cohort-count", items.length + " record");
  el("empty-cohorts").hidden = items.length > 0;
  const writable = state.user.role !== "lettura";
  for (const row of items) {
    const tr = tbody.insertRow();
    const code = tr.insertCell();
    code.textContent = row.course_name;
    const codeDetail = document.createElement("small");
    codeDetail.textContent = row.course_code;
    code.appendChild(codeDetail);
    tr.insertCell().textContent = row.campus;
    tr.insertCell().textContent = String(row.study_year);
    const status = document.createElement("span");
    status.className = "status" + (row.included ? "" : " off");
    status.textContent = row.included ? "Inclusa" : "Esclusa";
    tr.insertCell().appendChild(status);
    tr.insertCell().textContent = row.exclusion_reason || "—";
    const actions = tr.insertCell();
    if (writable) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = row.included ? "Escludi" : "Ripristina";
      button.addEventListener("click", async () => {
        const reason = row.included
          ? window.prompt("Motivazione dell'esclusione (obbligatoria):", "")
          : "";
        if (row.included && reason === null) return;
        try {
          await api("cohorts/" + row.id, "PATCH", {
            included: !row.included, reason: reason || "", expected_version: row.version
          });
          await refreshYears(state.selected);
          await refreshCohorts();
          showNotice(row.included ? "Annualità esclusa: storico conservato" : "Annualità ripristinata");
        } catch (error) {
          showNotice(error.message, true);
          await refreshCohorts();
        }
      });
      actions.appendChild(button);
    } else actions.textContent = "Sola lettura";
  }
}

async function refreshUsers() {
  const tbody = el("users-body");
  tbody.replaceChildren();
  if (!state.user || state.user.role !== "admin") return;
  const users = await api("users");
  for (const user of users) {
    const tr = tbody.insertRow();
    tr.insertCell().textContent = user.username;
    const roleCell = tr.insertCell();
    const selector = document.createElement("select");
    for (const [value, label] of [["admin","Amministratore"],["operatore","Operatore"],["lettura","Sola lettura"]]) {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      selector.appendChild(opt);
    }
    selector.value = user.role;
    selector.disabled = user.id === state.user.id;
    selector.addEventListener("change", async () => {
      try {
        await api("users/" + user.id, "PATCH", {
          role: selector.value, active: Boolean(user.active), expected_version: user.version
        });
        showNotice("Ruolo aggiornato. Le sessioni precedenti sono state revocate.");
        await refreshUsers();
      } catch (error) { showNotice(error.message, true); await refreshUsers(); }
    });
    roleCell.appendChild(selector);
    tr.insertCell().textContent = user.active ? "Attivo" : "Sospeso";
    const action = tr.insertCell();
    if (user.id !== state.user.id) {
      const toggle = document.createElement("button");
      toggle.className = "secondary";
      toggle.type = "button";
      toggle.textContent = user.active ? "Sospendi" : "Riattiva";
      toggle.addEventListener("click", async () => {
        try {
          await api("users/" + user.id, "PATCH", {
            role: user.role, active: !user.active, expected_version: user.version
          });
          await refreshUsers();
          showNotice(user.active ? "Account sospeso" : "Account riattivato");
        } catch (error) { showNotice(error.message, true); await refreshUsers(); }
      });
      action.appendChild(toggle);
    } else action.textContent = "Account corrente";
  }
}


async function downloadDepartmentArchive(path, button) {
  button.disabled = true;
  try {
    const response = await fetch(path, {
      credentials: "same-origin", headers: {"Accept": "application/zip"}
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "Download del pacchetto non riuscito");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    try {
      const a = document.createElement("a");
      a.href = url;
      a.download = "DidaUP_5_file_completi.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } finally { setTimeout(() => URL.revokeObjectURL(url), 1000); }
  } finally { button.disabled = false; }
}

async function refreshWorkbooks() {
  const select = el("workbook-import-id");
  const body = el("workbook-archives");
  select.replaceChildren();
  body.replaceChildren();
  if (!state.selected) return;
  if (state.user?.role === "lettura") {
    el("workbook-progress").textContent = "Generazione riservata ad amministratori e operatori.";
    return;
  }
  const sources = await api("years/" + state.selected + "/imports");
  const mapped = sources.filter(x => x.kind === "offerta" && x.mapping_status);
  for (const source of mapped) {
    const item = document.createElement("option");
    item.value = String(source.id);
    item.textContent = source.original_name + " · " + source.sha256.slice(0, 12) + "…";
    select.appendChild(item);
  }
  el("workbook-generate-button").disabled = !mapped.length;
  el("workbook-progress").textContent = mapped.length
    ? "La generazione usa tutte le attività della fonte, senza filtri per dipartimento."
    : "Nessun report di offerta mappato: acquisire e mappare prima un report sintetico.";
  const existing = await api("years/" + state.selected + "/department-workbooks");
  for (const item of existing) {
    const row = body.insertRow();
    row.insertCell().textContent = "Cinque Excel completi · #" + item.id;
    row.insertCell().textContent = new Date(item.generated_at * 1000).toLocaleString("it-IT");
    const c = row.insertCell();
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = "Scarica ZIP";
    button.addEventListener("click", () => {
      downloadDepartmentArchive(item.download_url, button)
        .catch(e => showNotice(e.message, true));
    });
    c.appendChild(button);
  }
}

function hookForms() {
  el("login-form").addEventListener("submit", async event => {
    event.preventDefault();
    el("login-error").textContent = "";
    try {
      await api("login", "POST", {
        username: el("login-username").value, password: el("login-password").value
      });
      await showApp();
    } catch (error) {
      el("login-error").textContent = error.message;
    }
  });

  el("logout").addEventListener("click", async () => {
    try { await api("logout", "POST", {}); } catch {}
    showLogin();
  });

  el("academic-select").addEventListener("change", async event => {
    state.selected = Number(event.target.value);
    try {
      await refreshYears(state.selected);
      if (state.view === "cohorts") {
        await refreshCohorts();
        await refreshCohortSourcePicker();
      }
      if (state.view === "imports") await refreshImports();
      if (state.view === "archive") await refreshArchive();
      if (state.view === "workbook") await refreshWorkbooks();
    }
    catch (error) { showNotice(error.message, true); }
  });

  el("year-form").addEventListener("submit", async event => {
    event.preventDefault();
    try {
      const year = await api("years", "POST", {code: el("new-year").value.trim()});
      await refreshYears(year.id);
      showNotice("Anno accademico creato senza copiare assegnazioni precedenti");
      el("year-form").reset();
    } catch (error) { showNotice(error.message, true); }
  });

  el("cohort-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (!state.selected) return;
    try {
      await api("years/" + state.selected + "/cohorts", "POST", {
        course_code: el("cohort-code").value.trim(),
        course_name: el("cohort-name").value.trim(),
        campus: el("cohort-campus").value.trim(),
        study_year: Number(el("cohort-study-year").value)
      });
      el("cohort-form").reset();
      el("cohort-study-year").value = "1";
      await refreshYears(state.selected);
      await refreshCohorts();
      showNotice("Annualità inserita per il collaudo");
    } catch (error) { showNotice(error.message, true); }
  });

  el("user-form").addEventListener("submit", async event => {
    event.preventDefault();
    try {
      await api("users", "POST", {
        username: el("new-username").value.trim(),
        role: el("new-role").value,
        password: el("new-user-password").value
      });
      el("user-form").reset();
      await refreshUsers();
      showNotice("Account creato. Comunicare le credenziali tramite un canale sicuro.");
    } catch (error) { showNotice(error.message, true); }
  });

  el("password-form").addEventListener("submit", async event => {
    event.preventDefault();
    try {
      await api("account/password", "POST", {
        current_password: el("current-password").value,
        new_password: el("changed-password").value
      });
      el("password-form").reset();
      showNotice("Password aggiornata e altre sessioni revocate");
    } catch (error) { showNotice(error.message, true); }
  });

  el("go-cohorts").addEventListener("click", () => switchView("cohorts"));
  el("go-imports").addEventListener("click", () => switchView("imports"));
  document.querySelectorAll("[data-theme-toggle]").forEach(button => {
    button.addEventListener("click", () => {
      applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
    });
  });
  el("reset-scope").addEventListener("change", updateResetPhrase);
  el("import-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (!state.selected) return;
    const file = el("import-file").files[0];
    if (!file) return;
    if (file.size > 32 * 1024 * 1024) { showNotice("File superiore a 32 MB", true); return; }
    const form = new FormData();
    form.append("kind", el("import-kind").value);
    form.append("test_data_only", String(el("import-synthetic").checked));
    form.append("source", file, file.name);
    const submit = el("import-submit");
    submit.disabled = true;
    setText("import-progress", "Acquisizione e lettura dei fogli in corso…");
    try {
      const response = await fetch("api/years/" + state.selected + "/imports", {
        method: "POST", credentials: "same-origin",
        headers: {"X-CSRF-Token": state.user.csrf}, body: form
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Importazione fallita");
      await refreshImports();
      el("import-form").reset();
      showNotice("Report acquisito. La struttura è stata letta; la mappatura degli incarichi deve ancora essere validata.");
    } catch (error) {
      showNotice(error.message, true);
    } finally {
      submit.disabled = false;
      setText("import-progress", "");
    }
  });

  el("workbook-generate-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (!state.selected) return;
    const sourceId = Number(el("workbook-import-id").value);
    if (!Number.isInteger(sourceId) || sourceId < 1) return;
    const button = el("workbook-generate-button");
    button.disabled = true;
    el("workbook-progress").textContent = "Creazione delle cinque copie in corso…";
    try {
      const result = await api("years/" + state.selected + "/department-workbooks",
        "POST", {import_id: sourceId});
      showNotice("Generati cinque file identici con " +
        result.historical_rows + " righe storiche ciascuno; nessun filtro dipartimentale. " +
        "Il pacchetto ZIP è disponibile per il download.");
      await refreshWorkbooks();
    } catch (error) {
      showNotice(error.message, true);
    } finally {
      button.disabled = false;
    }
  });

  el("workbook-review-form").addEventListener("submit", async event => {
    event.preventDefault();
    const uploads = [...el("workbook-review-files").files];
    if (uploads.length !== 5) {
      showNotice("Selezionare esattamente cinque file Excel.", true);
      return;
    }
    if (uploads.some(f => f.size > 32 * 1024 * 1024 || !f.name.toLowerCase().endsWith(".xlsx"))) {
      showNotice("Sono consentiti solo file XLSX, massimo 32 MB ciascuno.", true);
      return;
    }
    const sourceId = Number(el("workbook-import-id").value);
    if (!Number.isInteger(sourceId) || sourceId < 1) {
      showNotice("Selezionare un report mappato.", true);
      return;
    }
    const button = el("workbook-review-button");
    button.disabled = true;
    el("workbook-review-result").textContent = "Controllo delle cinque proposte in corso…";
    el("workbook-overlaps").replaceChildren();
    const data = new FormData();
    data.append("import_id", String(sourceId));
    data.append("test_data_only", "true");
    for (const f of uploads) data.append("files", f, f.name);
    try {
      const response = await fetch(
        "api/years/" + state.selected + "/department-workbooks/review",
        {method: "POST", credentials: "same-origin",
          headers: {"X-CSRF-Token": state.user.csrf}, body: data}
      );
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(typeof result.detail === "string" ? result.detail : "Analisi non riuscita");
      }
      const message = result.blocked
        ? "Revisione NON superata: " + result.overlap_count +
          " sovrapposizioni tra file, " + result.issue_count_at_least +
          " anomalie. Nessuna proposta acquisita o approvata."
        : "Nessuna sovrapposizione o anomalia strutturale rilevata. "
          + "Si tratta di un'anteprima, non di un'approvazione.";
      const examples = (result.issues || []).slice(0, 12).map(x =>
        "File " + x.file + (x.excel_row ? ", riga " + x.excel_row : "") +
        ": " + x.reason);
      el("workbook-review-result").textContent =
        message + (examples.length ? "\n" + examples.join("\n") : "");
      el("workbook-review-result").style.whiteSpace = "pre-line";
      for (const overlap of result.overlaps || []) {
        const row = el("workbook-overlaps").insertRow();
        row.insertCell().textContent = overlap.activity_id;
        row.insertCell().textContent = overlap.files.join(", ");
        row.insertCell().textContent = overlap.identical_proposals
          ? "Proposta ripetuta: da verificare" : "Proposte differenti: da risolvere";
      }
      showNotice(message, Boolean(result.blocked));
    } catch (error) {
      el("workbook-review-result").textContent = "Nessuna proposta acquisita.";
      showNotice(error.message, true);
    } finally {
      button.disabled = false;
    }
  });

  el("archive-reset-form").addEventListener("submit", async event => {
    event.preventDefault();
    const phrase = updateResetPhrase();
    if (el("reset-confirmation").value !== phrase) {
      showNotice("La conferma testuale non corrisponde. Nessun dato eliminato.", true);
      return;
    }
    if (!window.confirm("Confermi l'eliminazione dei soli file temporanei di lavorazione? Report, esclusioni e mappature resteranno conservati.")) return;
    const scope = el("reset-scope").value;
    try {
      const result = await api("admin/archive/reset", "POST", {
        scope, year_id: scope === "year" ? state.selected : null,
        confirmation: el("reset-confirmation").value,
        password: el("reset-password").value
      });
      el("archive-reset-form").reset();
      await refreshArchive();
      showNotice(result.message + " File di lavoro eliminati: " +
        result.deleted_working_items + ". Selezioni e mappature inalterate." +
        (result.file_removal_failures ? " ATTENZIONE: " +
          result.file_removal_failures + " rimozioni da verificare." : ""));
    } catch (error) {
      showNotice(error.message, true);
    } finally {
      el("reset-password").value = "";
      updateResetPhrase();
    }
  });
  document.querySelectorAll(".nav-item").forEach(node => node.addEventListener("click", () => switchView(node.dataset.view)));
}

document.addEventListener("DOMContentLoaded", async () => {
  applyTheme(initialTheme());
  hookForms();
  try { await showApp(); }
  catch { showLogin(); }
});
