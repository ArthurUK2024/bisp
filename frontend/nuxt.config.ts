// nuxt.config.ts
// https://nuxt.com/docs/api/configuration/nuxt-config

export default defineNuxtConfig({
  compatibilityDate: '2026-04-01',
  devtools: { enabled: true },

  modules: ['@nuxt/ui', '@nuxt/eslint', '@pinia/nuxt', '@vueuse/nuxt'],

  css: ['~/assets/css/main.css'],

  typescript: {
    strict: false, // per CONTEXT.md — future work, not Phase 1
  },

  runtimeConfig: {
    // Private — only available server-side (SSR, Nitro routes).
    // This is the URL the Nuxt server uses when running inside the Docker
    // network, where `api` resolves via Docker DNS. Do NOT point it at
    // http://localhost:8000 — inside the container, localhost is the
    // container itself.
    apiBaseServer: 'http://api:8000/api/v1/', // env: NUXT_API_BASE_SERVER

    public: {
      // Exposed to the browser after hydration. This URL is fetched from
      // the user's browser, so it must be a host-reachable URL. Do NOT
      // point it at http://api:8000 — `api` is not resolvable from the host.
      apiBase: 'http://localhost:8000/api/v1/', // env: NUXT_PUBLIC_API_BASE

      // Browser-reachable Django origin, used by the /admin redirect.
      djangoHost: 'http://localhost:8000', // env: NUXT_PUBLIC_DJANGO_HOST

      // Phase 6 — empty until Stripe lands.
      stripePublishableKey: '', // env: NUXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
    },
  },
})
