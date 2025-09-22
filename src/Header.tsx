import React from 'react';
import { useAuth } from './AuthContext';

interface HeaderProps {
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, sidebarOpen }) => {
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
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      backgroundColor: '#ffffff',
      borderBottom: '2px solid #000000',
      padding: '16px 24px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      {/* Left side - Title and History Toggle */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
      }}>
        {user && (
          <button
            onClick={onToggleSidebar}
            style={{
              background: 'none',
              border: '2px solid #000000',
              padding: '8px 12px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: '600',
              borderRadius: '4px',
              transition: 'all 0.2s ease',
              backgroundColor: sidebarOpen ? '#000000' : 'transparent',
              color: sidebarOpen ? '#ffffff' : '#000000',
            }}
            onMouseEnter={(e) => {
              if (!sidebarOpen) {
                e.currentTarget.style.backgroundColor = '#f0f0f0';
              }
            }}
            onMouseLeave={(e) => {
              if (!sidebarOpen) {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
          >
            ☰ History
          </button>
        )}
        
        <h1 style={{
          margin: 0,
          fontSize: '1.5rem',
          fontWeight: '700',
          color: '#000000',
          letterSpacing: '-0.025em',
        }}>
          Reddit Search Tool
        </h1>
      </div>

      {/* Right side - User Auth */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
      }}>
        {loading ? (
          <div style={{
            padding: '8px 16px',
            color: '#666666',
          }}>
            Loading...
          </div>
        ) : user ? (
          <>
            {user.photoURL && (
              <img
                src={user.photoURL}
                alt={user.displayName || 'User'}
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  border: '2px solid #000000',
                }}
              />
            )}
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-end',
            }}>
              <span style={{
                fontSize: '0.875rem',
                fontWeight: '600',
                color: '#000000',
              }}>
                {user.displayName || 'User'}
              </span>
              <span style={{
                fontSize: '0.75rem',
                color: '#666666',
              }}>
                {user.email}
              </span>
            </div>
            <button
              onClick={handleAuthAction}
              style={{
                background: 'none',
                border: '2px solid #000000',
                padding: '8px 16px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '600',
                borderRadius: '4px',
                transition: 'all 0.2s ease',
                color: '#000000',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#000000';
                e.currentTarget.style.color = '#ffffff';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.color = '#000000';
              }}
            >
              Sign Out
            </button>
          </>
        ) : (
          <button
            onClick={handleAuthAction}
            style={{
              background: '#000000',
              border: '2px solid #000000',
              color: '#ffffff',
              padding: '10px 20px',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '600',
              borderRadius: '4px',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#333333';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#000000';
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
          </button>
        )}
      </div>
    </header>
  );
};