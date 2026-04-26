<script setup lang="ts">
// pages/index.vue
// Landing page for Ijara -- hero, category shortcuts, latest listings
// feed, and a three-step "how it works" section.

import { CATEGORIES, DISTRICTS, useListings } from '~/composables/useListings'

const { fetchListings } = useListings()

const { data: listings } = await useAsyncData('latest-listings', () => fetchListings())

const featured = computed(() => (listings.value ?? []).slice(0, 8))

const stats = computed(() => {
  const all = listings.value ?? []
  const categories = new Set(all.map((l) => l.category)).size
  const districts = new Set(all.map((l) => l.district)).size
  return {
    items: all.length,
    categories,
    districts,
  }
})

const categoryIcons: Record<string, string> = {
  tools: '🔧',
  electronics: '📷',
  event_gear: '🎪',
  sports: '⛷️',
  furniture: '🪑',
  vehicles: '🚗',
  other: '📦',
}

function firstPhoto(item: any): string | null {
  return item.photos?.[0]?.image ?? null
}

function priceLabel(item: any): string {
  if (item.price_day) return `UZS ${Number(item.price_day).toLocaleString('en-US')} / day`
  if (item.price_hour) return `UZS ${Number(item.price_hour).toLocaleString('en-US')} / hour`
  if (item.price_month) return `UZS ${Number(item.price_month).toLocaleString('en-US')} / mo`
  return '—'
}

function categoryLabel(value: string): string {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value
}

function districtLabel(value: string): string {
  return DISTRICTS.find((d) => d.value === value)?.label ?? value
}
</script>

