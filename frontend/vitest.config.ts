import { defineVitestConfig } from '@nuxt/test-utils/config'

export default defineVitestConfig({
  test: {
    environment: 'nuxt',
    passWithNoTests: true,
    include: ['tests/unit/**/*.test.ts', 'server/**/__tests__/*.test.ts'],
  },
})
