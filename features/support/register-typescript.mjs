// Lets cucumber-js import the TypeScript support code and steps (and @sincero/engine, which ships
// TypeScript): tsx's programmatic API registers its hooks for every import after this one.
// Listed first in cucumber.mjs `import`. Not TypeScript itself, on purpose.
import { register } from "tsx/esm/api";

register();
