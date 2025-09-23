import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { getUsageMessage, type UsageStatus, type UserTier } from './usageTracking';
import { apiCall } from './api';

interface HeaderProps {
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
  usageStatus?: UsageStatus | null;
  onUpgrade?: () => void;
  onUnsubscribe?: () => void;
  userTier: UserTier;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, sidebarOpen, usageStatus, onUpgrade, onUnsubscribe, userTier }) => {
  const { user, userProfile, signInWithGoogle, signOut, loading } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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

  const handleDeleteAccount = async () => {
    if (!user) return;
    
    const confirmed = window.confirm(
      'Are you sure you want to delete your account? This will:\n\n' +
      '• Cancel your subscription (if any)\n' +
      '• Delete all your search history\n' +
      '• Remove all account data\n\n' +
      'This action cannot be undone.'
    );
    
    if (!confirmed) return;
    
    try {
      // Call backend to delete account
      const response = await apiCall('/api/delete-account', {
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
        throw new Error(errorData.error || 'Failed to delete account');
      }

      // Sign out after successful deletion
      await signOut();
      
      alert('Your account has been successfully deleted.');
    } catch (error) {
      console.error('Delete account error:', error);
      alert(`Failed to delete account: ${error instanceof Error ? error.message : 'Unknown error'}`);
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
          {/* Pro Mode indicator for paid users */}
          {user && userTier === 'paid' && (
            <div className="px-4 py-2 bg-transparent text-black cursor-default font-semibold"
              style={{ border: '3px solid #000000' }}
            >
              Pro Mode
            </div>
          )}
          
          {/* Upgrade button for non-paid users */}
          {user && userTier !== 'paid' && onUpgrade && (
            <button
              onClick={onUpgrade}
              className="px-4 py-2 bg-transparent text-black cursor-pointer font-semibold hover:bg-black hover:text-white"
              style={{ border: '3px solid #000000' }}
            >
              Upgrade
            </button>
          )}
          
          {usageStatus && userTier !== 'paid' && (
            <div className="px-4 py-2 font-semibold text-black bg-white" style={{ border: '3px solid #000000' }}>
              {getUsageMessage(usageStatus, userTier)}
            </div>
          )}

          {loading ? (
            <div className="px-3 py-2 text-sm text-black">Loading...</div>
          ) : user ? (
            <div className="relative" ref={menuRef}>
              {user.photoURL && (
                <img
                  src={user.photoURL}
                  alt={user.displayName || 'User'}
                  className="h-11 cursor-pointer hover:opacity-80"
                  style={{ border: '3px solid #000000', borderRadius: '0', width: 'auto', aspectRatio: '1' }}
                  onClick={() => setShowUserMenu(!showUserMenu)}
                />
              )}
              
              {/* User dropdown menu */}
              {showUserMenu && (
                <div 
                  className="absolute right-0 top-12 bg-white shadow-lg z-50 min-w-[200px]"
                  style={{ border: '3px solid #000000' }}
                >
                  <div className="py-2">
                    <div className="px-4 py-2 text-sm text-gray-700 border-b border-gray-200">
                      {user.displayName || user.email}
                    </div>
                    
                    {userTier === 'paid' && onUnsubscribe && (
                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          onUnsubscribe();
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-black hover:bg-gray-100 border-b border-gray-200"
                      >
                        Unsubscribe
                      </button>
                    )}
                    
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        handleDeleteAccount();
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-100 border-b border-gray-200"
                    >
                      Delete Account
                    </button>
                    
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        handleAuthAction();
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-black hover:bg-gray-100"
                    >
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
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