"use strict";
/* Only synthetic labels. Source report data are never committed to GitHub. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const code = fs.readFileSync(
  path.join(__dirname, "../app/static/cohort_review.js"), "utf8"
);
const controls = {
  "cohort-review-search": {value: ""},
  "cohort-review-filter": {value: "all"},
};
const context = vm.createContext({
  document: {addEventListener() {}},
  el: (name) => controls[name],
});
vm.runInContext(code, context, {filename: "cohort_review.js"});
const first = {
  course_code: "SYN01", course_name: "Tecniche sintetiche", campus: "Sede A",
  study_year: 1, source_rows: 2
};
const second = {
  course_code: "SYN01", course_name: "Tecniche sintetiche", campus: "Sede A",
  study_year: 2, source_rows: 3
};
const third = {
  course_code: "SYN02", course_name: "Esempio artificiale", campus: "Sede B",
  study_year: 1, source_rows: 1
};
assert.notEqual(context.cohortKey(first), context.cohortKey(second));
assert.equal(
  context.cohortKey(first),
  context.cohortKey({...first, course_name: "Nome diverso"}),
  "The code, campus and study year—not the display name—identify an annuality"
);
assert.equal(context.normalizeCohortSearch("  CITTÀ  "), "citta");
vm.runInContext("cohortReview.data = {cohorts: []};", context);
context.__fixture = [first, second, third];
vm.runInContext("cohortReview.data = {cohorts: __fixture};", context);
controls["cohort-review-search"].value = "SYN01";
assert.equal(context.visibleCohortCandidates().length, 2);
vm.runInContext(
  "cohortReview.selected.add(cohortKey(__fixture[1]));", context
);
controls["cohort-review-filter"].value = "excluded";
assert.equal(context.visibleCohortCandidates().length, 1);
assert.equal(context.visibleCohortCandidates()[0].study_year, 2);
controls["cohort-review-search"].value = "Sede B";
assert.equal(context.visibleCohortCandidates().length, 0,
  "Search does not erase hidden checkboxes or selected state");
controls["cohort-review-search"].value = "";
assert.equal(context.visibleCohortCandidates().length, 1);
console.log("DidaUP cohort checklist search tests: PASS");
