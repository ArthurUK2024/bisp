// vitest.unit.config.ts
//
// Minimal, plain vitest config for tests that do NOT need the Nuxt
// runtime environment — Zod schemas, the Pinia store (mocked $fetch),
// and the BFF proxy utilities. These tests import source files directly
// via a relative path and run in a pure node environment, so they do not
// depend on happy-dom or @vue/test-utils (neither of which is currently
// installed — see 02-01 Wave 0 dep set).
//
// The main `vitest.config.ts` (which wraps `defineVitestConfig` from
// `@nuxt/test-utils/config`) remains the config for any Nuxt-env tests
// that land later in Phase 2+. Run pure units via:
//
//   npx vitest run --config vitest.unit.config.ts
//
// The default `npx vitest run` still picks up `vitest.config.ts`.

import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/unit/**/*.test.ts', 'server/**/__tests__/*.test.ts'],
    passWithNoTests: true,
  },
})
