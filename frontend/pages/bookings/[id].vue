<script setup lang="ts">
// pages/bookings/[id].vue
// Booking detail with full state-transition timeline. Action buttons
// gated by actor role + current state.

import {
  BOOKING_STATE_LABELS,
  formatTashkent,
  useBookings,
  type BookingState,
} from '~/composables/useBookings'
import { CATEGORIES, DISTRICTS } from '~/composables/useListings'
import { useStripe } from '~/composables/useStripe'

definePageMeta({
  middleware: ['auth'],
})

const route = useRoute()
const auth = useAuthStore()
const toast = useToast()
const { fetchBooking, transitionBooking } = useBookings()

const booking = ref<any>(null)
const loadError = ref<string | null>(null)
const actError = ref<string | null>(null)
const acting = ref(false)

async function load() {
  try {
    booking.value = await fetchBooking(route.params.id as string)
  } catch {
    loadError.value = 'Booking not found.'
  }
}

// Client-only: auth-protected fetch, see plugins/auth.client.ts.
onMounted(load)

const isOwner = computed(() => auth.user?.id === booking.value?.owner_id)
const isRenter = computed(() => auth.user?.id === booking.value?.renter)

interface Action {
  label: string
  state: BookingState
  primary?: boolean
  danger?: boolean
}

const availableActions = computed<Action[]>(() => {
  if (!booking.value) return []
  const state = booking.value.state as BookingState
  const isStripe = booking.value.payment_method === 'stripe'
  if (isOwner.value) {
    if (state === 'requested')
      return [
        { label: 'Accept', state: 'accepted', primary: true },
        { label: 'Reject', state: 'rejected', danger: true },
      ]
    if (state === 'accepted') {
      // Stripe bookings: owner must wait for the renter to pay before
      // pickup. Cash bookings settle at handover, so pickup is fine.
      if (isStripe) {
        return [{ label: 'Cancel', state: 'cancelled', danger: true }]
      }
      return [
        { label: 'Mark picked up', state: 'picked_up', primary: true },
        { label: 'Cancel', state: 'cancelled' },
      ]
    }
    if (state === 'paid')
      return [
        { label: 'Mark picked up', state: 'picked_up', primary: true },
        { label: 'Cancel', state: 'cancelled' },
      ]
    if (state === 'picked_up') return [{ label: 'Mark returned', state: 'returned', primary: true }]
    if (state === 'returned') return [{ label: 'Complete', state: 'completed', primary: true }]
  }
  if (isRenter.value) {
    if (state === 'requested' || state === 'accepted')
      return [{ label: 'Cancel', state: 'cancelled', danger: true }]
  }
  return []
})

// Status banner for the owner — explains why "Mark picked up" is missing
// while a Stripe booking is still in `accepted`.
const ownerHint = computed(() => {
  if (!booking.value || !isOwner.value) return null
  if (booking.value.state === 'accepted' && booking.value.payment_method === 'stripe') {
    return 'Waiting on the renter to pay with card. Mark-pickup unlocks once Stripe confirms the payment.'
  }
  return null
})

// Status banner for the renter — once they have paid (or accepted for
// cash), the FSM hands control to the owner. Tell them what to expect
// at each step so the empty action panel does not feel like a dead end.
const renterHint = computed(() => {
  if (!booking.value || !isRenter.value) return null
  const state = booking.value.state
  const isStripe = booking.value.payment_method === 'stripe'
  if (state === 'requested') {
    return {
      tone: 'amber',
      text: 'Waiting on the owner to accept your request. You can cancel any time before they do.',
    }
  }
  if (state === 'accepted') {
    return isStripe
      ? {
          tone: 'emerald',
          text: 'Owner accepted. Pay with card above to confirm — your spot is held but not finalised until payment lands.',
        }
      : {
          tone: 'emerald',
          text: 'Owner accepted. Bring cash on pickup. The owner will mark the booking as picked up at handover.',
        }
  }
  if (state === 'paid') {
    return {
      tone: 'emerald',
      text: 'Payment received. Stripe sent a receipt to your email. Collect the item from the owner — they will mark it as picked up at handover.',
    }
  }
  if (state === 'picked_up') {
    return {
      tone: 'blue',
      text: 'Item is with you. When you return it, the owner will mark it returned and complete the booking.',
    }
  }
  if (state === 'returned') {
    return {
      tone: 'blue',
      text: 'Owner has confirmed return. Awaiting final completion — usually within a few minutes.',
    }
  }
  if (state === 'completed') {
    return {
      tone: 'slate',
      text: 'Booking complete. Thanks for renting on Ijara.',
    }
  }
  if (state === 'rejected') {
    return {
      tone: 'red',
      text: 'Owner declined this request. No charge was taken. Try a different listing or reach out to the owner.',
    }
  }
  if (state === 'cancelled') {
    return {
      tone: 'red',
      text: 'This booking was cancelled. If you paid by card, Stripe will refund automatically — please allow up to 5 business days.',
    }
  }
  return null
})

