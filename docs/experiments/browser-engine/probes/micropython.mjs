// Probe: can MicroPython (PyScript's small runtime, ~540 KB) run the unchanged engine?
//   node probes/micropython.mjs
// It cannot: see the output. The three blockers are in the language, not in missing modules.
import { loadMicroPython } from "@micropython/micropython-webassembly-pyscript";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const backendApp = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../backend/app");
const mp = await loadMicroPython({ stdout: (s) => console.log(s) });
const copy = (dir, dest) => {
  mp.FS.mkdirTree(dest);
  for (const f of fs.readdirSync(dir)) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) { if (f !== "__pycache__") copy(p, `${dest}/${f}`); }
    else if (f.endsWith(".py")) mp.FS.writeFile(`${dest}/${f}`, fs.readFileSync(p, "utf8"));
  }
};
mp.FS.mkdirTree("/engine/app");
mp.FS.writeFile("/engine/app/__init__.py", "");
copy(`${backendApp}/models`, "/engine/app/models");
copy(`${backendApp}/views`, "/engine/app/views");

const run = (label, code) => {
  try { mp.runPython(code); } catch (e) { console.log(`${label}: FAILS -> ${String(e.message ?? e).trim().split("\n").pop()}`); }
};
run("version", "import sys; print('runtime:', sys.version)");
run("import the engine", "import sys; sys.path.insert(0, '/engine'); import app.models; print('import the engine: ok')");
for (const m of ["__future__", "typing", "dataclasses", "abc"]) run(`module ${m}`, `import ${m}; print('module ${m}: ok')`);
console.log("-- even with stub modules, the language differs:");
run("annotations", `
class A:
    x: int
    y: int = 3
print("class annotations (a dataclass needs them):", getattr(A, "__annotations__", "DROPPED"), "- fields left:", [k for k in dir(A) if not k.startswith("_")])`);
run("format", `print("f'{1234567.891:,.2f}' ->", "{:,.2f}".format(1234567.891), "(CPython: 1,234,567.89)")`);
run("sum", `print("sum([0.1] * 10) ->", sum([0.1] * 10), "(CPython >= 3.12: 1.0)")`);
