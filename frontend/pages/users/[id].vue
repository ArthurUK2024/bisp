<script setup lang="ts">
// pages/users/[id].vue
//
// Public read-only profile — PROF-03 + PROF-04. Uses useApi() (the
// unauthenticated dual-URL wrapper) so SSR fetches hit the Docker
// internal DNS name api:8000 and browser fetches hit the host port
// mapping at localhost:8000. No Bearer header is attached because
// the Django PublicProfileView sets authentication_classes = [] and
// queryset.filter(is_active=True) so a soft-deleted account is a 404
// by construction.

interface PublicProfile {
  id: number
  display_name: string
  bio: string
  avatar: string | null
  date_joined: string
}

const route = useRoute()
const api = useApi()

const { data: profile, error } = await useAsyncData<PublicProfile>(
  `public-profile-${route.params.id}`,
  () => api(`users/${route.params.id}/`),
)
</script>

<template>
  <main class="max-w-2xl mx-auto p-8 space-y-8">
    <template v-if="error">
      <h1 class="text-2xl font-semibold">User not found</h1>
      <p class="text-gray-600">There is no public profile at this address.</p>
    </template>

    <template v-else-if="profile">
      <section class="flex items-center gap-6">
        <UAvatar :src="profile.avatar ?? undefined" size="2xl" />
        <div class="space-y-1">
          <h1 class="text-2xl font-semibold">
            {{ profile.display_name || 'Ijara user' }}
          </h1>
          <p v-if="profile.bio" class="text-gray-700">{{ profile.bio }}</p>
        </div>
      </section>

      <section class="space-y-3">
        <h2 class="text-lg font-medium">Listings</h2>
        <div class="rounded border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          Listings will appear here in Phase 3.
        </div>
      </section>
    </template>
  </main>
</template>
