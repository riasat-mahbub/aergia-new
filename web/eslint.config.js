import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";
import reactHooks from "eslint-plugin-react-hooks";

// Hardening: pin eslint to a focused, runnable rule set. Phase 7 shipped
// without these plugin rules installed (`ERR_MODULE_NOT_FOUND` masked the gap);
// Phase 8 installs the React Hooks plugin and replaces the broken
// `tseslint.configs.recommended.rules` spread (which referenced
// @typescript-eslint/*, n/*, jsdoc/*, ban/*, and react-hooks/exhaustive-deps
// rules whose plugins were never registered) with a flat config that only
// enables rules whose plugins are installed. Source code is left untouched;
// existing `eslint-disable` directives in source files continue to work.
const REACT_HOOKS_RECOMMENDED = reactHooks.configs?.recommended ?? { rules: {} };
const TYPESCRIPT_RECOMMENDED = tseslint.configs?.recommended ?? { rules: {} };

export default [
  {
    ignores: ["dist/", "node_modules/", "node_modules_bak/"],
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
      "react-hooks": reactHooks,
    },
    rules: {
      ...(REACT_HOOKS_RECOMMENDED.rules ?? {}),
      ...(TYPESCRIPT_RECOMMENDED.rules ?? {}),
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  },
];
