// plugins/auth.client.ts
//
// Client-only Nuxt plugin (the .client suffix keeps it out of the SSR
// path). Runs once on app mount in the browser. Calls authStore.init()
// which performs the silent-refresh swap — if the browser holds a valid
// HttpOnly refresh cookie issued by the BFF, a new access token lands
// in memory and the user appears logged in across a hard page refresh.
// If not, init() stays silent and the app boots into a logged-out
// shell. This plugin is the entry point for the AUTH-03 "session
// survives browser refresh" contract.

export default defineNuxtPlugin(async () => {
  const auth = useAuthStore()
  await auth.init()
})
