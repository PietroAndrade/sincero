import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    // The golden master runs ~430 whole simulations (1.8 M figures): give it room on a slow CI box.
    testTimeout: 60_000,
  },
});
