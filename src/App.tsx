import React, { useState } from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import { Header } from './Header';
import { SearchHistorySidebar } from './SearchHistorySidebar';
import { apiCall } from './api';
import { saveSearchToHistory } from './searchHistory';

function AppContent() {
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [maxPosts, setMaxPosts] = useState(10);
  const [model, setModel] = useState('claude-3-5-sonnet-20241022');
  const [useWebSearch, setUseWebSearch] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query');
      return;
    }

    setIsLoading(true);
    setError('');
    setSearchResults('');

    try {
      const response = await apiCall('/api/search-summarize', {
        method: 'POST',
        body: JSON.stringify({ 
          query: searchQuery,
          max_posts: maxPosts,
          model: model,
          web_search_mode: useWebSearch
        })
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }

      const data = await response.json();
      setSearchResults(data.summary || 'No results found');

      // Save search to history if user is signed in
      if (user) {
        await saveSearchToHistory(user.uid, {
          query: searchQuery,
          maxPosts: maxPosts,
          model: model,
          useWebSearch: useWebSearch,
          summary: data.summary || 'No results',
          searchMode: 'standard'
        });
      }

    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      backgroundColor: '#f8fafc',
      minHeight: '100vh',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif'
    }}>
      <Header 
        sidebarOpen={sidebarOpen} 
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} 
      />
      
      <SearchHistorySidebar 
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSelectSearch={(search) => {
          setSearchQuery(search.query);
          setSearchResults(search.summary);
          setMaxPosts(search.maxPosts);
          setModel(search.model);
          setUseWebSearch(search.useWebSearch);
          setSidebarOpen(false);
        }}
      />
      
      <div style={{
        backgroundColor: '#ffffff',
        border: '1px solid #d1d5db',
        borderRadius: '8px',
        padding: '32px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        maxWidth: '800px',
        margin: '40px auto',
        marginLeft: sidebarOpen ? '340px' : 'auto',
        transition: 'margin-left 0.3s ease'
      }}>
        <h1 style={{ 
          margin: '0 0 24px 0', 
          fontSize: '32px', 
          fontWeight: 'bold',
          color: '#111827'
        }}>
          Reddit Search Tool
        </h1>

        {/* Search Input */}
        <div style={{ marginBottom: '24px' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Enter your search query..."
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '16px',
              fontSize: '16px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              marginBottom: '16px',
              fontFamily: 'inherit',
              backgroundColor: isLoading ? '#f9fafb' : '#ffffff',
              outline: 'none',
              transition: 'border-color 0.15s ease',
              boxSizing: 'border-box'
            }}
            onFocus={(e) => e.target.style.borderColor = '#3b82f6'}
            onBlur={(e) => e.target.style.borderColor = '#d1d5db'}
          />
          
          {/* Advanced Options Toggle */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{
              backgroundColor: 'transparent',
              color: '#6b7280',
              border: '1px solid #d1d5db',
              padding: '8px 16px',
              fontSize: '14px',
              borderRadius: '6px',
              cursor: 'pointer',
              marginBottom: '16px',
              fontWeight: '500'
            }}
          >
            {showAdvanced ? '↑ Hide' : '↓ Show'} Advanced Options
          </button>

          {/* Advanced Options */}
          {showAdvanced && (
            <div style={{
              backgroundColor: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              padding: '20px',
              marginBottom: '16px'
            }}>
              <div style={{ 
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
                marginBottom: '16px'
              }}>
                {/* Model Selection */}
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    color: '#374151',
                    marginBottom: '8px'
                  }}>
                    AI Model
                  </label>
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      fontSize: '14px',
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      backgroundColor: '#ffffff',
                      color: '#374151'
                    }}
                  >
                    <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                    <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="gpt-4o-mini">GPT-4o Mini</option>
                  </select>
                </div>

                {/* Max Posts */}
                <div>
                  <label style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    color: '#374151',
                    marginBottom: '8px'
                  }}>
                    Max Posts
                  </label>
                  <select
                    value={maxPosts}
                    onChange={(e) => setMaxPosts(parseInt(e.target.value))}
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      fontSize: '14px',
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      backgroundColor: '#ffffff',
                      color: '#374151'
                    }}
                  >
                    <option value={5}>5 posts</option>
                    <option value={10}>10 posts</option>
                    <option value={15}>15 posts</option>
                    <option value={20}>20 posts</option>
                    <option value={30}>30 posts</option>
                  </select>
                </div>
              </div>

              {/* Web Search Toggle */}
              <div>
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#374151',
                  cursor: 'pointer'
                }}>
                  <input
                    type="checkbox"
                    checked={useWebSearch}
                    onChange={(e) => setUseWebSearch(e.target.checked)}
                    style={{
                      marginRight: '8px',
                      width: '16px',
                      height: '16px'
                    }}
                  />
                  Enable web search for additional context
                </label>
              </div>
            </div>
          )}
          
          <button
            onClick={handleSearch}
            disabled={isLoading || !searchQuery.trim()}
            style={{
              backgroundColor: isLoading ? '#9ca3af' : '#3b82f6',
              color: '#ffffff',
              border: 'none',
              padding: '16px 32px',
              fontSize: '16px',
              borderRadius: '6px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontWeight: '600',
              width: '100%',
              transition: 'background-color 0.15s ease'
            }}
          >
            {isLoading ? 'Searching...' : 'Search Reddit'}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fca5a5',
            borderRadius: '6px',
            padding: '16px',
            marginBottom: '24px',
            color: '#dc2626'
          }}>
            {error}
          </div>
        )}

        {/* User Status */}
        {user ? (
          <p style={{ 
            margin: '0 0 24px 0', 
            fontSize: '14px', 
            color: '#059669',
            padding: '12px',
            backgroundColor: '#f0fdf4',
            border: '1px solid #a7f3d0',
            borderRadius: '6px'
          }}>
            ✅ Signed in as {user.displayName} - Your searches will be saved!
          </p>
        ) : (
          <p style={{ 
            margin: '0 0 24px 0', 
            fontSize: '14px', 
            color: '#d97706',
            padding: '12px',
            backgroundColor: '#fffbeb',
            border: '1px solid #fcd34d',
            borderRadius: '6px'
          }}>
            ⚠️ Sign in to save your search history
          </p>
        )}

        {/* Search Results */}
        {searchResults && (
          <div style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #cbd5e1',
            borderRadius: '6px',
            padding: '24px',
            marginTop: '24px'
          }}>
            <h2 style={{
              margin: '0 0 16px 0',
              fontSize: '20px',
              fontWeight: '600',
              color: '#111827'
            }}>
              Search Results
            </h2>
            <div style={{
              fontSize: '16px',
              lineHeight: '1.6',
              color: '#374151',
              whiteSpace: 'pre-wrap'
            }}>
              {searchResults}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
