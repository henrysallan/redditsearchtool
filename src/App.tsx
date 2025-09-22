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
        body: JSON.stringify({ query: searchQuery })
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
          maxPosts: 10,
          model: 'claude-3-5-sonnet',
          useWebSearch: true,
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
          setSidebarOpen(false);
        }}
      />
      
      <div style={{
        backgroundColor: '#ffffff',
        border: '2px solid #000000',
        borderRadius: '12px',
        padding: '32px',
        boxShadow: '4px 4px 0px #000000',
        maxWidth: '800px',
        margin: '40px auto',
        marginLeft: sidebarOpen ? '340px' : 'auto',
        transition: 'margin-left 0.3s ease'
      }}>
        <h1 style={{ 
          margin: '0 0 24px 0', 
          fontSize: '32px', 
          fontWeight: 'bold',
          color: '#000000'
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
              border: '2px solid #000000',
              borderRadius: '8px',
              marginBottom: '16px',
              fontFamily: 'inherit',
              backgroundColor: isLoading ? '#f3f4f6' : '#ffffff'
            }}
          />
          
          <button
            onClick={handleSearch}
            disabled={isLoading || !searchQuery.trim()}
            style={{
              backgroundColor: isLoading ? '#9ca3af' : '#000000',
              color: '#ffffff',
              border: 'none',
              padding: '16px 32px',
              fontSize: '16px',
              borderRadius: '8px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontWeight: 'bold',
              width: '100%'
            }}
          >
            {isLoading ? 'Searching...' : 'Search Reddit'}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div style={{
            backgroundColor: '#fee2e2',
            border: '2px solid #ef4444',
            borderRadius: '8px',
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
            color: '#22c55e',
            padding: '12px',
            backgroundColor: '#f0fdf4',
            border: '2px solid #22c55e',
            borderRadius: '8px'
          }}>
            ✅ Signed in as {user.displayName} - Your searches will be saved!
          </p>
        ) : (
          <p style={{ 
            margin: '0 0 24px 0', 
            fontSize: '14px', 
            color: '#f59e0b',
            padding: '12px',
            backgroundColor: '#fefbf2',
            border: '2px solid #f59e0b',
            borderRadius: '8px'
          }}>
            ⚠️ Sign in to save your search history
          </p>
        )}

        {/* Search Results */}
        {searchResults && (
          <div style={{
            backgroundColor: '#f8fafc',
            border: '2px solid #64748b',
            borderRadius: '8px',
            padding: '24px',
            marginTop: '24px'
          }}>
            <h2 style={{
              margin: '0 0 16px 0',
              fontSize: '20px',
              fontWeight: 'bold',
              color: '#000000'
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
