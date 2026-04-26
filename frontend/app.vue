<script setup lang="ts">
const auth = useAuthStore()

async function handleLogout() {
  await auth.logout()
  await navigateTo('/login')
}
</script>

<template>
  <UApp>
    <div class="min-h-screen flex flex-col">
      <header class="border-b border-gray-200 bg-white">
        <div class="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <NuxtLink to="/" class="text-xl font-semibold tracking-tight"> Ijara </NuxtLink>
          <nav class="flex items-center gap-4 text-sm">
            <NuxtLink to="/listings" class="hover:underline">Browse</NuxtLink>
            <ClientOnly>
              <template v-if="auth.isAuthed">
                <NuxtLink to="/dashboard/listings" class="hover:underline">My listings</NuxtLink>
                <NuxtLink to="/dashboard/bookings" class="hover:underline">Bookings</NuxtLink>
                <NuxtLink to="/dashboard/analytics" class="hover:underline">Analytics</NuxtLink>
                <NuxtLink to="/dashboard/profile" class="hover:underline">Profile</NuxtLink>
                <a v-if="auth.user?.is_staff" href="/admin/" class="hover:underline text-purple-700"
                  >Admin</a
                >
                <UButton variant="ghost" size="sm" @click="handleLogout">Log out</UButton>
              </template>
              <template v-else>
                <NuxtLink to="/login" class="hover:underline">Sign in</NuxtLink>
                <NuxtLink to="/register" class="hover:underline">Register</NuxtLink>
              </template>
            </ClientOnly>
          </nav>
        </div>
      </header>

      <NuxtPage />
    </div>
  </UApp>
</template>
