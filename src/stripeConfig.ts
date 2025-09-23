// Stripe configuration
// Note: Publishable keys are safe to expose on the frontend
export const STRIPE_CONFIG = {
  // TODO: Replace with your actual Stripe publishable key (pk_live_... or pk_test_...)
  publishableKey: import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || 'pk_live_51SAOJuLyxmrWdjoa9TvO3JduHeYks3PAQX9IjdjmsC482g4Ri1WLGYO4ZvWPb5fNafnmVwIpedbZRqKKC0vuVpdZ00NKZAnVsB',
  
  // Live mode Price ID for RedditSearch Pro ($1.00/month)
  priceId: import.meta.env.VITE_STRIPE_PRICE_ID || 'price_1SAOoQLyxmrWdjoajIPo7BTo',
  
  // Your app's base URL for success/cancel redirects
  baseUrl: window.location.origin
};