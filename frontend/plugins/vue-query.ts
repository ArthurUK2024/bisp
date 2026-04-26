// plugins/vue-query.ts
//
// SRCH-02 — TanStack Query for client-side caching of read-mostly
// queries (browse listings, listing detail, etc.). Stays small: the
// QueryClient is registered with Nuxt's Vue app and serialised between
// SSR and client via Nuxt's payload so the first hydrated render does
// not refetch.

import { VueQueryPlugin, QueryClient, hydrate, dehydrate } from '@tanstack/vue-query'

export default defineNuxtPlugin((nuxtApp) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
    },
  })

  nuxtApp.vueApp.use(VueQueryPlugin, { queryClient })

  if (import.meta.server) {
    nuxtApp.hooks.hook('app:rendered', () => {
      nuxtApp.payload.vueQueryState = dehydrate(queryClient)
    })
  }

  if (import.meta.client) {
    hydrate(queryClient, nuxtApp.payload.vueQueryState)
  }
})
