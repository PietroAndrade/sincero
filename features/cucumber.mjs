// cucumber-js: the business scenarios against @sincero/engine. From the repository root:
//
//   npm run features                          every scenario (npm test runs the support tests first)
//   npm run features -- --tags @more-cash     a slice
//   npm run feature -- credit_gap.feature     one file (paths relative to features/)
//   npm run report                            every scenario, written as an Allure report
//
// No `paths` here: cucumber ADDS command-line paths to the configured ones, so a default here
// could never be narrowed to one file. The scripts pass `*.feature` (the English files; pt_br/ is
// documentation, not run).
const common = {
  // support/register-typescript.mjs first: it lets the .ts files after it load, with no build step
  import: ["support/register-typescript.mjs", "support/**/*.ts", "steps/**/*.ts"],
  strict: true, // an undefined or pending step fails the run
};

export default { ...common, format: ["progress"] };

/** `cucumber-js --profile report`: Allure results, grouped by the features' @allure.label.* tags. */
export const report = {
  ...common,
  // The reporter writes allure-results/ itself; its stream goes to a file so progress keeps stdout.
  format: ["progress", "allure-cucumberjs/reporter:allure-results/.cucumber-formatter.log"],
  formatOptions: {
    resultsDir: "allure-results",
    labels: ["parentSuite", "suite", "subSuite"].map((name) => ({
      name,
      pattern: [new RegExp(`@allure\\.label\\.${name}:(.+)`)],
    })),
  },
};
