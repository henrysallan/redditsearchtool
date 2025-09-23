import React, { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { User } from 'firebase/auth';
import { STRIPE_CONFIG } from './stripeConfig';
import { apiCall } from './api';

// Initialize Stripe
const stripePromise = loadStripe(STRIPE_CONFIG.publishableKey);

interface SubscriptionPageProps {
  onBack: () => void;
  user: any;
}

export const SubscriptionPage: React.FC<SubscriptionPageProps> = ({ onBack, user }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [couponCode, setCouponCode] = useState('');
  const [showCouponInput, setShowCouponInput] = useState(false);

  const handleSubscribe = async () => {
    if (!user) {
      setError('Please sign in to subscribe');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // Call your backend to create a Stripe checkout session
      const requestBody: any = {
        userId: user.uid,
        userEmail: user.email,
        priceId: STRIPE_CONFIG.priceId,
      };
      
      // Add coupon code if provided
      if (couponCode.trim()) {
        requestBody.couponCode = couponCode.trim();
      }
      
      const response = await apiCall('/api/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error('Failed to create checkout session');
      }

      const { sessionId } = await response.json();
      
      // Redirect to Stripe checkout
      const stripe = await stripePromise;
      if (stripe) {
        const { error } = await stripe.redirectToCheckout({
          sessionId: sessionId,
        });
        
        if (error) {
          setError(error.message || 'Payment failed');
        }
      } else {
        setError('Payment system unavailable');
      }
    } catch (err) {
      console.error('Subscription error:', err);
      setError(err instanceof Error ? err.message : 'Subscription failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="w-full px-6 py-4" style={{ borderBottom: '3px solid #000000' }}>
        <div className="flex items-center justify-between">
          <button
            onClick={onBack}
            className="px-4 py-2 bg-transparent text-black cursor-pointer hover:bg-black hover:text-white"
            style={{ border: '3px solid #000000' }}
          >
            ← Back
          </button>
          <h1 className="text-2xl font-bold text-black">Upgrade to Pro</h1>
          <div className="w-20"></div> {/* Spacer for center alignment */}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex items-center justify-center min-h-[80vh] px-4">
        <div className="w-full max-w-md">
          {/* Pricing Card */}
          <div 
            className="bg-white text-black p-8 text-center"
            style={{ border: '3px solid #000000' }}
          >
            {/* Plan Name */}
            <h2 className="text-3xl font-bold text-black mb-2">RedditSearch Pro</h2>
            
            {/* Price */}
            <div className="mb-6">
              <span className="text-5xl font-bold text-black">$1</span>
              <span className="text-xl text-gray-600">/month</span>
            </div>

            {/* Features */}
            <div className="mb-8 text-left">
              <h3 className="text-lg font-semibold text-black mb-4">What you get:</h3>
              <ul className="space-y-3">
                <li className="flex items-start space-x-3">
                  <span className="text-black font-bold">✓</span>
                  <span className="text-black">Access to more powerful AI models (Claude, GPT-4)</span>
                </li>
                <li className="flex items-start space-x-3">
                  <span className="text-black font-bold">✓</span>
                  <span className="text-black">More detailed search settings and filters</span>
                </li>
                <li className="flex items-start space-x-3">
                  <span className="text-black font-bold">✓</span>
                  <span className="text-black">Unlimited searches per day</span>
                </li>
                <li className="flex items-start space-x-3">
                  <span className="text-black font-bold">✓</span>
                  <span className="text-black">Priority support and early access to new features</span>
                </li>
              </ul>
            </div>

            {/* Coupon Code Section */}
            <div className="mb-6">
              <button
                type="button"
                onClick={() => setShowCouponInput(!showCouponInput)}
                className="text-sm text-gray-600 hover:text-black underline mb-2"
              >
                Have a coupon code?
              </button>
              
              {showCouponInput && (
                <div className="mt-2">
                  <input
                    type="text"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value)}
                    placeholder="Enter coupon code"
                    className="w-full px-3 py-2 border-2 border-gray-300 focus:border-black outline-none"
                  />
                  {couponCode && (
                    <p className="text-xs text-gray-500 mt-1">
                      Coupon will be applied at checkout
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Subscribe Button */}
            <button
              onClick={handleSubscribe}
              disabled={isLoading || !user}
              className="w-full px-6 py-4 bg-black text-white cursor-pointer font-semibold text-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ border: '3px solid #000000' }}
            >
              {isLoading ? 'Processing...' : 'Subscribe Now'}
            </button>

            {/* Error Message */}
            {error && (
              <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm" style={{ border: '2px solid #dc2626' }}>
                {error}
              </div>
            )}

            {/* Security Note */}
            <p className="mt-4 text-sm text-gray-600">
              Secure payment powered by Stripe. Cancel anytime.
            </p>
          </div>

          {/* Current Plan Info */}
          <div className="mt-6 text-center">
            <p className="text-gray-600">
              Currently on: <span className="font-semibold">Free Plan</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};