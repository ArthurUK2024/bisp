<script setup lang="ts">
// pages/dashboard/analytics.vue
//
// Owner analytics — opens with a one-sentence plain-English summary,
// then groups numbers into "Money" and "Activity" so the page can be
// scanned in 5 seconds. Zero-count rows in the state breakdown are
// hidden behind a "Show all" toggle so the live data is always front
// and centre.

import {
  BOOKING_STATE_LABELS,
  formatTashkent,
  useBookings,
  type BookingState,
  type OwnerAnalytics,
} from '~/composables/useBookings'
import { CATEGORIES, DISTRICTS } from '~/composables/useListings'

definePageMeta({
  middleware: ['auth'],
})

const { ownerAnalytics } = useBookings()

const data = ref<OwnerAnalytics | null>(null)
const loading = ref(true)
const errorMsg = ref<string | null>(null)

async function load() {
  loading.value = true
  errorMsg.value = null
  try {
    data.value = await ownerAnalytics()
  } catch {
    errorMsg.value = 'Could not load analytics.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function fmtUZS(amount: string | number): string {
  return Number(amount).toLocaleString('en-US')
}

function categoryLabel(v: string): string {
  return CATEGORIES.find((c) => c.value === v)?.label ?? v
}
function districtLabel(v: string): string {
  return DISTRICTS.find((d) => d.value === v)?.label ?? v
}

// Plain-English summary the user reads first.
const summary = computed(() => {
  if (!data.value) return ''
  const d = data.value
  if (d.bookings_total === 0) {
    return d.listings_active > 0
      ? `You have ${d.listings_active} live listing${d.listings_active === 1 ? '' : 's'} and no bookings yet — once renters request, this page lights up.`
      : 'No active listings yet. Post your first to start tracking performance.'
  }
  const earned = Number(d.earned_revenue)
  const pipeline = Number(d.pipeline_revenue)
  const parts: string[] = []
  parts.push(
    `You have earned <b>UZS ${fmtUZS(earned)}</b> across ${d.bookings_total} booking${d.bookings_total === 1 ? '' : 's'} on Ijara.`,
  )
  if (pipeline > 0) {
    parts.push(
      `Another <b>UZS ${fmtUZS(pipeline)}</b> is in flight — paid by renters and on its way to complete.`,
    )
  }
  if (d.last_30d_count > 0) {
    parts.push(
      `In the last 30 days you took ${d.last_30d_count} booking${d.last_30d_count === 1 ? '' : 's'}.`,
    )
  }
  return parts.join(' ')
})

// State chart — color tokens per FSM state.
const STATE_TONE: Record<BookingState, string> = {
  requested: 'bg-amber-400',
  accepted: 'bg-emerald-400',
  paid: 'bg-emerald-600',
  picked_up: 'bg-blue-500',
  returned: 'bg-blue-600',
  completed: 'bg-slate-700',
  rejected: 'bg-red-400',
  cancelled: 'bg-red-300',
  disputed: 'bg-purple-500',
}

const showAllStates = ref(false)

const visibleStates = computed(() => {
  if (!data.value) return []
  if (showAllStates.value) return data.value.state_breakdown
  return data.value.state_breakdown.filter((s) => s.count > 0)
})

const hiddenStateCount = computed(() => {
  if (!data.value) return 0
  return data.value.state_breakdown.filter((s) => s.count === 0).length
})

const maxStateCount = computed(() => {
  if (!data.value) return 1
  return Math.max(...data.value.state_breakdown.map((s) => s.count), 1)
})

// Top listings: only those that have ever had a booking. Sort by
// revenue first (most useful "top" signal) then booking count.
const performingListings = computed(() => {
  if (!data.value) return []
  return data.value.top_listings
    .filter((l) => l.booking_count > 0)
    .slice()
    .sort((a, b) => {
      const r = Number(b.revenue) - Number(a.revenue)
      if (r !== 0) return r
      return b.booking_count - a.booking_count
    })
})

const maxTopRevenue = computed(() => {
  return Math.max(...performingListings.value.map((l) => Number(l.revenue || 0)), 1)
})

function stateBadgeClass(state: string): string {
  if (state === 'requested') return 'bg-amber-50 text-amber-800 border-amber-200'
  if (state === 'accepted' || state === 'paid')
    return 'bg-emerald-50 text-emerald-800 border-emerald-200'
  if (state === 'picked_up' || state === 'returned')
    return 'bg-blue-50 text-blue-800 border-blue-200'
  if (state === 'completed') return 'bg-slate-100 text-slate-700 border-slate-200'
  if (state === 'rejected' || state === 'cancelled') return 'bg-red-50 text-red-700 border-red-200'
  if (state === 'disputed') return 'bg-purple-50 text-purple-800 border-purple-200'
  return 'bg-gray-100 text-gray-600 border-gray-200'
}
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] bg-gray-50">
    <div class="max-w-6xl mx-auto px-6 py-10 space-y-6">
      <!-- Header -->
      <header class="flex items-end justify-between gap-4 flex-wrap">
        <div class="space-y-2">
          <NuxtLink to="/dashboard/listings" class="text-sm text-gray-500 hover:text-gray-900">
            ← Dashboard
          </NuxtLink>
          <h1 class="text-3xl font-semibold tracking-tight">Analytics</h1>
        </div>
        <button
          type="button"
          class="rounded-md border border-gray-300 bg-white text-sm text-gray-700 px-4 py-2 hover:bg-gray-50 transition"
          @click="load"
        >
          Refresh
        </button>
      </header>

      <!-- Loading / error -->
      <div
        v-if="loading"
        class="rounded-xl border border-gray-200 bg-white p-12 text-center text-sm text-gray-500"
      >
        Loading analytics…
      </div>

      <div
        v-else-if="errorMsg"
        class="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700"
      >
        {{ errorMsg }}
      </div>

      <template v-else-if="data">
        <!-- Plain-English summary -->
        <section class="rounded-2xl bg-slate-900 text-white p-6 sm:p-8">
          <p class="text-xs uppercase tracking-wider text-slate-400 font-medium mb-2">
            At a glance
          </p>
          <p class="text-base sm:text-lg leading-relaxed text-white/90" v-html="summary" />
        </section>

        <!-- TWO BIG GROUPS: Money & Activity -->
        <section class="grid lg:grid-cols-2 gap-6">
          <!-- ===== MONEY ===== -->
          <div class="rounded-xl border border-gray-200 bg-white p-6 space-y-5">
            <div class="flex items-center gap-2">
              <div
                class="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center"
              >
                <svg
                  class="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <line x1="12" y1="1" x2="12" y2="23" />
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
              </div>
              <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500">Money</h2>
            </div>

            <!-- Headline number: earned. -->
            <div>
              <p class="text-xs text-gray-500 mb-0.5">Earned and settled</p>
              <p class="text-4xl font-semibold tabular-nums text-gray-900">
                UZS {{ fmtUZS(data.earned_revenue) }}
              </p>
              <p class="text-xs text-gray-500 mt-1">Total from completed bookings.</p>
            </div>

            <div class="border-t border-gray-100 pt-4 grid grid-cols-2 gap-4">
              <div>
                <p class="text-xs text-gray-500 mb-0.5">Coming in</p>
                <p class="text-xl font-semibold tabular-nums text-gray-900">
                  UZS {{ fmtUZS(data.pipeline_revenue) }}
                </p>
                <p class="text-xs text-gray-500 mt-1">Paid by renters, item not yet returned.</p>
              </div>
              <div>
                <p class="text-xs text-gray-500 mb-0.5">Last 30 days</p>
                <p class="text-xl font-semibold tabular-nums text-gray-900">
                  UZS {{ fmtUZS(data.last_30d_revenue) }}
                </p>
                <p class="text-xs text-gray-500 mt-1">Settled in the past month.</p>
              </div>
            </div>
          </div>

          <!-- ===== ACTIVITY ===== -->
          <div class="rounded-xl border border-gray-200 bg-white p-6 space-y-5">
            <div class="flex items-center gap-2">
              <div
                class="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center"
              >
                <svg
                  class="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                </svg>
              </div>
              <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500">Activity</h2>
            </div>

            <!-- Headline number: bookings. -->
            <div>
              <p class="text-xs text-gray-500 mb-0.5">Bookings lifetime</p>
              <p class="text-4xl font-semibold tabular-nums text-gray-900">
                {{ data.bookings_total }}
              </p>
              <p class="text-xs text-gray-500 mt-1">Across every state, since you joined.</p>
            </div>

            <div class="border-t border-gray-100 pt-4 grid grid-cols-2 gap-4">
              <div>
                <p class="text-xs text-gray-500 mb-0.5">Listings live</p>
                <p class="text-xl font-semibold tabular-nums text-gray-900">
                  {{ data.listings_active }}
                  <span class="text-sm text-gray-400 font-normal">/ {{ data.listings_total }}</span>
                </p>
                <p class="text-xs text-gray-500 mt-1">Active out of all you've published.</p>
              </div>
              <div>
                <p class="text-xs text-gray-500 mb-0.5">Acceptance</p>
                <p class="text-xl font-semibold tabular-nums text-gray-900">
                  {{ data.acceptance_rate }}<span class="text-sm font-normal text-gray-400">%</span>
                </p>
                <p class="text-xs text-gray-500 mt-1">Requests you've said yes to.</p>
              </div>
            </div>
          </div>
        </section>

        <!-- WHERE EVERY BOOKING STANDS -->
        <section class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
          <div class="flex items-center justify-between gap-4">
            <div>
              <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500">
                Where every booking stands
              </h2>
              <p class="text-xs text-gray-500 mt-0.5">
                {{ data.bookings_total }} booking{{ data.bookings_total === 1 ? '' : 's' }} grouped
                by current state.
              </p>
            </div>
            <button
              v-if="hiddenStateCount > 0"
              type="button"
              class="text-xs text-slate-700 hover:text-slate-900 underline"
              @click="showAllStates = !showAllStates"
            >
              {{ showAllStates ? 'Hide empty' : `Show all ${data.state_breakdown.length} states` }}
            </button>
          </div>

          <div v-if="data.bookings_total === 0" class="text-sm text-gray-500 py-4 text-center">
            No bookings yet.
          </div>
          <ul v-else class="space-y-2.5">
            <li
              v-for="row in visibleStates"
              :key="row.state"
              class="grid grid-cols-[120px_1fr_44px] items-center gap-3 text-sm"
            >
              <span :class="['text-gray-700', row.count === 0 && 'text-gray-400']">
                {{ BOOKING_STATE_LABELS[row.state] }}
              </span>
              <div class="h-2.5 rounded-full bg-gray-100 overflow-hidden">
                <div
                  :class="[
                    'h-full rounded-full transition-all',
                    STATE_TONE[row.state] ?? 'bg-gray-400',
                  ]"
                  :style="{ width: (row.count / maxStateCount) * 100 + '%' }"
                />
              </div>
              <span
                :class="[
                  'text-right tabular-nums',
                  row.count === 0 ? 'text-gray-400' : 'text-gray-900 font-medium',
                ]"
              >
                {{ row.count }}
              </span>
            </li>
          </ul>
        </section>

        <!-- TOP LISTINGS + RECENT ACTIVITY -->
        <section class="grid lg:grid-cols-2 gap-6">
          <!-- Top listings (only those with bookings) -->
          <div class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500">
                  Best earning listings
                </h2>
                <p class="text-xs text-gray-500 mt-0.5">Sorted by revenue.</p>
              </div>
              <NuxtLink
                to="/dashboard/listings"
                class="text-xs text-slate-700 hover:text-slate-900 underline"
              >
                Manage all →
              </NuxtLink>
            </div>
            <div
              v-if="performingListings.length === 0"
              class="text-sm text-gray-500 py-6 text-center space-y-1"
            >
              <p>No listing has earned yet.</p>
              <p class="text-xs">
                <NuxtLink
                  to="/dashboard/listings"
                  class="underline text-slate-700 hover:text-slate-900"
                >
                  Manage your listings
                </NuxtLink>
                or
                <NuxtLink
                  to="/dashboard/listings/new"
                  class="underline text-slate-700 hover:text-slate-900"
                >
                  post a new one </NuxtLink
                >.
              </p>
            </div>
            <ul v-else class="space-y-3">
              <li v-for="(l, idx) in performingListings" :key="l.id" class="space-y-1.5">
                <div class="flex items-center gap-3 text-sm">
                  <span
                    class="w-5 h-5 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-[11px] font-medium shrink-0"
                  >
                    {{ idx + 1 }}
                  </span>
                  <NuxtLink
                    :to="`/listings/${l.id}`"
                    class="font-medium text-gray-900 hover:underline truncate"
                  >
                    {{ l.title }}
                  </NuxtLink>
                  <span
                    v-if="!l.is_active"
                    class="ml-auto text-[10px] uppercase tracking-wider text-gray-400 shrink-0"
                  >
                    inactive
                  </span>
                </div>
                <div class="flex items-center gap-3 text-xs text-gray-500 pl-8">
                  <span>{{ categoryLabel(l.category) }} · {{ districtLabel(l.district) }}</span>
                  <span class="ml-auto tabular-nums shrink-0 text-gray-700">
                    UZS {{ fmtUZS(l.revenue) }}
                    <span class="text-gray-400"
                      >· {{ l.booking_count }} booking{{ l.booking_count === 1 ? '' : 's' }}</span
                    >
                  </span>
                </div>
                <div class="ml-8 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    class="h-full bg-emerald-600 rounded-full"
                    :style="{ width: (Number(l.revenue) / maxTopRevenue) * 100 + '%' }"
                  />
                </div>
              </li>
            </ul>
          </div>

          <!-- Recent bookings -->
          <div class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500">
                  Recent activity
                </h2>
                <p class="text-xs text-gray-500 mt-0.5">
                  Last {{ data.recent_bookings.length }} bookings.
                </p>
              </div>
              <NuxtLink
                to="/dashboard/bookings"
                class="text-xs text-slate-700 hover:text-slate-900 underline"
              >
                See all →
              </NuxtLink>
            </div>
            <div
              v-if="data.recent_bookings.length === 0"
              class="text-sm text-gray-500 py-6 text-center"
            >
              Nothing yet. New requests show up here.
            </div>
            <ul v-else class="divide-y divide-gray-100">
              <li
                v-for="b in data.recent_bookings"
                :key="b.id"
                class="py-3 first:pt-0 last:pb-0 flex items-start gap-3"
              >
                <div class="flex-1 min-w-0 space-y-0.5">
                  <NuxtLink
                    :to="`/bookings/${b.id}`"
                    class="block font-medium text-gray-900 hover:underline truncate text-sm"
                  >
                    {{ b.listing_title }}
                  </NuxtLink>
                  <p class="text-xs text-gray-500 truncate">
                    {{ b.renter_display_name }}
                    · {{ formatTashkent(b.start_at) }} ·
                    {{ b.payment_method === 'stripe' ? 'Stripe' : 'Cash' }}
                  </p>
                </div>
                <div class="text-right shrink-0 space-y-1">
                  <span
                    :class="[
                      'inline-block rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap',
                      stateBadgeClass(b.state),
                    ]"
                  >
                    {{ BOOKING_STATE_LABELS[b.state] }}
                  </span>
                  <p class="text-xs tabular-nums text-gray-700">UZS {{ fmtUZS(b.total_amount) }}</p>
                </div>
              </li>
            </ul>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
