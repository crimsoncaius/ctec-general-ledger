import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "playwright-report", "test-results", "coverage", "../artifacts"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    },
  },
  {
    files: ["e2e/**/*.{ts,mjs}"],
    languageOptions: { globals: { ...globals.node } },
    rules: {
      "no-empty-pattern": "off",
      "react-hooks/rules-of-hooks": "off",
    },
  },
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
);
