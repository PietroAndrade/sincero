// `npm run report`: every scenario through cucumber-js, written as an Allure 3 report in
// allure-report/ (open it with `npx allure open allure-report`). The report is generated even when
// scenarios fail, that is when it is most useful; the exit code is still cucumber's.
import { spawnSync } from "node:child_process";
import fs from "node:fs";

const run = (args) => spawnSync("npx", args, { stdio: "inherit", shell: process.platform === "win32" }).status ?? 1;

// This run only: old results would be merged in, and Allure 3 leaves files of an older report
// (summary.json) in place when it writes into an existing folder.
for (const dir of ["allure-results", "allure-report"]) fs.rmSync(dir, { recursive: true, force: true });
const cucumber = run(["cucumber-js", "--profile", "report", "*.feature"]);
const allure = run(["allure", "generate", "-c", ".allurerc.mjs", "allure-results"]);
if (allure === 0) console.log("Allure report: features/allure-report/index.html (npx allure open allure-report)");
process.exit(cucumber || allure);
