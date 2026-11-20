"use strict";
/**
 * Static checks for the OneDrive synthetic prototype. These cannot replace
 * execution inside the tenant's Excel for the Web environment.
 */
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

const root = path.join(__dirname, "..", "prototypes", "office_scripts");
const initialize = fs.readFileSync(path.join(root, "prepara_protezione.ts"), "utf8");
const addRow = fs.readFileSync(path.join(root, "aggiungi_variazione.ts"), "utf8");

assert.match(initialize, /getRange\("G7:J1000"\)/);
assert.match(initialize, /setLocked\(false\)/);
assert.match(initialize, /getRange\("A1:M1000"\)/);
assert.match(initialize, /setLocked\(true\)/);
assert.match(initialize, /guard\.protect\(/);
assert.match(addRow, /getSelectedRange\(\)/);
assert.match(addRow, /getIsPasswordProtected\(\)/);
assert.match(addRow, /getRangeByIndexes\(insertIndex, 0, 1, WIDTH\)/);
assert.match(addRow, /\.insert\(ExcelScript\.InsertShiftDirection\.down\)/);
assert.match(addRow, /getRangeByIndexes\(insertIndex, 6, 1, 4\)\.setValues/);
assert.match(addRow, /"VARIAZIONE"/);
assert.match(addRow, /DIDAUP-VAR-/);
assert.match(addRow, /protection\.protect\(options\)/);
// The prototype intentionally has no hardcoded password and no network I/O.
assert.doesNotMatch(addRow + initialize, /\.protect\([^)]*,\s*["']/);
assert.doesNotMatch(addRow + initialize, /fetch\s*\(|XMLHttpRequest|localStorage/);
console.log("DidaUP Office Scripts prototype checks: PASS");
