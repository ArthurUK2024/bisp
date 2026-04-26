// server/middleware/admin-redirect.ts
//
// Django serves the admin at port 8000, but users naturally type
// http://localhost:3000/admin/ since that's the front-end origin they
// already have open. This middleware bounces those requests over to the
// Django admin URL the browser can actually reach, preserving the full
// subpath so /admin/login/, /admin/bookings/booking/, etc. still work.
//
// The redirect target is the host-reachable Django origin, configured
// via NUXT_PUBLIC_DJANGO_HOST and falling back to http://localhost:8000
// for the default Docker Compose setup.

export default defineEventHandler((event) => {
  const url = getRequestURL(event)
  const isAdmin = url.pathname === '/admin' || url.pathname.startsWith('/admin/')
  if (!isAdmin) return

  const config = useRuntimeConfig()
  const djangoHost = (config.public.djangoHost as string) || 'http://localhost:8000'
  const target = `${djangoHost.replace(/\/$/, '')}${url.pathname}${url.search}`
  return sendRedirect(event, target, 302)
})
