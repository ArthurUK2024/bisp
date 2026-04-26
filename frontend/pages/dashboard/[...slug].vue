<script setup lang="ts">
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
