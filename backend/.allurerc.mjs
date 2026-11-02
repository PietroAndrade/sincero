export default {
  name: "SINCERO — business scenarios",
  output: "./allure-report",
  plugins: {
    awesome: {
      options: {
        groupBy: ["parentSuite", "suite", "subSuite"],
      },
    },
  },
};
