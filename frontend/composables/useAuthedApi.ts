// composables/useAuthedApi.ts
//
// Authenticated $fetch wrapper for browser-side calls. Every request
// goes through a same-origin Nitro route at /api/auth/*, which the
// BFF proxies to Django with the Bearer header attached. The Phase 1
// useApi() composable stays the unauthenticated dual-URL wrapper —
// this composable is the Phase 2+ layer on top of it.
//
// Silent refresh on 401: if a response comes back 401, the composable
// calls /api/auth/refresh once, swaps the new access token into the
// Pinia store, and retries the original request. A second 401 drops
// the store state and routes the user to /login.
//
// The `options as never` cast on the retry is the documented ofetch
// typing escape hatch — the retry signature is narrower than the
// initial call and the generics do not line up without the cast.

export const useAuthedApi = () => {
  const auth = useAuthStore()

  return $fetch.create({
    baseURL: '/api/auth/',

    onRequest({ options }) {
      if (auth.accessToken) {
        options.headers = {
          ...(options.headers || {}),
          Authorization: `Bearer ${auth.accessToken}`,
        }
      }
    },

    async onResponseError({ request, response, options }) {
      if (response.status !== 401) {
        return
      }
      // Single silent-refresh retry.
      try {
        const { access } = await $fetch<{ access: string }>('/api/auth/refresh', { method: 'POST' })
        auth.accessToken = access
        options.headers = {
          ...(options.headers || {}),
          Authorization: `Bearer ${access}`,
        }
        // Retry the original request once with the new token.
        return await $fetch(request, options as never)
      } catch {
        auth.user = null
        auth.accessToken = null
        // Preserve the originally-requested path so the login page can
        // bring the user back after a successful login.
        const route = useRoute()
        const next =
          route.fullPath && route.fullPath !== '/login'
            ? `?next=${encodeURIComponent(route.fullPath)}`
            : ''
        await navigateTo(`/login${next}`)
      }
    },
  })
}
