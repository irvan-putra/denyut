"use strict";
const $ = id => document.getElementById(id), KEY = "denyut.web.v1";
const FILES = ["denyut/__init__.py", "denyut/behavior.py", "denyut/core.py", "denyut/models.py", "denyut/skills/__init__.py", "denyut/skills/notes.py", "denyut/skills/reminders.py"];
let py = null, timer = null;
function add(cls, txt) { const d = document.createElement("div"); d.className = "m " + cls; d.textContent = txt; $("log").appendChild(d); $("log").scrollTop = 1e9; }
const store = () => JSON.parse(localStorage.getItem(KEY) || "{}");
function save(k, v) { const s = store(); s[k] = v; localStorage.setItem(KEY, JSON.stringify(s)); }
function persist() { for (const f of ["notes.json", "reminders.json"]) { try { save(f, py.FS.readFile("/data/" + f, {encoding: "utf8"})); } catch (e) {} } }
async function boot() {
  py = await loadPyodide({indexURL: new URL("pyodide/", location.href).href});
  py.FS.mkdirTree("/app/denyut/skills"); py.FS.mkdirTree("/data");
  for (const f of FILES) py.FS.writeFile("/app/" + f, await (await fetch("py/" + f)).text());
  const def = await (await fetch("py/behavior.json")).text();
  window.__defaultBehavior = def;
  const s = store();
  py.FS.writeFile("/data/behavior.json", s["behavior.json"] || def);
  for (const f of ["notes.json", "reminders.json"]) if (s[f]) py.FS.writeFile("/data/" + f, s[f]);
  $("b").value = s["behavior.json"] || def;
  py.runPython(`
import sys; sys.path.insert(0, "/app")
from denyut.core import Assistant
import time
_a = None
def make():
    global _a
    _a = Assistant(behavior_path="/data/behavior.json", store_dir="/data")
    return _a.name
def handle(t): return _a.handle(t, sender="local")
def due(): return [t for (_s, t) in _a.due_reminders()]
`);
  start();
}
function start() {
  try { const name = py.globals.get("make")(); document.title = name + " in your browser"; $("st").textContent = "Ready. Assistant name: " + name + "."; $("t").disabled = false; $("s").disabled = false; }
  catch (e) { $("st").textContent = "behavior.json could not be loaded: " + String(e.message || e).split("\n").slice(-2)[0]; return; }
  if (!timer) timer = setInterval(tick, 3000);
}
function tick() { try { for (const t of py.globals.get("due")().toJs()) add("bot", "Reminder: " + t); persist(); } catch (e) {} }
$("f").onsubmit = e => {
  e.preventDefault(); const v = $("t").value.trim(); if (!v) return; $("t").value = ""; add("me", v);
  try { add("bot", py.globals.get("handle")(v)); } catch (err) { add("sys", "The assistant raised: " + String(err.message || err).split("\n").filter(Boolean).slice(-1)[0]); }
  persist();
};
$("apply").onclick = () => { try { JSON.parse($("b").value); } catch (e) { $("bs").textContent = "Not valid JSON: " + e.message; return; } py.FS.writeFile("/data/behavior.json", $("b").value); save("behavior.json", $("b").value); $("bs").textContent = "Applied."; start(); };
$("reset").onclick = () => { $("b").value = window.__defaultBehavior; $("apply").click(); };
$("exp").onclick = () => { persist(); const s = store(), o = {notes: s["notes.json"] ? JSON.parse(s["notes.json"]) : {}, reminders: s["reminders.json"] ? JSON.parse(s["reminders.json"]) : {}}; const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(o, null, 2)], {type: "application/json"})); a.download = "denyut-web-data.json"; a.click(); };
$("clr").onclick = () => { if (!confirm("Erase all notes and reminders stored in this browser?")) return; for (const f of ["notes.json", "reminders.json"]) { try { py.FS.unlink("/data/" + f); } catch (e) {} const s = store(); delete s[f]; localStorage.setItem(KEY, JSON.stringify(s)); } start(); add("sys", "Notes and reminders erased from this browser."); };
add("sys", "Try: /help, /note buy milk, /notes, /remind 1m stretch");
boot().catch(e => { $("st").textContent = "Could not start: " + e.message; });
