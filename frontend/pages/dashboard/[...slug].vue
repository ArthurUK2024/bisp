<script setup lang="ts">
// pages/dashboard/[...slug].vue
//
// Catch-all placeholder page for every /dashboard/** route. Exists
// for two reasons:
//
//   1. The auth route guard (middleware/auth.ts) only fires on page
//      components Nuxt actually mounts. Without a page file under
//      /dashboard/**, Nuxt renders a 404 *before* middleware runs,
//      so an unauthed deep-link to /dashboard/anything would never
//      be redirected to /login?next=... This catch-all gives the
//      guard a page to attach to, so the redirect contract behaves
//      in a real browser the same way the unit tests pin it.
//
//   2. 02-06 lands frontend/pages/dashboard/profile.vue, which is a
//      NAMED route and takes priority over this catch-all for that
//      exact path. Every other /dashboard/** URL (dashboard/anything,
//      dashboard/bookings, dashboard/settings, etc.) falls through
//      to this placeholder until the matching page ships.
//
// The placeholder is deliberately minimal — a sentence telling the
// signed-in user the section is still being built. 02-06 replaces
// the profile slot with a real page; later phases replace the
// bookings slot.

definePageMeta({
  middleware: ['auth'],
})
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] flex items-center justify-center p-8">
    <UCard class="w-full max-w-md text-center">
      <template #header>
        <h1 class="text-2xl font-semibold">Dashboard</h1>
      </template>
      <p class="text-sm text-gray-600">This section is still being built. Check back soon.</p>
    </UCard>
  </main>
</template>