<template>
  <div class="flex flex-col">
    <!-- Hero ------------------------------------------------------------->
    <section
      class="relative bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white"
    >
      <div class="max-w-6xl mx-auto px-6 py-20 md:py-28 relative z-10">
        <div class="max-w-2xl space-y-6">
          <p class="text-sm tracking-[0.2em] uppercase text-slate-300">
            Tashkent · Peer-to-peer rentals
          </p>
          <h1 class="text-4xl md:text-6xl font-semibold tracking-tight leading-tight">
            Rent anything,<br />from anyone,<br />
            <span class="text-amber-300">right in your district.</span>
          </h1>
          <p class="text-lg text-slate-300 max-w-xl">
            A drill for the weekend. A drone for your wedding. A Niva for the mountains. Find it in
            Tashkent, book it for the days you need, collect it the same afternoon.
          </p>
          <div class="flex flex-wrap gap-3 pt-2">
            <NuxtLink
              to="/listings"
              class="rounded-md bg-amber-300 text-slate-900 px-5 py-3 font-medium hover:bg-amber-200"
            >
              Browse {{ stats.items }} rentals
            </NuxtLink>
            <NuxtLink
              to="/dashboard/listings/new"
              class="rounded-md border border-white/30 px-5 py-3 font-medium hover:bg-white/10"
            >
              List your item
            </NuxtLink>
          </div>
          <dl class="flex gap-8 pt-6 text-sm text-slate-300">
            <div>
              <dt class="text-xs uppercase tracking-wider text-slate-400">Items</dt>
              <dd class="text-xl font-semibold text-white">{{ stats.items }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wider text-slate-400">Categories</dt>
              <dd class="text-xl font-semibold text-white">{{ stats.categories }}</dd>
            </div>
            <div>
              <dt class="text-xs uppercase tracking-wider text-slate-400">Districts</dt>
              <dd class="text-xl font-semibold text-white">{{ stats.districts }}</dd>
            </div>
          </dl>
        </div>
      </div>
      <div
        class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,theme(colors.amber.500/20),transparent_60%)]"
      />
    </section>

    <!-- Category tiles ---------------------------------------------------->
    <section class="max-w-6xl mx-auto px-6 py-14 w-full">
      <h2 class="text-2xl font-semibold mb-6">Browse by category</h2>
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <NuxtLink
          v-for="c in CATEGORIES"
          :key="c.value"
          :to="`/listings?category=${c.value}`"
          class="group rounded-lg border border-gray-200 bg-white p-4 hover:border-slate-900 hover:shadow-md transition"
        >
          <div class="text-3xl mb-2">{{ categoryIcons[c.value] ?? '📦' }}</div>
          <p class="text-sm font-medium group-hover:text-slate-900">{{ c.label }}</p>
        </NuxtLink>
      </div>
    </section>

    <!-- Latest listings ---------------------------------------------------->
    <section class="bg-slate-50 border-y border-gray-200">
      <div class="max-w-6xl mx-auto px-6 py-14 w-full space-y-6">
        <header class="flex items-end justify-between gap-3">
          <div>
            <h2 class="text-2xl font-semibold">Latest rentals</h2>
            <p class="text-sm text-gray-600">
              Fresh listings from your neighbours across Tashkent.
            </p>
          </div>
          <NuxtLink to="/listings" class="text-sm underline text-slate-700 hover:text-slate-900">
            See all {{ stats.items }} &rarr;
          </NuxtLink>
        </header>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <NuxtLink
            v-for="item in featured"
            :key="item.id"
            :to="`/listings/${item.id}`"
            class="group rounded-lg overflow-hidden bg-white border border-gray-200 hover:shadow-lg transition-shadow"
          >
            <div class="aspect-[4/3] bg-gray-100 overflow-hidden">
              <img
                v-if="firstPhoto(item)"
                :src="firstPhoto(item)!"
                :alt="item.title"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div
                v-else
                class="w-full h-full flex items-center justify-center text-gray-400 text-xs"
              >
                No photo yet
              </div>
            </div>
            <div class="p-3 space-y-1">
              <div class="flex justify-between items-start gap-2">
                <h3 class="text-sm font-medium line-clamp-1">{{ item.title }}</h3>
                <span class="text-sm font-semibold whitespace-nowrap">{{ priceLabel(item) }}</span>
              </div>
              <p class="text-xs text-gray-600">
                {{ categoryLabel(item.category) }} · {{ districtLabel(item.district) }}
              </p>
              <p class="text-xs text-gray-500">by {{ item.owner_display_name || 'Ijara user' }}</p>
            </div>
          </NuxtLink>
        </div>
      </div>
    </section>

    <!-- How it works ------------------------------------------------------->
    <section class="max-w-6xl mx-auto px-6 py-16 w-full">
      <h2 class="text-2xl font-semibold mb-8">How Ijara works</h2>
      <div class="grid md:grid-cols-3 gap-6">
        <div class="space-y-2">
          <div
            class="w-10 h-10 rounded-full bg-slate-900 text-white flex items-center justify-center text-sm font-semibold"
          >
            1
          </div>
          <h3 class="font-medium">Find what you need</h3>
          <p class="text-sm text-gray-600">
            Browse by category or district, or search by keyword. Every listing shows the daily
            price, the owner's profile, and photos straight from them.
          </p>
        </div>
        <div class="space-y-2">
          <div
            class="w-10 h-10 rounded-full bg-slate-900 text-white flex items-center justify-center text-sm font-semibold"
          >
            2
          </div>
          <h3 class="font-medium">Pick your dates</h3>
          <p class="text-sm text-gray-600">
            Choose a start and end date on the listing page. Ijara shows the total up front. Submit
            the request and the owner is notified.
          </p>
        </div>
        <div class="space-y-2">
          <div
            class="w-10 h-10 rounded-full bg-slate-900 text-white flex items-center justify-center text-sm font-semibold"
          >
            3
          </div>
          <h3 class="font-medium">Collect and return</h3>
          <p class="text-sm text-gray-600">
            Once the owner approves, you agree on pickup. Pay cash or card on collection. Return the
            item at the end of your booking window.
          </p>
        </div>
      </div>
    </section>

    <!-- Owner CTA ---------------------------------------------------------->
    <section class="bg-slate-900 text-white">
      <div
        class="max-w-6xl mx-auto px-6 py-14 flex flex-col md:flex-row items-start md:items-center justify-between gap-6"
      >
        <div class="max-w-lg space-y-2">
          <h2 class="text-2xl font-semibold">Got something sitting unused?</h2>
          <p class="text-slate-300">
            A drill you bought for one job. A camera you use twice a year. List it on Ijara in five
            minutes and let it earn its keep.
          </p>
        </div>
        <NuxtLink
          to="/dashboard/listings/new"
          class="rounded-md bg-amber-300 text-slate-900 px-5 py-3 font-medium hover:bg-amber-200"
        >
          Post your first listing
        </NuxtLink>
      </div>
    </section>

    <!-- Footer ------------------------------------------------------------->
    <footer class="border-t border-gray-200 bg-white">
      <div
        class="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-sm text-gray-500"
      >
        <p>&copy; 2026 Ijara. A final-year BSc project at WIUT Tashkent.</p>
        <nav class="flex gap-5">
          <NuxtLink to="/listings" class="hover:text-gray-900">Browse</NuxtLink>
          <NuxtLink to="/register" class="hover:text-gray-900">Register</NuxtLink>
          <NuxtLink to="/login" class="hover:text-gray-900">Sign in</NuxtLink>
        </nav>
      </div>
    </footer>
  </div>
</template>
