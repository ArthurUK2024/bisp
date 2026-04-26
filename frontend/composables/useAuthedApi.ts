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
      try {
        const { access } = await $fetch<{ access: string }>('/api/auth/refresh', { method: 'POST' })
        auth.accessToken = access
        options.headers = {
          ...(options.headers || {}),
          Authorization: `Bearer ${access}`,
        }
        return await $fetch(request, options as never)
      } catch {
        auth.user = null
        auth.accessToken = null
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
