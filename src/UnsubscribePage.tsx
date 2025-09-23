import React, { useState } from 'react';
import { useAuth } from './AuthContext';
import { apiCall } from './api';

interface UnsubscribePageProps {
  onBack: () => void;
}

export const UnsubscribePage: React.FC<UnsubscribePageProps> = ({ onBack }) => {
  const { user } = useAuth();
  const [isUnsubscribing, setIsUnsubscribing] = useState(false);
  const [isUnsubscribed, setIsUnsubscribed] = useState(false);
  const [error, setError] = useState('');

  const handleUnsubscribe = async () => {
    if (!user) return;

    setIsUnsubscribing(true);
    setError('');

    try {
      const response = await apiCall('/api/unsubscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userId: user.uid,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to unsubscribe');
      }

      setIsUnsubscribed(true);
    } catch (error) {
      console.error('Unsubscribe error:', error);
      setError(error instanceof Error ? error.message : 'Failed to unsubscribe');
    } finally {
      setIsUnsubscribing(false);
    }
  };

  if (isUnsubscribed) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="text-center space-y-6 p-8" style={{ border: '3px solid #000000' }}>
            <h1 className="text-3xl font-bold text-black">Successfully Unsubscribed</h1>
            <p className="text-gray-700">
              Your subscription has been cancelled. You'll continue to have access to paid features until the end of your current billing period.
            </p>
            <p className="text-sm text-gray-600">
              Your account will automatically switch to the free tier when your subscription expires.
            </p>
            <button
              onClick={onBack}
              className="w-full px-6 py-3 bg-transparent text-black font-semibold hover:bg-black hover:text-white"
              style={{ border: '3px solid #000000' }}
            >
              Back to Search
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="text-center space-y-6 p-8" style={{ border: '3px solid #000000' }}>
          <h1 className="text-3xl font-bold text-black">Cancel Subscription</h1>
          
          <div className="text-left space-y-4">
            <p className="text-gray-700">
              We're sorry to see you go! Are you sure you want to cancel your subscription?
            </p>
            
            <div className="bg-gray-50 p-4 space-y-2" style={{ border: '2px solid #000000' }}>
              <h3 className="font-semibold text-black">What happens when you cancel:</h3>
              <ul className="text-sm text-gray-700 space-y-1">
                <li>• You'll keep access to paid features until your billing period ends</li>
                <li>• Your account will switch to the free tier automatically</li>
                <li>• You can resubscribe at any time</li>
                <li>• Your search history will be preserved</li>
              </ul>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-700 text-sm" style={{ border: '2px solid #dc2626' }}>
              {error}
            </div>
          )}

          <div className="space-y-3">
            <button
              onClick={handleUnsubscribe}
              disabled={isUnsubscribing}
              className="w-full px-6 py-3 bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50"
              style={{ border: '3px solid #000000' }}
            >
              {isUnsubscribing ? 'Cancelling...' : 'Yes, Cancel Subscription'}
            </button>
            
            <button
              onClick={onBack}
              disabled={isUnsubscribing}
              className="w-full px-6 py-3 bg-transparent text-black font-semibold hover:bg-black hover:text-white disabled:opacity-50"
              style={{ border: '3px solid #000000' }}
            >
              Keep Subscription
            </button>
          </div>

          <p className="text-xs text-gray-500">
            Need help? Contact us before cancelling and we'll do our best to resolve any issues.
          </p>
        </div>
      </div>
    </div>
  );
};