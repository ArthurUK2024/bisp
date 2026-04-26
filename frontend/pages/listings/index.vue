<script setup lang="ts">
// pages/listings/index.vue
// Public catalog browse with a search bar and filter set. Backed by
// TanStack Query so back-and-forth navigation between detail and
// browse does not refetch within the staleTime window.

import { useQuery } from '@tanstack/vue-query'
import { CATEGORIES, DISTRICTS, useListings } from '~/composables/useListings'

const route = useRoute()
const router = useRouter()

const category = ref((route.query.category as string) || '')
const district = ref((route.query.district as string) || '')
const query = ref((route.query.q as string) || '')
const unit = ref((route.query.unit as string) || '')
const minPrice = ref((route.query.min_price as string) || '')
const maxPrice = ref((route.query.max_price as string) || '')

// Debounce keystrokes so we don't fire a request per character.
const debouncedQuery = ref(query.value)
let queryTimer: ReturnType<typeof setTimeout> | null = null
watch(query, (q) => {
  if (queryTimer) clearTimeout(queryTimer)
  queryTimer = setTimeout(() => {
    debouncedQuery.value = q
  }, 400)
})

const { fetchListings } = useListings()

const filters = computed(() => ({
  category: category.value || undefined,
  district: district.value || undefined,
  q: debouncedQuery.value || undefined,
  unit: unit.value || undefined,
  min_price: minPrice.value || undefined,
  max_price: maxPrice.value || undefined,
}))

// TanStack Query keyed on the filter object so each unique filter
// combination caches separately. Within staleTime (30s), going back
// to a previous filter combination is a memory hit, no network call.
const { data: listings } = useQuery({
  queryKey: ['listings', filters],
  queryFn: () => fetchListings(filters.value),
})

watch([category, district, debouncedQuery, unit, minPrice, maxPrice], ([c, d, q, u, lo, hi]) => {
  router.replace({
    query: {
      ...(c && { category: c }),
      ...(d && { district: d }),
      ...(q && { q }),
      ...(u && { unit: u }),
      ...(lo && { min_price: lo }),
      ...(hi && { max_price: hi }),
    },
  })
})

function clearFilters() {
  category.value = ''
  district.value = ''
  query.value = ''
  unit.value = ''
  minPrice.value = ''
  maxPrice.value = ''
}

const activeFilterCount = computed(() => {
  return (
    (category.value ? 1 : 0) +
    (district.value ? 1 : 0) +
    (query.value ? 1 : 0) +
    (unit.value ? 1 : 0) +
    (minPrice.value ? 1 : 0) +
    (maxPrice.value ? 1 : 0)
  )
})

function firstPrice(item: any): { amount: string; unit: string } | null {
  if (item.price_hour) return { amount: item.price_hour, unit: 'hour' }
  if (item.price_day) return { amount: item.price_day, unit: 'day' }
  if (item.price_month) return { amount: item.price_month, unit: 'month' }
  return null
}

