export default defineEventHandler((event) => {
  const url = getRequestURL(event)
  const isAdmin = url.pathname === '/admin' || url.pathname.startsWith('/admin/')
  if (!isAdmin) return

  const config = useRuntimeConfig()
  const djangoHost = (config.public.djangoHost as string) || 'http://localhost:8000'
  const target = `${djangoHost.replace(/\/$/, '')}${url.pathname}${url.search}`
  return sendRedirect(event, target, 302)
})
