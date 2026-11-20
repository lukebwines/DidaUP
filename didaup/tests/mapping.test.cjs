/* Regression tests for the real mapping.js helper functions (synthetic values). */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const mappingJs = fs.readFileSync(path.join(__dirname, "../app/static/mapping.js"), "utf8");
const context = {document: {addEventListener() {}}};
vm.runInNewContext(mappingJs, context, {filename:"mapping.js"});
const suggested = {assigned: {ssd_insegnamento_originale: 21, ssd_docente_nuovo: 76, ore_previste: 60}};
const saved = {assigned: {
  ssd_insegnamento_vecchio: 21, ssd_insegnamento_originale: 21,
  ssd_docente_vecchio: 76, ssd_docente_nuovo: 76,
  ore_copertura: 60, ore_previste: 60
}};
assert.equal(context.mappingSelectedValue("ssd_insegnamento_originale", suggested, saved, true, true), "21");
assert.equal(context.mappingSelectedValue("ssd_insegnamento_vecchio", suggested, saved, true, true), "");
assert.equal(context.mappingSelectedValue("ssd_docente_vecchio", suggested, saved, true, true), "");
assert.equal(context.mappingSelectedValue("ore_copertura", suggested, saved, true, true), "");
assert.equal(context.mappingSelectedValue("ore_previste", suggested, saved, true, true), "60");
assert.equal(context.mappingSelectedValue("ssd_insegnamento_vecchio", null, saved, false, true), "21");
assert.equal(context.mappingSelectedValue("ssd_insegnamento_vecchio", null, saved, false, false), "");
const conflicts = context.mappingConflicts([
  {value: "21", label: "SSD precedente"},
  {value: "21", label: "SSD originale"},
  {value: "76", label: "SSD docente nuovo"},
  {value: "", label: "Non associato"},
]);
assert.equal(conflicts.length, 1);
assert.equal(conflicts[0].column, 22);
assert.equal(conflicts[0].left, "SSD precedente");
assert.equal(conflicts[0].right, "SSD originale");
assert.equal(context.mappingConflicts([
  {value: "21", label: "SSD originale"},
  {value: "76", label: "SSD docente nuovo"},
  {value: "", label: "Non associato"},
]).length, 0);
console.log("DidaUP mapping regression tests: PASS");
