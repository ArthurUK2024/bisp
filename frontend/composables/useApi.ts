// composables/useApi.ts
/**
 * Dual-URL-aware $fetch wrapper. Picks the SSR base URL when running on the
 * Nitro server and the public base URL when running in the browser. Without
 * this split, SSR fetches would try http://localhost:8000 from inside the
 * api container (where localhost means "the container itself") and browser
 * fetches would try http://api:8000 (where api is not a DNS-resolvable name).
 *
 * This composable is the single consumer of runtimeConfig.apiBaseServer.
 * Every feature-level composable in Phase 2+ builds on top of this one.
 */
export const useApi = () => {
  const config = useRuntimeConfig()
  const baseURL = import.meta.server ? config.apiBaseServer : config.public.apiBase
  return $fetch.create({ baseURL })
}
