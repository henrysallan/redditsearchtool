import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { getUserSearchHistory, SearchHistoryItem } from './searchHistory';

interface SearchHistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSearch: (search: SearchHistoryItem) => void;
}

export const SearchHistorySidebar: React.FC<SearchHistorySidebarProps> = ({
  isOpen,
  onClose,
  onSelectSearch,
}) => {
  const { user } = useAuth();
  const [searchHistory, setSearchHistory] = useState<SearchHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && user) {
      loadSearchHistory();
    }
  }, [isOpen, user]);

  const loadSearchHistory = async () => {
    if (!user) return;
    
    setLoading(true);
    try {
      const history = await getUserSearchHistory(user.uid);
      setSearchHistory(history);
    } catch (error) {
      console.error('Error loading search history:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (date: Date) => {
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)} hours ago`;
    } else if (diffInHours < 24 * 7) {
      return `${Math.floor(diffInHours / 24)} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '400px',
      height: '100vh',
      backgroundColor: '#ffffff',
      borderRight: '2px solid #000000',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
      transition: 'transform 0.3s ease-in-out',
    }}>
      {/* Header */}
      <div style={{
        padding: '20px',
        borderBottom: '2px solid #000000',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#f8f9fa',
      }}>
        <h2 style={{
          margin: 0,
          fontSize: '1.25rem',
          fontWeight: '700',
          color: '#000000',
        }}>
          Search History
        </h2>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: '2px solid #000000',
            padding: '8px 12px',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: '600',
            transition: 'all 0.2s ease',
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
          ✕
        </button>
      </div>

      {/* Content */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '20px',
      }}>
        {loading ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '200px',
            color: '#666666',
          }}>
            Loading search history...
          </div>
        ) : searchHistory.length === 0 ? (
          <div style={{
            textAlign: 'center',
            color: '#666666',
            marginTop: '50px',
          }}>
            <p>No search history yet.</p>
            <p>Start by making your first search!</p>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}>
            {searchHistory.map((search) => (
              <div
                key={search.id}
                onClick={() => onSelectSearch(search)}
                style={{
                  border: '2px solid #e0e0e0',
                  padding: '16px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  backgroundColor: '#ffffff',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#000000';
                  e.currentTarget.style.backgroundColor = '#f8f9fa';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#e0e0e0';
                  e.currentTarget.style.backgroundColor = '#ffffff';
                }}
              >
                <div style={{
                  fontSize: '0.875rem',
                  color: '#666666',
                  marginBottom: '8px',
                }}>
                  {formatDate(search.timestamp)}
                </div>
                
                <div style={{
                  fontSize: '1rem',
                  fontWeight: '600',
                  color: '#000000',
                  marginBottom: '8px',
                }}>
                  {truncateText(search.query, 50)}
                </div>
                
                <div style={{
                  fontSize: '0.875rem',
                  color: '#666666',
                  marginBottom: '8px',
                  lineHeight: '1.4',
                }}>
                  {truncateText(search.summary, 100)}
                </div>
                
                <div style={{
                  display: 'flex',
                  gap: '8px',
                  fontSize: '0.75rem',
                  color: '#888888',
                }}>
                  <span style={{
                    padding: '2px 6px',
                    border: '1px solid #d0d0d0',
                    backgroundColor: '#f5f5f5',
                  }}>
                    {search.useWebSearch ? 'Web Search' : 'Reddit Only'}
                  </span>
                  <span style={{
                    padding: '2px 6px',
                    border: '1px solid #d0d0d0',
                    backgroundColor: '#f5f5f5',
                  }}>
                    {search.maxPosts} posts
                  </span>
                  {search.estimatedCost && (
                    <span style={{
                      padding: '2px 6px',
                      border: '1px solid #d0d0d0',
                      backgroundColor: '#f5f5f5',
                    }}>
                      ${search.estimatedCost.toFixed(4)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};