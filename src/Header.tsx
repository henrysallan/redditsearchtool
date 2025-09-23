import React from 'react';
import { useAuth } from './AuthContext';
import { getUsageMessage, type UsageStatus } from './usageTracking';

interface HeaderProps {
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
  usageStatus?: UsageStatus | null;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, sidebarOpen, usageStatus }) => {
  const { user, userProfile, signInWithGoogle, signOut, loading } = useAuth();

  const handleAuthAction = async () => {
    try {
      if (user) {
        await signOut();
      } else {
        await signInWithGoogle();
      }
    } catch (error) {
      console.error('Authentication error:', error);
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-white" style={{ borderBottom: '3px solid #000000' }}>
      <div className="w-full px-6 py-3 flex items-center justify-between">
        {/* Left: Title + History */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {user && (
            <button
              onClick={onToggleSidebar}
              className={
                `px-4 py-2 bg-transparent text-black cursor-pointer font-semibold hover:bg-black hover:text-white ` +
                (sidebarOpen
                  ? 'bg-black text-white'
                  : '')
              }
              style={{ border: '3px solid #000000' }}
            >
              History
            </button>
          )}
          <h1 className="m-0 text-xl font-bold tracking-tight text-black">Reddit Search Tool</h1>
        </div>

        {/* Right: Usage + Auth */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {usageStatus && (
            <div className="px-4 py-2 font-semibold text-black bg-white" style={{ border: '3px solid #000000' }}>
              {getUsageMessage(usageStatus)}
            </div>
          )}

          {loading ? (
            <div className="px-3 py-2 text-sm text-black">Loading...</div>
          ) : user ? (
            <>
              {user.photoURL && (
                <img
                  src={user.photoURL}
                  alt={user.displayName || 'User'}
                  className="h-11"
                  style={{ border: '3px solid #000000', borderRadius: '0', width: 'auto', aspectRatio: '1' }}
                />
              )}
              <button
                onClick={handleAuthAction}
                className="px-4 py-2 bg-transparent text-black cursor-pointer font-semibold hover:bg-black hover:text-white"
                style={{ border: '3px solid #000000' }}
              >
                Sign Out
              </button>
            </>
          ) : (
            <button
              onClick={handleAuthAction}
              className="px-6 py-2 bg-transparent text-black cursor-pointer font-semibold hover:bg-black hover:text-white"
              style={{ border: '3px solid #000000' }}
            >
              Sign in with Google
            </button>
          )}
        </div>
      </div>
    </header>
  );
};