async function act(state: BookingState) {
  actError.value = null
  acting.value = true
  try {
    await transitionBooking(booking.value.id, state)
    await load()
    toast.add({ title: `Booking is now ${BOOKING_STATE_LABELS[state]}.` })
  } catch (err: any) {
    actError.value = err?.data?.state?.[0] ?? 'Action failed.'
  } finally {
    acting.value = false
  }
}

// Stripe Checkout flow (Phase 6).
//
// Uses Stripe-hosted Checkout instead of an embedded Payment Element:
// click → POST /payments/checkout/ → window.location to Stripe → user
// pays on Stripe's page → Stripe redirects back with ?stripe_session=
// → we POST /payments/verify/ which confirms the session against
// Stripe's API and flips the booking to `paid`. No webhook required
// for the demo to work end-to-end (the webhook stays as a backup).
const stripeApi = useStripe()
const stripeConfig = ref<{ configured: boolean } | null>(null)
const stripeUI = ref<'idle' | 'redirecting' | 'verifying' | 'failed' | 'cancelled'>('idle')
const stripeError = ref<string | null>(null)

const showStripeButton = computed(
  () =>
    isRenter.value &&
    booking.value?.state === 'accepted' &&
    booking.value?.payment_method === 'stripe' &&
    stripeConfig.value?.configured,
)

// Load Stripe config once the booking arrives in `accepted`+Stripe.
watch(
  booking,
  async (b) => {
    if (
      b &&
      isRenter.value &&
      b.payment_method === 'stripe' &&
      b.state === 'accepted' &&
      !stripeConfig.value
    ) {
      stripeConfig.value = await stripeApi.loadConfig()
    }
  },
  { immediate: true },
)

// On return from Stripe Checkout the URL carries ?stripe_session=cs_...
// Verify against Stripe to flip the booking, then strip the param.
const router = useRouter()
watch(
  booking,
  async (b) => {
    if (!b || !isRenter.value) return
    const sessionId = route.query.stripe_session as string | undefined
    const cancelled = route.query.stripe_cancelled as string | undefined
    if (cancelled) {
      stripeUI.value = 'cancelled'
      await router.replace({ query: {} })
      return
    }
    if (!sessionId) return
    stripeUI.value = 'verifying'
    try {
      await stripeApi.verifySession(b.id, sessionId)
      await load()
      toast.add({ title: 'Payment received.' })
      stripeUI.value = 'idle'
    } catch (err: any) {
      stripeError.value = err?.data?.stripe_session?.[0] ?? 'Could not verify payment with Stripe.'
      stripeUI.value = 'failed'
    } finally {
      await router.replace({ query: {} })
    }
  },
  { immediate: true },
)

async function startStripeCheckout() {
  stripeError.value = null
  stripeUI.value = 'redirecting'
  try {
    const { url } = await stripeApi.createCheckoutSession(
      booking.value.id,
      route.fullPath.split('?')[0],
    )
    window.location.href = url
  } catch (err: any) {
    stripeError.value = err?.data?.detail ?? err?.message ?? 'Could not start Stripe Checkout.'
    stripeUI.value = 'failed'
  }
}

