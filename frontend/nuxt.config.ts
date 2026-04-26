export default defineNuxtConfig({
  compatibilityDate: '2026-04-01',
  devtools: { enabled: true },

  modules: ['@nuxt/ui', '@nuxt/eslint', '@pinia/nuxt', '@vueuse/nuxt'],

  css: ['~/assets/css/main.css'],

  typescript: {
    strict: false,
  },

  runtimeConfig: {
    apiBaseServer: 'http://api:8000/api/v1/',

    public: {
      apiBase: 'http://localhost:8000/api/v1/',

      djangoHost: 'http://localhost:8000',

      stripePublishableKey: '',
    },
  },
})
