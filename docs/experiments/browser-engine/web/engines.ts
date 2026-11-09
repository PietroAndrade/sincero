/**
 * One interface, three ways to run the SINCERO engine inside the browser:
 *
 *   ts        the TypeScript port (engine-ts/), bundled into app.js
 *   pyodide   the unchanged Python engine on CPython compiled to WebAssembly
 *   brython   the unchanged Python engine on Brython (Python translated to JavaScript at runtime)
 *
 * Every engine answers `callJson(kind, requestJson)` with the JSON string of a `Reply`, so the UI,
 * the benchmark and the behave gateway (harness/) treat them alike.
 */
import { InputShapeError, SimulationError, cashLadderDict, compareDicts, simulateDict } from "../engine-ts/index.js";

export type Kind = "simulate" | "compare" | "cash_ladder";

export type Reply =
  | { ok: true; value: unknown }
  | { ok: false; kind: "rejected" | "invalid_shape"; error: string };

export interface Engine {
  readonly name: EngineName;
  readonly label: string;
  load(): Promise<void>;
  callJson(kind: Kind, requestJson: string): string;
}

export type EngineName = "ts" | "pyodide" | "brython";

const BASE = new URL(".", location.href).href;

// ----- TypeScript ---------------------------------------------------------------------------------
class TypeScriptEngine implements Engine {
  readonly name = "ts";
  readonly label = "TypeScript port";
  async load(): Promise<void> {}
  callJson(kind: Kind, requestJson: string): string {
    const request = JSON.parse(requestJson);
    try {
      const value =
        kind === "simulate"
          ? simulateDict(request.input)
          : kind === "compare"
            ? compareDicts(request.inputs)
            : cashLadderDict(request.input, request.amounts);
      return JSON.stringify({ ok: true, value });
    } catch (exc) {
      if (exc instanceof SimulationError) return JSON.stringify({ ok: false, kind: "rejected", error: exc.message });
      if (exc instanceof InputShapeError) return JSON.stringify({ ok: false, kind: "invalid_shape", error: exc.message });
      throw exc;
    }
  }
}

// ----- Python: the engine's sources as built by build.mjs (py/engine.json: path -> source) ---------
async function engineSources(): Promise<Record<string, string>> {
  const response = await fetch(`${BASE}py/engine.json`);
  if (!response.ok) throw new Error(`py/engine.json: HTTP ${response.status}`);
  return response.json();
}

// ----- Pyodide ------------------------------------------------------------------------------------
interface PyodideLike {
  FS: { mkdirTree(path: string): void; writeFile(path: string, data: string): void };
  runPython(code: string): unknown;
  globals: { get(name: string): (kind: string, json: string) => string };
}

class PyodideEngine implements Engine {
  readonly name = "pyodide";
  readonly label = "Python (Pyodide, WebAssembly)";
  private call?: (kind: string, json: string) => string;

  async load(): Promise<void> {
    const [module, sources] = await Promise.all([
      import(/* @vite-ignore */ `${BASE}pyodide/pyodide.mjs`) as Promise<{ loadPyodide(o: object): Promise<PyodideLike> }>,
      engineSources(),
    ]);
    const py = await module.loadPyodide({ indexURL: `${BASE}pyodide/` });
    for (const [path, source] of Object.entries(sources)) {
      py.FS.mkdirTree(`/engine/${path.split("/").slice(0, -1).join("/")}`);
      py.FS.writeFile(`/engine/${path}`, source);
    }
    py.runPython("import sys; sys.path.insert(0, '/engine'); from sincero_bridge import call");
    this.call = py.globals.get("call");
  }

  callJson(kind: Kind, requestJson: string): string {
    return this.call!(kind, requestJson);
  }
}

// ----- Brython ------------------------------------------------------------------------------------
declare global {
  interface Window {
    brython?: (options?: object) => void;
    __BRYTHON__?: { runPythonSource(src: string, options?: object): unknown };
    sinceroBrythonCall?: (kind: string, json: string) => string;
  }
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`cannot load ${src}`));
    document.head.append(s);
  });
}

class BrythonEngine implements Engine {
  readonly name = "brython";
  readonly label = "Python (Brython, translated to JavaScript)";

  async load(): Promise<void> {
    await loadScript(`${BASE}brython/brython.min.js`);
    await loadScript(`${BASE}brython/brython_stdlib.js`);
    window.brython!({ debug: 0, pythonpath: [`${BASE}py/`] });
    // Brython imports `app.models…` from py/ with synchronous requests, like a file system.
    window.__BRYTHON__!.runPythonSource(
      "from browser import window\nfrom sincero_bridge import call\nwindow.sinceroBrythonCall = call\n",
      { pythonpath: [`${BASE}py/`] },
    );
    if (!window.sinceroBrythonCall) throw new Error("Brython did not load the bridge");
  }

  callJson(kind: Kind, requestJson: string): string {
    return window.sinceroBrythonCall!(kind, requestJson);
  }
}

export const ENGINES: Record<EngineName, () => Engine> = {
  ts: () => new TypeScriptEngine(),
  pyodide: () => new PyodideEngine(),
  brython: () => new BrythonEngine(),
};