function priceLabel(item: any): string {
  const p = firstPrice(item)
  if (!p) return '—'
  return `UZS ${Number(p.amount).toLocaleString('en-US')} / ${p.unit}`
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
  <main class="max-w-6xl mx-auto px-6 py-10 space-y-8">
    <!-- Header row -->
    <header class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-3xl font-semibold tracking-tight">Rentals in Tashkent</h1>
        <p class="text-sm text-gray-600 mt-1">
          Browse what the neighbourhood is renting out today.
        </p>
      </div>
      <NuxtLink
        to="/dashboard/listings/new"
        class="rounded-md bg-slate-900 text-white text-sm px-4 py-2 hover:bg-slate-800 transition"
      >
        List an item
      </NuxtLink>
    </header>

    <!-- Filter bar -->
    <section
      class="rounded-xl border border-gray-200 bg-white p-3 flex flex-col md:flex-row gap-2 md:items-center"
    >
      <!-- Search -->
      <div class="relative flex-1 min-w-[220px]">
        <svg
          class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          v-model="query"
          type="search"
          placeholder="Search drills, cameras, tents..."
          class="w-full rounded-md border border-gray-200 bg-gray-50 pl-9 pr-3 py-2 text-sm placeholder:text-gray-400 focus:bg-white focus:border-slate-900 focus:outline-none"
        />
      </div>

      <!-- Category -->
      <div class="relative md:w-44">
        <select
          v-model="category"
          class="appearance-none w-full rounded-md border border-gray-200 bg-white pl-3 pr-9 py-2 text-sm text-gray-800 focus:border-slate-900 focus:outline-none cursor-pointer"
        >
          <option value="">All categories</option>
          <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">
            {{ c.label }}
          </option>
        </select>
        <svg
          class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>

      <!-- District -->
      <div class="relative md:w-44">
        <select
          v-model="district"
          class="appearance-none w-full rounded-md border border-gray-200 bg-white pl-3 pr-9 py-2 text-sm text-gray-800 focus:border-slate-900 focus:outline-none cursor-pointer"
        >
          <option value="">Every district</option>
          <option v-for="d in DISTRICTS" :key="d.value" :value="d.value">
            {{ d.label }}
          </option>
        </select>
        <svg
          class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>

      <!-- Unit -->
      <div class="relative md:w-32">
        <select
          v-model="unit"
          class="appearance-none w-full rounded-md border border-gray-200 bg-white pl-3 pr-9 py-2 text-sm text-gray-800 focus:border-slate-900 focus:outline-none cursor-pointer"
        >
          <option value="">Any unit</option>
          <option value="hour">Per hour</option>
          <option value="day">Per day</option>
          <option value="month">Per month</option>
        </select>
        <svg
          class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>

      <!-- Price min / max -->
      <input
        v-model="minPrice"
        type="number"
        min="0"
        placeholder="Min UZS"
        class="md:w-28 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
      />
      <input
        v-model="maxPrice"
        type="number"
        min="0"
        placeholder="Max UZS"
        class="md:w-28 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
      />

      <!-- Clear -->
      <button
        v-if="activeFilterCount > 0"
        type="button"
        class="text-sm text-gray-500 hover:text-gray-900 px-2"
        @click="clearFilters"
      >
        Clear
      </button>
    </section>

    <!-- Results summary -->
    <p class="text-sm text-gray-500 -mt-4">
      {{ listings?.length ?? 0 }} result{{ (listings?.length ?? 0) === 1 ? '' : 's' }}
      <span v-if="activeFilterCount">
        · {{ activeFilterCount }} filter{{ activeFilterCount === 1 ? '' : 's' }} active</span
      >
    </p>

    <!-- Grid -->
    <section
      v-if="listings && listings.length > 0"
      class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      <NuxtLink
        v-for="item in listings"
        :key="item.id"
        :to="`/listings/${item.id}`"
        class="group rounded-lg border border-gray-200 overflow-hidden bg-white hover:shadow-md transition-shadow"
      >
        <div class="aspect-[4/3] bg-gray-100 flex items-center justify-center overflow-hidden">
          <img
            v-if="firstPhoto(item)"
            :src="firstPhoto(item)!"
            :alt="item.title"
            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
          <span v-else class="text-gray-400 text-sm">No photo yet</span>
        </div>
        <div class="p-3 space-y-1">
          <div class="flex justify-between items-start gap-2">
            <h2 class="font-medium line-clamp-1">{{ item.title }}</h2>
            <span class="text-sm font-semibold whitespace-nowrap">{{ priceLabel(item) }}</span>
          </div>
          <p class="text-xs text-gray-600">
            {{ categoryLabel(item.category) }} · {{ districtLabel(item.district) }}
          </p>
          <p class="text-xs text-gray-500">by {{ item.owner_display_name || 'Ijara user' }}</p>
        </div>
      </NuxtLink>
    </section>

    <section
      v-else
      class="rounded-lg border border-dashed border-gray-300 p-10 text-center text-gray-500"
    >
      <p class="font-medium text-gray-700">No listings match yet.</p>
      <p class="text-sm">Try a different filter or search term.</p>
      <button
        v-if="activeFilterCount"
        type="button"
        class="mt-4 rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-white"
        @click="clearFilters"
      >
        Clear filters
      </button>
    </section>
  </main>
</template>
