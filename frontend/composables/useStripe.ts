import type { Stripe } from '@stripe/stripe-js'

interface StripeConfig {
  configured: boolean
  publishable_key: string
}

let cachedConfig: StripeConfig | null = null
let cachedStripe: Stripe | null = null
let cachedStripePromise: Promise<Stripe | null> | null = null

export function useStripe() {
  const publicApi = useApi()
  const authedApi = useAuthedApi()

  async function loadConfig(): Promise<StripeConfig> {
    if (cachedConfig) return cachedConfig
    cachedConfig = await publicApi<StripeConfig>('payments/config/')
    return cachedConfig
  }

  async function loadStripe(): Promise<Stripe | null> {
    if (cachedStripe) return cachedStripe
    if (cachedStripePromise) return cachedStripePromise
    const config = await loadConfig()
    if (!config.configured) return null
    cachedStripePromise = (async () => {
      const { loadStripe: loadStripeJs } = await import('@stripe/stripe-js')
      cachedStripe = await loadStripeJs(config.publishable_key)
      return cachedStripe
    })()
    return cachedStripePromise
  }

  function createPaymentIntent(bookingId: number) {
    return authedApi<{
      client_secret: string
      amount_cents: number
      currency: string
      publishable_key: string
    }>('payments/intent/', {
      method: 'POST',
      body: { booking: bookingId },
    })
  }

  function createCheckoutSession(bookingId: number, returnTo: string) {
    return authedApi<{ url: string }>('payments/checkout/', {
      method: 'POST',
      body: { booking: bookingId, return_to: returnTo },
    })
  }

  function verifySession(bookingId: number, sessionId: string) {
    return authedApi<{ booking_id: number; state: string }>('payments/verify/', {
      method: 'POST',
      body: { booking: bookingId, session_id: sessionId },
    })
  }

  return {
    loadConfig,
    loadStripe,
    createPaymentIntent,
    createCheckoutSession,
    verifySession,
  }
}
