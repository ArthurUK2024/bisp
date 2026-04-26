export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return

  const auth = useAuthStore()

  if (auth.isAuthed) return

  if (!auth._initTried) {
    await auth.init()
  }

  if (auth.isAuthed) return

  return navigateTo(`/login?next=${encodeURIComponent(to.fullPath)}`)
})
