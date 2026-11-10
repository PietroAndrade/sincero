// Builds dist/: a static site with the three engines. `npm run build`, then `python3 harness/serve.py`.
//
//   dist/index.html, style.css, app.js    the UI + the TypeScript engine (esbuild bundle)
//   dist/pyodide/                         the Pyodide runtime (from node_modules/pyodide)
//   dist/brython/                         the Brython runtime (from node_modules/brython)
//   dist/py/                              the UNCHANGED Python engine, read at build time from the retired
//                                         backend/app/ (legacy/backend/app, or $SINCERO_PYTHON_BACKEND/app):
//                                         app/{__init__,models/*,views/*}.py + sincero_bridge.py, as files
//                                         (Brython imports them one by one) and as engine.json (Pyodide)
import { build } from "esbuild";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const dist = path.join(here, "dist");
// The Python engine left develop (docs/decisions/engine-in-the-browser.md): read it from legacy/backend,
// or from a worktree of the tag `python-engine-final` named by SINCERO_PYTHON_BACKEND.
const backendApp = path.resolve(process.env.SINCERO_PYTHON_BACKEND ?? path.resolve(here, "../../../legacy/backend"), "app");

fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });

// 1. UI + TypeScript engine
const result = await build({
  entryPoints: [path.join(here, "web/app.ts")],
  bundle: true,
  minify: true,
  format: "esm",
  target: "es2022",
  outfile: path.join(dist, "app.js"),
  metafile: true,
  logLevel: "warning",
});
for (const f of ["index.html", "style.css"]) fs.copyFileSync(path.join(here, "web", f), path.join(dist, f));

// 2. runtimes
const copy = (from, to, files) => {
  fs.mkdirSync(to, { recursive: true });
  for (const f of files) fs.copyFileSync(path.join(from, f), path.join(to, f));
};
copy(path.join(here, "node_modules/pyodide"), path.join(dist, "pyodide"),
  ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]);
copy(path.join(here, "node_modules/brython"), path.join(dist, "brython"), ["brython.min.js", "brython_stdlib.js"]);

// 3. the Python engine, unchanged (no controllers: they import connectrpc; no gen/)
const sources = {};
const addTree = (dir, rel) => {
  for (const f of fs.readdirSync(dir).sort()) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) continue;
    if (f.endsWith(".py")) sources[`${rel}/${f}`] = fs.readFileSync(p, "utf8");
  }
};
sources["app/__init__.py"] = fs.readFileSync(path.join(backendApp, "__init__.py"), "utf8");
addTree(path.join(backendApp, "models"), "app/models");
addTree(path.join(backendApp, "views"), "app/views");
sources["sincero_bridge.py"] = fs.readFileSync(path.join(here, "web/sincero_bridge.py"), "utf8");
for (const [rel, src] of Object.entries(sources)) {
  fs.mkdirSync(path.dirname(path.join(dist, "py", rel)), { recursive: true });
  fs.writeFileSync(path.join(dist, "py", rel), src);
}
fs.writeFileSync(path.join(dist, "py/engine.json"), JSON.stringify(sources));

// 4. sizes: how much of app.js is the engine port
const inputs = result.metafile.outputs[path.relative(process.cwd(), path.join(dist, "app.js"))]?.inputs
  ?? Object.values(result.metafile.outputs)[0].inputs;
const engineBytes = Object.entries(inputs).filter(([k]) => k.includes("engine/src")).reduce((s, [, v]) => s + v.bytesInOutput, 0);
const sizes = {
  "app.js": fs.statSync(path.join(dist, "app.js")).size,
  "app.js: engine part": engineBytes,
  "py/engine.json": fs.statSync(path.join(dist, "py/engine.json")).size,
  "python engine files": Object.keys(sources).length,
};
fs.writeFileSync(path.join(dist, "build-sizes.json"), JSON.stringify(sizes, null, 2));
console.log("built dist/", sizes);
