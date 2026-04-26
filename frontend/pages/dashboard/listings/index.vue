<script setup lang="ts">
import { useListings, CATEGORIES, DISTRICTS } from '~/composables/useListings'

definePageMeta({
  middleware: ['auth'],
})

const { fetchMyListings, deleteListing } = useListings()
const toast = useToast()

const listings = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    listings.value = await fetchMyListings()
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function onDelete(id: number) {
  if (!confirm('Delete this listing? It will stop showing up in browse.')) return
  try {
    await deleteListing(id)
    toast.add({ title: 'Listing deleted.' })
    await load()
  } catch {
    toast.add({ title: 'Could not delete the listing.', color: 'error' })
  }
}

function firstPhoto(item: any): string | null {
  return item.photos?.[0]?.image ?? null
}

function categoryLabel(value: string): string {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value
}

function districtLabel(value: string): string {
  return DISTRICTS.find((d) => d.value === value)?.label ?? value
}
</script>

<template>
  <main class="max-w-4xl mx-auto p-8 space-y-6">
    <header class="flex justify-between items-end gap-3">
      <div>
        <h1 class="text-2xl font-semibold">My listings</h1>
        <p class="text-sm text-gray-600">Everything you have posted, active or removed.</p>
      </div>
      <NuxtLink
        to="/dashboard/listings/new"
        class="rounded-md bg-primary text-inverted text-sm px-3 py-2 hover:bg-primary/75"
      >
        + New listing
      </NuxtLink>
    </header>

    <ul v-if="listings.length" class="space-y-3">
      <li
        v-for="item in listings"
        :key="item.id"
        class="flex gap-4 rounded-md border border-gray-200 p-3"
      >
        <div
          class="w-24 h-24 rounded bg-gray-100 overflow-hidden flex items-center justify-center shrink-0"
        >
          <img
            v-if="firstPhoto(item)"
            :src="firstPhoto(item)!"
            class="w-full h-full object-cover"
          />
          <span v-else class="text-xs text-gray-400">No photo</span>
        </div>
        <div class="grow min-w-0 space-y-1">
          <div class="flex items-start justify-between gap-2">
            <NuxtLink :to="`/listings/${item.id}`" class="font-medium hover:underline">
              {{ item.title }}
            </NuxtLink>
            <UBadge :color="item.is_active ? 'success' : 'neutral'" variant="soft" size="sm">
              {{ item.is_active ? 'active' : 'removed' }}
            </UBadge>
          </div>
          <p class="text-xs text-gray-600">
            {{ categoryLabel(item.category) }} · {{ districtLabel(item.district) }}
          </p>
          <p class="text-xs text-gray-500 line-clamp-1">{{ item.description }}</p>
          <div class="flex gap-2 pt-1">
            <UButton
              v-if="item.is_active"
              size="xs"
              variant="soft"
              :to="`/dashboard/listings/${item.id}/edit`"
            >
              Edit
            </UButton>
            <UButton
              v-if="item.is_active"
              size="xs"
              variant="soft"
              color="error"
              @click="onDelete(item.id)"
            >
              Remove
            </UButton>
          </div>
        </div>
      </li>
    </ul>

    <div
      v-else-if="!loading"
      class="rounded-md border border-dashed border-gray-300 p-10 text-center text-sm text-gray-500"
    >
      <p>You have not posted anything yet.</p>
      <NuxtLink to="/dashboard/listings/new" class="underline text-sm mt-3 inline-block">
        Post your first listing
      </NuxtLink>
    </div>
  </main>
</template>
