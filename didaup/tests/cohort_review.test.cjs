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
  study_year: 1, source_rows: 2, assignment_titles: ["Interno", "Esterno"]
};
const second = {
  course_code: "SYN01", course_name: "Tecniche sintetiche", campus: "Sede A",
  study_year: 2, source_rows: 3, assignment_titles: ["Esterno"]
};
const third = {
  course_code: "SYN02", course_name: "Esempio artificiale", campus: "Sede B",
  study_year: 1, source_rows: 1, assignment_titles: ["Convenzione"]
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

// Multiselect facets compose with search and checkbox state; no checkbox gets
// dropped merely because its row becomes hidden.
controls["cohort-review-search"].value = "";
controls["cohort-review-filter"].value = "all";
vm.runInContext("cohortReview.filters.courses.add('SYN01');", context);
assert.equal(context.visibleCohortCandidates().length, 2);
vm.runInContext("cohortReview.filters.campuses.add('Sede B');", context);
assert.equal(context.visibleCohortCandidates().length, 0,
  "Course and campus selections must combine with AND");
vm.runInContext("cohortReview.filters.campuses.clear();", context);
vm.runInContext("cohortReview.filters.years.add('1');", context);
assert.equal(context.visibleCohortCandidates().length, 1);
assert.equal(context.visibleCohortCandidates()[0].course_code, "SYN01");
vm.runInContext("cohortReview.filters.courses.clear();", context);
assert.equal(context.visibleCohortCandidates().length, 2,
  "Multiple CdS are possible; a clear facet does not erase other choices");
vm.runInContext("cohortReview.filters.years.clear();", context);
assert.equal(context.visibleCohortCandidates().length, 3);
assert.equal(context.cohortFacetOptions("courses").length, 2);
assert.equal(context.cohortFacetOptions("campuses").length, 2);
assert.equal(context.cohortFacetOptions("years").length, 2);
assert.equal(context.pendingCohortChanges().exclude, 1);
assert.equal(context.pendingCohortChanges().restore, 0);
vm.runInContext("cohortReview.saved.add(cohortKey(__fixture[1]));", context);
assert.equal(context.pendingCohortChanges().exclude, 0);
vm.runInContext("cohortReview.selected.delete(cohortKey(__fixture[1]));", context);
assert.equal(context.pendingCohortChanges().restore, 1);
controls["cohort-review-filter"].value = "changed";
assert.equal(context.visibleCohortCandidates().length, 1);
assert.equal(context.visibleCohortCandidates()[0].study_year, 2);
controls["cohort-review-filter"].value = "all";
// Do not classify the filter choice as an administrative exclusion.
assert.equal(context.cohortFacetOptions("courses").length, 2);
// The title filter operates on all historic activities grouped in an
// annuality. A matched title DOES NOT turn into a partial exclusion.
vm.runInContext("cohortReview.filters.assignments.add('Esterno');", context);
assert.equal(context.visibleCohortCandidates().length, 2);
assert.equal(context.visibleCohortCandidates()[0].course_code, "SYN01");
assert.equal(context.cohortFacetOptions("assignments").length, 3);
vm.runInContext("cohortReview.filters.assignments.clear();", context);
assert.equal(context.visibleCohortCandidates().length, 3);

// ANNO is a text filter: "1" and "1,2,3" are distinct source values.
vm.runInContext("cohortReview.filters.years.clear();", context);
vm.runInContext("cohortReview.data.source_year_filter_values = ['1','2','1,2,3'];", context);
vm.runInContext("cohortReview.data.cohorts[0].source_year_values = ['1,2,3'];", context);
vm.runInContext("cohortReview.data.cohorts[1].source_year_values = ['2'];", context);
vm.runInContext("cohortReview.data.cohorts[2].source_year_values = ['1'];", context);
assert.deepEqual(
  Array.from(context.cohortFacetOptions("years"), x => x.value),
  ["1", "1,2,3", "2"],
  "All literal source-year strings must be available, without merging"
);
vm.runInContext("cohortReview.filters.years.add('1,2,3');", context);
assert.equal(context.visibleCohortCandidates().length, 1);
assert.equal(context.visibleCohortCandidates()[0].course_code, "SYN01");
vm.runInContext("cohortReview.filters.years.clear();", context);
assert.equal(context.visibleCohortCandidates().length, 3);
console.log("DidaUP cohort checklist multiselect and draft-persistence tests: PASS");