function stateStyle(state: string): string {
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

function categoryLabel(v: string): string {
  return CATEGORIES.find((c) => c.value === v)?.label ?? v
}
function districtLabel(v: string): string {
  return DISTRICTS.find((d) => d.value === v)?.label ?? v
}
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] bg-gray-50">
    <div v-if="loadError" class="max-w-xl mx-auto py-20 text-center space-y-3">
      <p class="text-2xl">🔎</p>
      <h1 class="text-xl font-semibold">Booking not found</h1>
      <NuxtLink
        to="/dashboard/bookings"
        class="inline-block rounded-md border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
      >
        ← Back to my bookings
      </NuxtLink>
    </div>

    <div v-else-if="booking" class="max-w-4xl mx-auto px-6 py-10 space-y-8">
      <NuxtLink to="/dashboard/bookings" class="text-sm text-gray-500 hover:text-gray-900">
        ← My bookings
      </NuxtLink>

      <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h1 class="text-2xl md:text-3xl font-semibold tracking-tight">
            Booking #{{ booking.id }}
          </h1>
          <p class="text-sm text-gray-600 mt-1">
            <NuxtLink
              :to="`/listings/${booking.listing}`"
              class="font-medium text-slate-800 hover:underline"
            >
              {{ booking.listing_title }}
            </NuxtLink>
            · {{ categoryLabel(booking.listing_category) }} ·
            {{ districtLabel(booking.listing_district) }}
          </p>
        </div>
        <span
          :class="[
            'self-start md:self-auto rounded-full border px-3 py-1 text-sm font-medium',
            stateStyle(booking.state),
          ]"
        >
          {{ BOOKING_STATE_LABELS[booking.state as BookingState] ?? booking.state }}
        </span>
      </header>

      <!-- Summary card -->
      <section
        class="rounded-xl border border-gray-200 bg-white p-6 grid sm:grid-cols-2 gap-x-8 gap-y-5"
      >
        <div>
          <p class="text-xs text-gray-500">Pickup</p>
          <p class="font-medium">{{ formatTashkent(booking.start_at) }}</p>
          <p class="text-xs text-gray-500 mt-0.5">Asia/Tashkent</p>
        </div>
        <div>
          <p class="text-xs text-gray-500">Return</p>
          <p class="font-medium">{{ formatTashkent(booking.end_at) }}</p>
          <p class="text-xs text-gray-500 mt-0.5">Asia/Tashkent</p>
        </div>
        <div>
          <p class="text-xs text-gray-500">Owner</p>
          <NuxtLink
            :to="`/users/${booking.owner_id}`"
            class="font-medium text-slate-800 hover:underline"
          >
            {{ booking.owner_display_name || 'Ijara user' }}
          </NuxtLink>
        </div>
        <div>
          <p class="text-xs text-gray-500">Renter</p>
          <NuxtLink
            :to="`/users/${booking.renter}`"
            class="font-medium text-slate-800 hover:underline"
          >
            {{ booking.renter_display_name || 'Ijara user' }}
          </NuxtLink>
        </div>
        <div>
          <p class="text-xs text-gray-500">Pricing</p>
          <p class="font-medium">
            UZS {{ Number(booking.unit_price).toLocaleString('en-US') }} × {{ booking.quantity }}
            {{ booking.unit }}{{ booking.quantity === 1 ? '' : 's' }}
          </p>
        </div>
        <div>
          <p class="text-xs text-gray-500">
            Total · {{ booking.payment_method === 'stripe' ? 'Stripe' : 'Cash on pickup' }}
          </p>
          <p class="font-semibold text-lg">
            UZS {{ Number(booking.total_amount).toLocaleString('en-US') }}
          </p>
        </div>
        <div v-if="booking.note" class="sm:col-span-2">
          <p class="text-xs text-gray-500">Renter's message</p>
          <p
            class="mt-1 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm italic text-slate-700"
          >
            "{{ booking.note }}"
          </p>
        </div>
      </section>

      <!-- Stripe Payment (hosted Checkout flow) -->
      <section
        v-if="
          showStripeButton ||
          stripeUI === 'verifying' ||
          stripeUI === 'cancelled' ||
          stripeUI === 'failed'
        "
        class="rounded-xl border border-gray-200 bg-white p-6 space-y-4"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500">
              Pay with card
            </h2>
            <p class="mt-1 text-sm text-gray-600">
              You will be sent to Stripe's secure payment page. After paying, Stripe brings you back
              here automatically.
            </p>
          </div>
          <span class="hidden sm:inline-flex items-center gap-1 text-xs text-gray-500">
            <svg
              class="w-3.5 h-3.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            Hosted by Stripe
          </span>
        </div>

        <div v-if="stripeUI === 'verifying'" class="flex items-center gap-2 text-sm text-gray-600">
          <div
            class="w-4 h-4 border-2 border-gray-300 border-t-slate-900 rounded-full animate-spin"
          />
          Verifying your payment with Stripe…
        </div>

        <div
          v-else-if="stripeUI === 'cancelled'"
          class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
        >
          You cancelled the payment. Try again whenever you are ready.
        </div>

        <button
          v-if="
            showStripeButton &&
            (stripeUI === 'idle' || stripeUI === 'failed' || stripeUI === 'cancelled')
          "
          type="button"
          :disabled="stripeUI === 'redirecting'"
          class="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-md bg-[#635bff] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#544aff] disabled:opacity-50 transition-colors"
          @click="startStripeCheckout"
        >
          <svg
            v-if="stripeUI === 'redirecting'"
            class="w-4 h-4 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
          >
            <path d="M21 12a9 9 0 1 1-6.2-8.55" />
          </svg>
          <span v-if="stripeUI === 'redirecting'">Redirecting to Stripe…</span>
          <span v-else-if="stripeUI === 'failed' || stripeUI === 'cancelled'">Try again</span>
          <span v-else>Pay UZS {{ Number(booking.total_amount).toLocaleString('en-US') }}</span>
        </button>

        <p v-if="stripeError" class="text-sm text-red-600">{{ stripeError }}</p>

        <p class="text-xs text-gray-500">
          Test card: <code>4242 4242 4242 4242</code>, any future expiry, any CVC, any postal code.
          Decline: <code>4000 0000 0000 9995</code>.
        </p>
      </section>

      <!-- Owner hint while waiting on a Stripe payment -->
      <section
        v-if="ownerHint"
        class="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-start gap-3"
      >
        <svg
          class="w-5 h-5 text-amber-600 mt-0.5 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <circle cx="12" cy="16" r="0.5" fill="currentColor" />
        </svg>
        <p class="text-sm text-amber-900">{{ ownerHint }}</p>
      </section>

      <!-- Renter "what's next" banner — tone-coloured by booking state -->
      <section
        v-if="renterHint"
        :class="[
          'rounded-xl border p-4 flex items-start gap-3',
          {
            amber: 'border-amber-200 bg-amber-50',
            emerald: 'border-emerald-200 bg-emerald-50',
            blue: 'border-blue-200 bg-blue-50',
            slate: 'border-slate-200 bg-slate-50',
            red: 'border-red-200 bg-red-50',
          }[renterHint.tone] ?? 'border-gray-200 bg-gray-50',
        ]"
      >
        <svg
          :class="[
            'w-5 h-5 mt-0.5 shrink-0',
            {
              amber: 'text-amber-600',
              emerald: 'text-emerald-600',
              blue: 'text-blue-600',
              slate: 'text-slate-600',
              red: 'text-red-600',
            }[renterHint.tone] ?? 'text-gray-600',
          ]"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
        <p
          :class="[
            'text-sm',
            {
              amber: 'text-amber-900',
              emerald: 'text-emerald-900',
              blue: 'text-blue-900',
              slate: 'text-slate-700',
              red: 'text-red-800',
            }[renterHint.tone] ?? 'text-gray-800',
          ]"
        >
          {{ renterHint.text }}
        </p>
      </section>

      <!-- Actions -->
      <section
        v-if="availableActions.length"
        class="rounded-xl border border-gray-200 bg-white p-6 space-y-3"
      >
        <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500">What's next</h2>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="a in availableActions"
            :key="a.state"
            type="button"
            :disabled="acting"
            :class="[
              'rounded-md px-4 py-2 text-sm font-medium transition disabled:opacity-50',
              a.primary
                ? 'bg-slate-900 text-white hover:bg-slate-800'
                : a.danger
                  ? 'border border-red-300 text-red-700 hover:bg-red-50'
                  : 'border border-gray-300 text-gray-700 hover:bg-gray-50',
            ]"
            @click="act(a.state)"
          >
            {{ a.label }}
          </button>
        </div>
        <p v-if="actError" class="text-sm text-red-600">{{ actError }}</p>
      </section>

      <!-- Timeline -->
      <section class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500">Timeline</h2>
        <ol class="space-y-4">
          <li v-for="t in booking.transitions" :key="t.id" class="flex gap-3">
            <div class="flex flex-col items-center">
              <span
                :class="[
                  'w-2.5 h-2.5 rounded-full mt-1.5',
                  t.to_state === 'rejected' || t.to_state === 'cancelled'
                    ? 'bg-red-400'
                    : t.to_state === 'completed'
                      ? 'bg-emerald-500'
                      : 'bg-slate-700',
                ]"
              ></span>
              <span class="flex-1 w-px bg-gray-200 mt-1"></span>
            </div>
            <div class="pb-3 flex-1">
              <p class="text-sm">
                <span class="font-medium">
                  {{
                    t.from_state ? `${BOOKING_STATE_LABELS[t.from_state as BookingState]} → ` : ''
                  }}
                  {{ BOOKING_STATE_LABELS[t.to_state as BookingState] }}
                </span>
                <span class="text-gray-500"> by {{ t.actor_display_name }} </span>
              </p>
              <p class="text-xs text-gray-500 mt-0.5">
                {{ formatTashkent(t.created_at) }}
                <template v-if="t.reason"> · "{{ t.reason }}"</template>
              </p>
            </div>
          </li>
        </ol>
      </section>
    </div>
  </main>
</template>
