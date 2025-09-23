import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { AuthProvider, useAuth } from './AuthContext';
import { Header } from './Header';
import { SearchHistorySidebar } from './SearchHistorySidebar';
import { AnalyticsDashboard } from './AnalyticsDashboard';
import { SignInPromptModal } from './SignInPromptModal';
import { SearchProgressConsole } from './SearchProgressConsole';
import { SubscriptionPage } from './SubscriptionPage';
import { UnsubscribePage } from './UnsubscribePage';
import { apiCall } from './api';
import { saveSearchToHistory, getSearchById } from './searchHistory';
import { 
  checkUsageStatus, 
  recordSearch, 
  getUsageMessage,
  getUserTier,
  getAvailableModels,
  isModelAllowed,
  type UsageStatus,
  type UserTier
} from './usageTracking';

function AppContent() {
  const { user } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [maxPosts, setMaxPosts] = useState(10);
  const [model, setModel] = useState('gemini-1.5-flash');
  const [useWebSearch, setUseWebSearch] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [sources, setSources] = useState<any[]>([]);
  const [showAnalytics, setShowAnalytics] = useState(false);
  
  // Enhanced link discovery state
  const [enhancedLinks, setEnhancedLinks] = useState<Record<string, any[]>>({});
  const [extractedTerms, setExtractedTerms] = useState<string[]>([]);
  
  // Usage tracking state
  const [usageStatus, setUsageStatus] = useState<UsageStatus | null>(null);
  const [showSignInModal, setShowSignInModal] = useState(false);
  
  // Subscription state
  const [showSubscriptionPage, setShowSubscriptionPage] = useState(false);
  const [showUnsubscribePage, setShowUnsubscribePage] = useState(false);
  
  // Tier-based access control
  const [userTier, setUserTier] = useState<UserTier>('anonymous');
  const [availableModels, setAvailableModels] = useState(getAvailableModels('anonymous'));

  // Pro mode features
  const [analysisVerbosity, setAnalysisVerbosity] = useState(50); // 0-100 scale
  const [customPrompt, setCustomPrompt] = useState('');

  // Update user tier and available models when user changes
  useEffect(() => {
    const updateUserTier = async () => {
      const tier = await getUserTier(user);
      setUserTier(tier);
      setAvailableModels(getAvailableModels(tier));
      
      // Reset model to first available if current model is not allowed
      if (!isModelAllowed(model, tier)) {
        const models = getAvailableModels(tier);
        if (models.length > 0) {
          setModel(models[0].value);
        }
      }
    };
    
    updateUserTier();
  }, [user, model]);

  // Load usage status on component mount and when user changes
  useEffect(() => {
    const loadUsageStatus = async () => {
      try {
        const status = await checkUsageStatus(user?.uid);
        setUsageStatus(status);
      } catch (error) {
        console.error('Error loading usage status:', error);
      }
    };
    
    loadUsageStatus();
  }, [user]);

  // Restore search results from URL on page load
  useEffect(() => {
    const restoreSearchFromUrl = async () => {
      if (!user) return; // Only restore if user is signed in
      
      const urlParams = new URLSearchParams(window.location.search);
      const searchId = urlParams.get('search');
      
      // Handle Stripe success/cancel redirects
      const success = urlParams.get('success');
      const canceled = urlParams.get('canceled');
      const sessionId = urlParams.get('session_id');
      
      if (success === 'true') {
        console.log('🎉 Payment successful! Session ID:', sessionId);
        // Show success message and refresh user tier
        alert('🎉 Subscription successful! You now have access to all AI models.');
        // Update user tier to reflect new subscription
        const newTier = await getUserTier(user);
        setUserTier(newTier);
        // Clean up URL
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('success');
        newUrl.searchParams.delete('session_id');
        window.history.replaceState({}, '', newUrl.toString());
      } else if (canceled === 'true') {
        console.log('❌ Payment canceled');
        alert('Payment canceled. You can try again anytime.');
        // Clean up URL
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('canceled');
        window.history.replaceState({}, '', newUrl.toString());
      }
      
      if (searchId) {
        console.log('🔍 Restoring search from Firestore with ID:', searchId);
        try {
          const searchData = await getSearchById(user.uid, searchId);
          if (searchData) {
            console.log('✅ Successfully loaded search data from Firestore:', {
              query: searchData.query,
              hasAnalyticsData: !!searchData.analyticsData,
              hasEnhancedLinks: !!searchData.enhancedLinks && Object.keys(searchData.enhancedLinks).length > 0,
              hasExtractedTerms: !!searchData.extractedTerms && searchData.extractedTerms.length > 0,
              hasSources: !!searchData.sources && searchData.sources.length > 0,
              timestamp: searchData.timestamp,
              dataSource: 'Firestore'
            });
            
            // Restore all search state
            setSearchQuery(searchData.query);
            setSearchResults(searchData.summary);
            setMaxPosts(searchData.maxPosts);
            setModel(searchData.model);
            setUseWebSearch(searchData.useWebSearch || false);
            
            // Restore analytics and enhanced links
            if (searchData.analyticsData) {
              console.log('📊 Restoring analytics data from Firestore');
              setAnalyticsData(searchData.analyticsData);
            }
            if (searchData.enhancedLinks) {
              console.log('🔗 Restoring enhanced links from Firestore:', Object.keys(searchData.enhancedLinks));
              setEnhancedLinks(searchData.enhancedLinks);
            }
            if (searchData.extractedTerms) {
              console.log('📝 Restoring extracted terms from Firestore:', searchData.extractedTerms);
              setExtractedTerms(searchData.extractedTerms);
            }
            if (searchData.sources) {
              console.log('📰 Restoring sources from Firestore:', searchData.sources.length, 'sources');
              setSources(searchData.sources);
            }
          } else {
            console.warn('⚠️ No search data found in Firestore for ID:', searchId);
          }
        } catch (error) {
          console.error('❌ Error restoring search from Firestore:', error);
        }
      }
    };
    
    restoreSearchFromUrl();
  }, [user]); // Run when user changes (signs in)

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query');
      return;
    }

    // Validate model access for current user tier
    if (!isModelAllowed(model, userTier)) {
      if (userTier === 'anonymous') {
        setShowSignInModal(true);
        return;
      } else if (userTier === 'free') {
        setError('This model requires a paid subscription. Please upgrade your account.');
        return;
      }
    }

    // Check usage limits before proceeding
    if (!usageStatus) {
      setError('Unable to check usage status. Please try again.');
      return;
    }

    if (!usageStatus.canSearch) {
      if (!usageStatus.isAuthenticated) {
        setShowSignInModal(true);
        return;
      } else {
        setError('Daily search limit reached. Try again tomorrow!');
        return;
      }
    }

    setIsLoading(true);
    setError('');
    
    // Clear previous results immediately to ensure fresh data
    console.log('🧹 Clearing previous search state for fresh results');
    setSearchResults('');
    setAnalyticsData(null);
    setEnhancedLinks({});
    setExtractedTerms([]);
    setSources([]);
    setShowAnalytics(false);
    setSearchResults('');
    setEnhancedLinks({});
    setExtractedTerms([]);
    setAnalyticsData(null);
    setShowAnalytics(false);

    try {
      const response = await apiCall('/api/search-summarize', {
        method: 'POST',
        body: JSON.stringify({ 
          query: searchQuery,
          max_posts: maxPosts,
          model: model,
          use_web_search: false // Force to false until web search is implemented
        })
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }

      const data = await response.json();
      setSearchResults(data.summary || 'No results found');
      
      // Store enhanced links data
      if (data.enhanced_links) {
        setEnhancedLinks(data.enhanced_links);
      }
      if (data.extracted_search_terms) {
        setExtractedTerms(data.extracted_search_terms);
      }
      
      // Store analytics data and sources
      if (data.analysis) {
        setAnalyticsData(data.analysis);
        setShowAnalytics(true);
      }
      if (data.sources) {
        setSources(data.sources);
      }

      // Record search usage
      await recordSearch(user?.uid);
      
      // Update usage status after successful search
      const newUsageStatus = await checkUsageStatus(user?.uid);
      setUsageStatus(newUsageStatus);

      // Save search to history if user is signed in
      if (user) {
        const searchDataToSave = {
          query: searchQuery,
          maxPosts: maxPosts,
          model: model,
          useWebSearch: useWebSearch,
          summary: data.summary || 'No results',
          analyticsData: data.analysis,
          enhancedLinks: data.enhanced_links,
          extractedTerms: data.extracted_search_terms,
          sources: data.sources,
          searchMode: 'standard'
        };
        
        console.log('💾 Saving complete search data to Firestore:', {
          query: searchDataToSave.query,
          hasAnalyticsData: !!searchDataToSave.analyticsData,
          hasEnhancedLinks: !!searchDataToSave.enhancedLinks && Object.keys(searchDataToSave.enhancedLinks).length > 0,
          hasExtractedTerms: !!searchDataToSave.extractedTerms && searchDataToSave.extractedTerms.length > 0,
          hasSources: !!searchDataToSave.sources && searchDataToSave.sources.length > 0,
          dataSource: 'Fresh from API'
        });
        
        const searchId = await saveSearchToHistory(user.uid, searchDataToSave);
        
        console.log('✅ Search data saved to Firestore with ID:', searchId);
        
        // Update URL to include search ID for persistence
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.set('search', searchId);
        window.history.pushState(null, '', newUrl.toString());
      }

    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setIsLoading(false);
    }
  };

  // Function to clean up auto-generated titles from summary
  const cleanSummaryText = (text: string): string => {
    // Remove common auto-generated titles that appear at the start
    const titlePatterns = [
      /^# Reddit Data Analysis.*?(\n\n|\n)/i,
      /^# Analysis of.*?(\n\n|\n)/i,
      /^# Summary of.*?(\n\n|\n)/i,
      /^# Reddit Discussion.*?(\n\n|\n)/i,
      /^# .*?Analysis.*?(\n\n|\n)/i,
      /^## Reddit Data Analysis.*?(\n\n|\n)/i,
      /^## Analysis of.*?(\n\n|\n)/i,
      /^## Summary of.*?(\n\n|\n)/i,
      /^## Reddit Discussion.*?(\n\n|\n)/i,
      /^## .*?Analysis.*?(\n\n|\n)/i,
      // Also remove any line that starts with "Reddit Data Analysis" even without #
      /^Reddit Data Analysis.*?(\n\n|\n)/i,
      /^Analysis of.*?(\n\n|\n)/i,
      /^Summary of.*?(\n\n|\n)/i,
      /^Reddit Discussion.*?(\n\n|\n)/i,
    ];
    
    let cleanedText = text;
    titlePatterns.forEach(pattern => {
      cleanedText = cleanedText.replace(pattern, '');
    });
    
    // Also remove any leading whitespace after cleaning
    return cleanedText.trim();
  };

  // Enhanced text processing function for intelligent hyperlinking
  const enhanceTextWithLinks = (text: string): string => {
    if (!enhancedLinks || Object.keys(enhancedLinks).length === 0) {
      return text;
    }

    let enhancedText = text;
    
    // Process each term and its associated links
    Object.entries(enhancedLinks).forEach(([term, links]) => {
      if (Array.isArray(links) && links.length > 0) {
        // Create a more flexible regex that matches variations of the term
        const termVariations = [
          term,
          term.toLowerCase(),
          term.replace(/[^a-zA-Z0-9\s]/g, ''), // Remove special characters
          term.split(' ').join('\\s+'), // Allow flexible spacing
        ];
        
        // Create regex pattern that matches any variation
        const pattern = new RegExp(`\\b(${termVariations.join('|')})\\b`, 'gi');
        
        // Find the best link (highest relevance score)
        const bestLink = links.reduce((best, current) => {
          return (current.relevance_score || 0) > (best.relevance_score || 0) ? current : best;
        }, links[0]);
        
        // Replace first occurrence of the term with a link
        let hasReplaced = false;
        enhancedText = enhancedText.replace(pattern, (match) => {
          if (!hasReplaced) {
            hasReplaced = true;
            return `[${match}](${bestLink.url})`;
          }
          return match;
        });
      }
    });
    
    return enhancedText;
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Show subscription page if requested */}
      {showSubscriptionPage ? (
        <SubscriptionPage
          onBack={() => setShowSubscriptionPage(false)}
          user={user}
        />
      ) : showUnsubscribePage ? (
        <UnsubscribePage
          onBack={() => setShowUnsubscribePage(false)}
        />
      ) : (
        <>
          <Header
            sidebarOpen={sidebarOpen}
            onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
            usageStatus={usageStatus}
            onUpgrade={() => setShowSubscriptionPage(true)}
            onUnsubscribe={() => setShowUnsubscribePage(true)}
            userTier={userTier}
          />

      <SearchHistorySidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onSelectSearch={(search) => {
          console.log('📂 Selecting search from history:', {
            id: search.id,
            query: search.query,
            hasAnalyticsData: !!search.analyticsData,
            hasEnhancedLinks: !!search.enhancedLinks && Object.keys(search.enhancedLinks).length > 0,
            hasExtractedTerms: !!search.extractedTerms && search.extractedTerms.length > 0,
            hasSources: !!search.sources && search.sources.length > 0,
            dataSource: 'SearchHistory'
          });
          
          // Restore all search state completely
          setSearchQuery(search.query);
          setSearchResults(search.summary);
          setMaxPosts(search.maxPosts);
          setModel(search.model);
          setUseWebSearch(search.useWebSearch);
          
          // Restore analytics and enhanced data
          if (search.analyticsData) {
            console.log('📊 Restoring analytics data from history');
            setAnalyticsData(search.analyticsData);
          }
          if (search.enhancedLinks) {
            console.log('🔗 Restoring enhanced links from history:', Object.keys(search.enhancedLinks));
            setEnhancedLinks(search.enhancedLinks);
          }
          if (search.extractedTerms) {
            console.log('📝 Restoring extracted terms from history:', search.extractedTerms);
            setExtractedTerms(search.extractedTerms);
          }
          if (search.sources) {
            console.log('📰 Restoring sources from history:', search.sources.length, 'sources');
            setSources(search.sources);
          }
          
          // Update URL to match the search ID for proper persistence
          const newUrl = new URL(window.location.href);
          newUrl.searchParams.set('search', search.id);
          window.history.pushState(null, '', newUrl.toString());
          console.log('🔗 Updated URL with search ID:', search.id);
          
          setSidebarOpen(false);
        }}
      />

      <main className={`transition-all duration-300 ${sidebarOpen ? 'ml-80' : ''}`}>
        {/* Empty State */}
        {!searchResults && !isLoading && !error && (
          <section className="flex flex-col items-center justify-center min-h-[60vh] px-4">
            <div className="w-full max-w-2xl">
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div className="relative flex-1">
                  <input
                    type="text"
                    className="w-full px-4 py-4 pr-16 text-lg bg-transparent text-black outline-none"
                    style={{ border: '3px solid #000000' }}
                    placeholder="Search Reddit..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    disabled={isLoading}
                  />
                  <button
                    onClick={handleSearch}
                    disabled={!searchQuery.trim() || isLoading}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 bg-transparent text-black cursor-pointer hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-xl"
                    title="Search"
                  >
                    ⏵
                  </button>
                </div>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="px-4 py-4 bg-transparent text-black cursor-pointer text-lg hover:bg-black hover:text-white flex items-center justify-center"
                  style={{ border: '3px solid #000000', minWidth: '4rem' }}
                  title={showAdvanced ? 'Hide Options' : 'Show Options'}
                >
                  {showAdvanced ? '▲' : '▼'}
                </button>
              </div>

              {showAdvanced && (
                <div style={{ marginTop: '24px', background: 'white', padding: '20px', border: '3px solid #000000' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '24px', marginBottom: '20px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <label className="block text-base font-semibold text-black">AI Model</label>
                      <select
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        className="w-full px-3 py-3 bg-transparent text-black outline-none"
                        style={{ border: '3px solid #000000' }}
                      >
                        {availableModels.map((m) => (
                          <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                      </select>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <label className="block text-base font-semibold text-black">Max Posts</label>
                      <select
                        value={maxPosts}
                        onChange={(e) => setMaxPosts(parseInt(e.target.value))}
                        className="w-full px-3 py-3 bg-transparent text-black outline-none"
                        style={{ border: '3px solid #000000' }}
                      >
                        {[5,10,15,20,30].map(n => <option key={n} value={n}>{n} posts</option>)}
                      </select>
                    </div>
                  </div>
                  <label style={{ display: 'inline-flex', alignItems: 'center', gap: '12px' }} className="text-base font-semibold text-gray-400">
                    <input
                      type="checkbox"
                      checked={false}
                      onChange={(e) => {}} // Disabled for now
                      disabled={true}
                      className="w-4 h-4 opacity-50"
                      style={{ border: '3px solid #999999', borderRadius: '0' }}
                    />
                    Enable additional context (Coming Soon)
                  </label>
                </div>
              )}
            </div>
            
            {/* Description */}
            <div className="w-full max-w-2xl mt-12">
              <p className="text-black font-bold text-left">
                Reddit Search Tool helps you search entire reddit threads at once and then create clean AI generated summaries of them. Our tool is better than any chat bot alone. Give it a try!
              </p>
            </div>
          </section>
        )}

        {/* Loading Progress Console */}
        {isLoading && (
          <SearchProgressConsole
            isVisible={isLoading}
            searchQuery={searchQuery}
            maxPosts={maxPosts}
          />
        )}

        {/* Error */}
        {error && (
          <section className="max-w-2xl mx-auto mt-8 bg-white p-3" style={{ border: '3px solid #000000' }}>
            <h3 className="text-lg font-semibold text-black mb-2">Error</h3>
            <p className="text-black mb-4">{error}</p>
            <button 
              onClick={() => setError('')} 
              className="px-6 py-3 bg-transparent text-black cursor-pointer font-semibold hover:bg-black hover:text-white"
              style={{ border: '3px solid #000000' }}
            >
              Dismiss
            </button>
          </section>
        )}

        {/* Results - 2 Column Layout */}
        {searchResults && (
          <section className="w-full">
            {/* Header with New Search Button */}
            <div className="flex items-start justify-between mb-3">
              <h2 className="text-3xl font-bold text-black underline">{searchQuery}</h2>
              <button
                onClick={() => {
                  setSearchResults('');
                  setSearchQuery('');
                  setEnhancedLinks({});
                  setExtractedTerms([]);
                }}
                className="px-4 py-2 bg-transparent text-black cursor-pointer hover:bg-black hover:text-white font-bold"
                style={{ border: '3px solid #000000' }}
              >
                New Search
              </button>
            </div>

            {/* Two Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Column - Summary */}
              <div className="bg-white p-3" style={{ border: '3px solid #000000' }}>
                <h3 className="text-xl font-bold text-black mb-4">📝 Summary</h3>
                <div className="markdown-content max-w-none text-black">
                  <ReactMarkdown>{enhanceTextWithLinks(cleanSummaryText(searchResults))}</ReactMarkdown>
                </div>
              </div>

              {/* Right Column - Data & Links */}
              <div className="space-y-6">
                {/* Enhanced Links Section */}
                {enhancedLinks && Object.keys(enhancedLinks).length > 0 && (
                  <div className="bg-white p-3" style={{ border: '3px solid #000000' }}>
                    <h3 className="text-xl font-bold mb-4 text-black">🔗 Enhanced Links</h3>
                    <div className="space-y-4">
                      {Object.entries(enhancedLinks).map(([term, links]) => (
                        <div key={term} className="border-b border-gray-300 pb-3 last:border-b-0">
                          <h4 className="font-semibold text-lg mb-2 text-black">{term}</h4>
                          <div className="space-y-2">
                            {Array.isArray(links) && links.slice(0, 3).map((link: any, index: number) => (
                              <div key={index} className="bg-gray-50 p-3 border">
                                <a 
                                  href={link.url || link} 
                                  target="_blank" 
                                  rel="noopener noreferrer" 
                                  className="text-blue-600 hover:text-blue-800 font-medium block mb-1"
                                >
                                  {link.title || link.url || link}
                                </a>
                                {link.snippet && (
                                  <p className="text-gray-600 text-sm">{link.snippet}</p>
                                )}
                                {link.relevance_score && (
                                  <div className="text-xs text-gray-500 mt-1">
                                    Relevance: {Math.round(link.relevance_score * 100)}%
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Search Terms Section */}
                {extractedTerms && extractedTerms.length > 0 && (
                  <div className="bg-white p-3" style={{ border: '3px solid #000000' }}>
                    <h3 className="text-xl font-bold mb-4 text-black">📝 Extracted Search Terms</h3>
                    <div className="flex flex-wrap gap-2">
                      {extractedTerms.map((term: string, index: number) => (
                        <span 
                          key={index} 
                          className="inline-block bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700"
                          style={{ border: '2px solid #000000' }}
                        >
                          {term}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Analytics Dashboard */}
                {analyticsData && (
                  <div className="bg-white p-3" style={{ border: '3px solid #000000' }}>
                    <AnalyticsDashboard data={analyticsData as any} sources={sources} isVisible={!!analyticsData} />
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>

      <SignInPromptModal
        isOpen={showSignInModal}
        onClose={() => setShowSignInModal(false)}
        searchCount={usageStatus?.searchCount || 0}
        limit={usageStatus?.limit || 1}
      />
        </>
      )}
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
