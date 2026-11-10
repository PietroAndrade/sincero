#!/usr/bin/env node
// `npx sincero --help`: the SINCERO command line. The CLI and the engine are TypeScript, run by tsx
// with no build step (as the scenarios are).
import { register } from "tsx/esm/api";

register();
const { main } = await import("../src/main.ts");
process.exitCode = main(process.argv.slice(2), {
  out: (text) => process.stdout.write(text),
  err: (text) => process.stderr.write(text),
});
