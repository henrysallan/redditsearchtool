import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { apiCall } from './api'

type ApiResponse = {
  summary: string
  sources: { 
    title: string; 
    url: string;
    upvotes?: number;
    subreddit?: string;
    num_comments?: number;
    upvote_ratio?: number;
    age_days?: number;
  }[]
  analysis?: {
    post_metrics: any;
    engagement_analysis: any;
    content_analysis: any;
    temporal_analysis: any;
    community_analysis: any;
    sentiment_indicators: any;
    // Web search mode specific fields
    agent_count?: number;
    success_rate?: number;
    coordinator_model?: string;
    search_method?: string;
  }
  // Search mode indicator
  search_mode?: 'traditional_reddit_search' | 'multi_agent_web_search'
  // Web search mode specific data
  agent_summary?: {
    total_searches: number;
    successful_searches: number;
    failed_searches: number;
  }
}

export default function App() {
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ApiResponse | null>(null)
  
  // New configuration state
  const [maxPosts, setMaxPosts] = useState(3)
  const [model, setModel] = useState('claude-3-5-sonnet-20241022')
  const [costEstimate, setCostEstimate] = useState<any>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // Web search mode state
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [agentCount, setAgentCount] = useState(3)
  const [coordinatorModel, setCoordinatorModel] = useState('claude-3-5-sonnet-20241022')

  const models = [
    { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', description: 'Fast & Affordable' },
    { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', description: 'Balanced Performance' },
    { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', description: 'Highest Quality' }
  ]

  // Update cost estimate when settings change
  React.useEffect(() => {
    const updateCostEstimate = async () => {
      try {
        const res = await apiCall('/api/estimate-cost', {
          method: 'POST',
          body: JSON.stringify({ 
            max_posts: maxPosts, 
            model, 
            use_web_search: useWebSearch,
            agent_count: agentCount,
            coordinator_model: coordinatorModel
          })
        })
        if (res.ok) {
          const estimate = await res.json()
          setCostEstimate(estimate)
        }
      } catch (err) {
        console.log('Failed to get cost estimate:', err)
      }
    }
    updateCostEstimate()
  }, [maxPosts, model, useWebSearch, agentCount, coordinatorModel])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await apiCall('/api/search-summarize', {
        method: 'POST',
        body: JSON.stringify({ 
          query: q,
          max_posts: maxPosts,
          model: model,
          use_web_search: useWebSearch,
          agent_count: agentCount,
          coordinator_model: coordinatorModel
        })
      })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg || `Request failed: ${res.status}`)
      }
      const data: ApiResponse = await res.json()
      setResult(data)
    } catch (err: any) {
      setError(err.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Add some global styles */}
      <style>{`
        * {
          box-sizing: border-box;
        }
        
        body {
          margin: 0;
          background: #0a0a0a;
          color: #ffffff;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
          line-height: 1.6;
        }
        
        .gradient-bg {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          background-size: 400% 400%;
          animation: gradient 15s ease infinite;
        }
        
        @keyframes gradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        
        .slide-up {
          animation: slideUp 0.6s ease-out;
        }
        
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .fade-in {
          animation: fadeIn 0.5s ease-out;
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        .pulse {
          animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        .loading-dots {
          display: inline-block;
        }
        
        .loading-dots::after {
          content: '';
          animation: dots 1.5s infinite;
        }
        
        @keyframes dots {
          0%, 20% { content: ''; }
          40% { content: '.'; }
          60% { content: '..'; }
          80%, 100% { content: '...'; }
        }
        
        .glassmorphism {
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .reddit-orange {
          color: #ff4500;
        }
        
        .hover-lift {
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .hover-lift:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
      `}</style>
      
      <div style={{ 
        minHeight: '100vh', 
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Animated background elements */}
        <div style={{
          position: 'absolute',
          top: '10%',
          left: '10%',
          width: '200px',
          height: '200px',
          background: 'linear-gradient(45deg, #ff6b6b, #4ecdc4)',
          borderRadius: '50%',
          opacity: 0.1,
          animation: 'gradient 8s ease infinite',
          filter: 'blur(40px)'
        }} />
        <div style={{
          position: 'absolute',
          top: '60%',
          right: '10%',
          width: '150px',
          height: '150px',
          background: 'linear-gradient(45deg, #a8edea, #fed6e3)',
          borderRadius: '50%',
          opacity: 0.1,
          animation: 'gradient 12s ease infinite',
          filter: 'blur(30px)'
        }} />
        
        <div style={{ 
          maxWidth: '1000px', 
          margin: '0 auto', 
          padding: '2rem 1rem',
          position: 'relative',
          zIndex: 1
        }}>
          {/* Header */}
          <div className="fade-in" style={{ textAlign: 'center', marginBottom: '3rem' }}>
            <h1 style={{ 
              fontSize: '4rem', 
              fontWeight: '800',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              marginBottom: '0.5rem',
              letterSpacing: '-0.02em'
            }}>
              Reddit Insights
            </h1>
            <p style={{ 
              fontSize: '1.25rem', 
              color: '#a0a0a0',
              margin: 0,
              fontWeight: '300'
            }}>
              AI-powered Reddit search and summarization
            </p>
          </div>

          {/* Search Form */}
          <form onSubmit={onSubmit} className="slide-up" style={{ 
            marginBottom: '3rem',
            animation: 'slideUp 0.6s ease-out 0.2s both'
          }}>
            <div style={{ 
              display: 'flex', 
              gap: '1rem',
              maxWidth: '600px',
              margin: '0 auto',
              marginBottom: '1rem'
            }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Ask anything about Reddit discussions..."
                  style={{ 
                    width: '100%',
                    padding: '1rem 1.5rem',
                    borderRadius: '16px',
                    border: 'none',
                    background: 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: 'blur(20px)',
                    color: '#ffffff',
                    fontSize: '1.1rem',
                    outline: 'none',
                    transition: 'all 0.3s ease'
                  }}
                  onFocus={(e) => {
                    e.target.style.background = 'rgba(255, 255, 255, 0.15)'
                    e.target.style.transform = 'scale(1.02)'
                  }}
                  onBlur={(e) => {
                    e.target.style.background = 'rgba(255, 255, 255, 0.1)'
                    e.target.style.transform = 'scale(1)'
                  }}
                />
              </div>
              <button 
                disabled={loading || !q.trim()} 
                className="hover-lift"
                style={{ 
                  padding: '1rem 2rem',
                  borderRadius: '16px',
                  border: 'none',
                  background: loading 
                    ? 'rgba(255, 255, 255, 0.1)' 
                    : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: '#ffffff',
                  fontSize: '1.1rem',
                  fontWeight: '600',
                  cursor: loading || !q.trim() ? 'not-allowed' : 'pointer',
                  opacity: loading || !q.trim() ? 0.5 : 1,
                  transition: 'all 0.3s ease',
                  minWidth: '120px'
                }}
              >
                {loading ? (
                  <span className="loading-dots">Searching</span>
                ) : (
                  '🔍 Search'
                )}
              </button>
            </div>

            {/* Advanced Configuration Toggle */}
            <div style={{ 
              textAlign: 'center',
              maxWidth: '600px',
              margin: '0 auto'
            }}>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#a0a0a0',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  padding: '0.5rem',
                  borderRadius: '8px',
                  transition: 'all 0.3s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#ffffff'
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#a0a0a0'
                  e.currentTarget.style.background = 'none'
                }}
              >
                {showAdvanced ? '▲ Hide Advanced Options' : '▼ Show Advanced Options'}
              </button>
            </div>

            {/* Advanced Configuration Panel */}
            {showAdvanced && (
              <div className="fade-in glassmorphism" style={{
                maxWidth: '600px',
                margin: '1rem auto 0',
                padding: '1.5rem',
                borderRadius: '16px',
                animation: 'fadeIn 0.3s ease-out'
              }}>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '1.5rem',
                  marginBottom: '1rem'
                }}>
                  {/* Posts Count */}
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: '0.9rem',
                      color: '#a0a0a0',
                      marginBottom: '0.5rem',
                      fontWeight: '500'
                    }}>
                      Posts to Analyze
                    </label>
                    <select
                      value={maxPosts}
                      onChange={(e) => setMaxPosts(parseInt(e.target.value))}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        background: 'rgba(255, 255, 255, 0.05)',
                        color: '#ffffff',
                        fontSize: '1rem',
                        outline: 'none'
                      }}
                    >
                      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(num => (
                        <option key={num} value={num} style={{ background: '#1a1a2e' }}>
                          {num} post{num !== 1 ? 's' : ''}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Model Selection */}
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: '0.9rem',
                      color: '#a0a0a0',
                      marginBottom: '0.5rem',
                      fontWeight: '500'
                    }}>
                      AI Model
                    </label>
                    <select
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.75rem',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        background: 'rgba(255, 255, 255, 0.05)',
                        color: '#ffffff',
                        fontSize: '1rem',
                        outline: 'none'
                      }}
                    >
                      {models.map(m => (
                        <option key={m.id} value={m.id} style={{ background: '#1a1a2e' }}>
                          {m.name} - {m.description}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Web Search Mode Toggle */}
                <div style={{
                  marginBottom: '1.5rem',
                  padding: '1rem',
                  borderRadius: '8px',
                  border: `1px solid ${useWebSearch ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255, 255, 255, 0.2)'}`,
                  background: useWebSearch ? 'rgba(34, 197, 94, 0.1)' : 'rgba(255, 255, 255, 0.05)'
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    marginBottom: useWebSearch ? '1rem' : '0'
                  }}>
                    <input
                      type="checkbox"
                      id="webSearchMode"
                      checked={useWebSearch}
                      onChange={(e) => setUseWebSearch(e.target.checked)}
                      style={{
                        width: '18px',
                        height: '18px',
                        marginRight: '0.75rem',
                        accentColor: '#22c55e'
                      }}
                    />
                    <label htmlFor="webSearchMode" style={{
                      fontSize: '1rem',
                      color: '#ffffff',
                      fontWeight: '500',
                      cursor: 'pointer',
                      flex: 1
                    }}>
                      🌐 Multi-Agent Web Search Mode
                    </label>
                    <span style={{
                      fontSize: '0.8rem',
                      color: useWebSearch ? '#22c55e' : '#a0a0a0',
                      fontWeight: '600',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      background: useWebSearch ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255, 255, 255, 0.1)'
                    }}>
                      {useWebSearch ? 'ENABLED' : 'DISABLED'}
                    </span>
                  </div>
                  
                  {useWebSearch && (
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '1rem',
                      paddingTop: '1rem',
                      borderTop: '1px solid rgba(34, 197, 94, 0.2)'
                    }}>
                      {/* Agent Count */}
                      <div>
                        <label style={{
                          display: 'block',
                          fontSize: '0.9rem',
                          color: '#a0a0a0',
                          marginBottom: '0.5rem',
                          fontWeight: '500'
                        }}>
                          Search Agents (Haiku)
                        </label>
                        <select
                          value={agentCount}
                          onChange={(e) => setAgentCount(parseInt(e.target.value))}
                          style={{
                            width: '100%',
                            padding: '0.75rem',
                            borderRadius: '8px',
                            border: '1px solid rgba(34, 197, 94, 0.3)',
                            background: 'rgba(34, 197, 94, 0.1)',
                            color: '#ffffff',
                            fontSize: '1rem',
                            outline: 'none'
                          }}
                        >
                          {[1, 2, 3, 4, 5].map(num => (
                            <option key={num} value={num} style={{ background: '#1a1a2e' }}>
                              {num} agent{num !== 1 ? 's' : ''}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Coordinator Model */}
                      <div>
                        <label style={{
                          display: 'block',
                          fontSize: '0.9rem',
                          color: '#a0a0a0',
                          marginBottom: '0.5rem',
                          fontWeight: '500'
                        }}>
                          Coordinator Model
                        </label>
                        <select
                          value={coordinatorModel}
                          onChange={(e) => setCoordinatorModel(e.target.value)}
                          style={{
                            width: '100%',
                            padding: '0.75rem',
                            borderRadius: '8px',
                            border: '1px solid rgba(34, 197, 94, 0.3)',
                            background: 'rgba(34, 197, 94, 0.1)',
                            color: '#ffffff',
                            fontSize: '1rem',
                            outline: 'none'
                          }}
                        >
                          {models.map(m => (
                            <option key={m.id} value={m.id} style={{ background: '#1a1a2e' }}>
                              {m.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}

                  {useWebSearch && (
                    <div style={{
                      marginTop: '1rem',
                      padding: '0.75rem',
                      borderRadius: '6px',
                      background: 'rgba(34, 197, 94, 0.1)',
                      border: '1px solid rgba(34, 197, 94, 0.2)',
                      fontSize: '0.85rem',
                      color: '#a0a0a0',
                      lineHeight: '1.4'
                    }}>
                      <strong style={{ color: '#22c55e' }}>How it works:</strong> {agentCount} Haiku agents will search the web in parallel for Reddit posts, then a {models.find(m => m.id === coordinatorModel)?.name} agent will synthesize all findings into a comprehensive analysis.
                    </div>
                  )}
                </div>

                {/* Cost Estimate */}
                {costEstimate && (
                  <div style={{
                    background: 'rgba(102, 126, 234, 0.1)',
                    borderRadius: '8px',
                    padding: '1rem',
                    border: '1px solid rgba(102, 126, 234, 0.2)'
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div>
                        <div style={{ fontSize: '0.9rem', color: '#a0a0a0' }}>
                          Estimated Cost
                        </div>
                        <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#667eea' }}>
                          ${costEstimate?.costs?.total?.toFixed(4) || '0.0000'}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                          ~{costEstimate?.estimated_tokens?.total?.toLocaleString() || '0'} tokens
                        </div>
                        {useWebSearch ? (
                          <div style={{ fontSize: '0.8rem', color: '#22c55e' }}>
                            {agentCount} agents + coordinator
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                            Reddit API: Free
                          </div>
                        )}
                        {useWebSearch && (
                          <div style={{ fontSize: '0.8rem', color: '#a0a0a0' }}>
                            Web search included
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </form>

          {/* Error State */}
          {error && (
            <div className="fade-in glassmorphism" style={{ 
              margin: '2rem auto',
              maxWidth: '600px',
              padding: '1.5rem',
              borderRadius: '16px',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              background: 'rgba(239, 68, 68, 0.1)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '1.5rem' }}>❌</span>
                <span style={{ color: '#fca5a5', fontWeight: '500' }}>
                  {error}
                </span>
              </div>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="slide-up" style={{ 
              animation: 'slideUp 0.6s ease-out',
              display: 'grid',
              gap: '2rem'
            }}>
              {/* Summary Card */}
              <div className="glassmorphism hover-lift" style={{ 
                borderRadius: '20px',
                padding: '2rem'
              }}>
                <h2 style={{ 
                  fontSize: '1.75rem',
                  marginBottom: '1.5rem',
                  color: '#ffffff',
                  fontWeight: '700',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem'
                }}>
                  <span>📋</span>
                  Summary
                </h2>
                <div style={{ 
                  fontSize: '1.1rem',
                  lineHeight: 1.7,
                  color: '#e0e0e0'
                }}>
                  <ReactMarkdown
                    components={{
                      p: ({children}) => <p style={{marginBottom: '1rem'}}>{children}</p>,
                      ul: ({children}) => <ul style={{paddingLeft: '1.5rem', marginBottom: '1rem'}}>{children}</ul>,
                      li: ({children}) => <li style={{marginBottom: '0.5rem'}}>{children}</li>,
                      strong: ({children}) => <strong style={{color: '#ffffff', fontWeight: '600'}}>{children}</strong>
                    }}
                  >
                    {result.summary}
                  </ReactMarkdown>
                </div>
              </div>

              {/* Data Insights Card - Traditional Search */}
              {result.analysis && result.search_mode === 'traditional_reddit_search' && result.analysis.post_metrics && (
                <div className="glassmorphism hover-lift" style={{ 
                  borderRadius: '20px',
                  padding: '2rem'
                }}>
                  <h3 style={{ 
                    fontSize: '1.5rem',
                    marginBottom: '1.5rem',
                    color: '#ffffff',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem'
                  }}>
                    <span>📊</span>
                    Data Insights
                  </h3>
                  
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '1.5rem',
                    marginBottom: '1.5rem'
                  }}>
                    {/* Engagement Metrics */}
                    <div style={{
                      background: 'rgba(102, 126, 234, 0.1)',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      border: '1px solid rgba(102, 126, 234, 0.2)'
                    }}>
                      <div style={{ fontSize: '0.9rem', color: '#a0a0a0', marginBottom: '0.5rem' }}>
                        Total Engagement
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#667eea' }}>
                        {result.analysis.post_metrics.total_upvotes?.toLocaleString()}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                        upvotes • {result.analysis.post_metrics.total_comments?.toLocaleString()} comments
                      </div>
                    </div>

                    {/* Community Consensus */}
                    <div style={{
                      background: 'rgba(34, 197, 94, 0.1)',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      border: '1px solid rgba(34, 197, 94, 0.2)'
                    }}>
                      <div style={{ fontSize: '0.9rem', color: '#a0a0a0', marginBottom: '0.5rem' }}>
                        Consensus Score
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#22c55e' }}>
                        {Math.round(result.analysis.post_metrics.avg_upvote_ratio * 100)}%
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                        average upvote ratio
                      </div>
                    </div>

                    {/* Content Freshness */}
                    <div style={{
                      background: 'rgba(245, 158, 11, 0.1)',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      border: '1px solid rgba(245, 158, 11, 0.2)'
                    }}>
                      <div style={{ fontSize: '0.9rem', color: '#a0a0a0', marginBottom: '0.5rem' }}>
                        Freshness
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#f59e0b' }}>
                        {result.analysis.temporal_analysis?.freshness_score}%
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                        recent content
                      </div>
                    </div>

                    {/* Sentiment */}
                    <div style={{
                      background: 'rgba(236, 72, 153, 0.1)',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      border: '1px solid rgba(236, 72, 153, 0.2)'
                    }}>
                      <div style={{ fontSize: '0.9rem', color: '#a0a0a0', marginBottom: '0.5rem' }}>
                        Sentiment
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#ec4899' }}>
                        {result.analysis.sentiment_indicators?.overall_sentiment}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                        ratio: {result.analysis.sentiment_indicators?.sentiment_ratio}
                      </div>
                    </div>
                  </div>

                  {/* Brand Analysis */}
                  {result.analysis.content_analysis?.top_brands?.length > 0 && (
                    <div style={{ marginBottom: '1.5rem' }}>
                      <h4 style={{ 
                        fontSize: '1.1rem', 
                        color: '#ffffff', 
                        marginBottom: '1rem',
                        fontWeight: '600'
                      }}>
                        Most Mentioned Brands
                      </h4>
                      <div style={{ 
                        display: 'flex', 
                        flexWrap: 'wrap', 
                        gap: '0.75rem' 
                      }}>
                        {result.analysis.content_analysis.top_brands.slice(0, 6).map(([brand, count]: [string, number], i: number) => (
                          <span
                            key={i}
                            style={{
                              background: 'rgba(255, 255, 255, 0.1)',
                              padding: '0.5rem 1rem',
                              borderRadius: '20px',
                              fontSize: '0.9rem',
                              color: '#ffffff',
                              border: '1px solid rgba(255, 255, 255, 0.2)'
                            }}
                          >
                            {brand} <span style={{ color: '#a0a0a0' }}>({count})</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Price Analysis */}
                  {result.analysis.content_analysis?.price_analysis?.prices_found > 0 && (
                    <div>
                      <h4 style={{ 
                        fontSize: '1.1rem', 
                        color: '#ffffff', 
                        marginBottom: '1rem',
                        fontWeight: '600'
                      }}>
                        Price Analysis
                      </h4>
                      <div style={{ 
                        display: 'grid', 
                        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                        gap: '1rem' 
                      }}>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#22c55e' }}>
                            ${result.analysis.content_analysis.price_analysis.avg_price}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#a0a0a0' }}>Average</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#667eea' }}>
                            ${result.analysis.content_analysis.price_analysis.median_price}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#a0a0a0' }}>Median</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#f59e0b' }}>
                            {result.analysis.content_analysis.price_analysis.price_range}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#a0a0a0' }}>Range</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Web Search Insights Card */}
              {result.analysis && result.search_mode === 'multi_agent_web_search' && (
                <div className="glassmorphism hover-lift" style={{ 
                  borderRadius: '20px',
                  padding: '2rem'
                }}>
                  <h3 style={{ 
                    fontSize: '1.5rem',
                    marginBottom: '1.5rem',
                    color: '#ffffff',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem'
                  }}>
                    <span>🌐</span>
                    Multi-Agent Search Analysis
                  </h3>
                  
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                    gap: '1.5rem',
                    marginBottom: '1.5rem'
                  }}>
                    {/* Agent Count */}
                    <div style={{
                      background: 'rgba(102, 126, 234, 0.1)',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      border: '1px solid rgba(102, 126, 234, 0.2)'
                    }}>
                      <div style={{ fontSize: '0.9rem', color: '#a0a0a0', marginBottom: '0.5rem' }}>
                        Search Agents
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#667eea' }}>
                        {result.analysis?.agent_count || 'N/A'}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                        parallel searches
                      </div>
                    </div>

                    {/* Success Rate */}
                    <div style={{
                      background: 'rgba(34, 197, 94, 0.1)',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      border: '1px solid rgba(34, 197, 94, 0.2)'
                    }}>
                      <div style={{ fontSize: '0.9rem', color: '#a0a0a0', marginBottom: '0.5rem' }}>
                        Success Rate
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#22c55e' }}>
                        {Math.round((result.analysis?.success_rate || 0) * 100)}%
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                        agent completion
                      </div>
                    </div>

                    {/* Search Method */}
                    <div style={{
                      background: 'rgba(245, 158, 11, 0.1)',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      border: '1px solid rgba(245, 158, 11, 0.2)'
                    }}>
                      <div style={{ fontSize: '0.9rem', color: '#a0a0a0', marginBottom: '0.5rem' }}>
                        Search Method
                      </div>
                      <div style={{ fontSize: '1.2rem', fontWeight: '700', color: '#f59e0b' }}>
                        Web Search
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                        with Claude API
                      </div>
                    </div>

                    {/* Coordinator Model */}
                    <div style={{
                      background: 'rgba(236, 72, 153, 0.1)',
                      borderRadius: '12px',
                      padding: '1.25rem',
                      border: '1px solid rgba(236, 72, 153, 0.2)'
                    }}>
                      <div style={{ fontSize: '0.9rem', color: '#a0a0a0', marginBottom: '0.5rem' }}>
                        Coordinator
                      </div>
                      <div style={{ fontSize: '1rem', fontWeight: '700', color: '#ec4899' }}>
                        {result.analysis?.coordinator_model?.replace('claude-3-5-', '').replace('-20241022', '') || 'N/A'}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#c0c0c0' }}>
                        analysis model
                      </div>
                    </div>
                  </div>

                  {/* Agent Summary Details */}
                  {result.agent_summary && (
                    <div style={{ marginBottom: '1rem' }}>
                      <h4 style={{ 
                        fontSize: '1.1rem', 
                        color: '#ffffff', 
                        marginBottom: '1rem',
                        fontWeight: '600'
                      }}>
                        Agent Search Summary
                      </h4>
                      <div style={{
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '8px',
                        padding: '1rem',
                        border: '1px solid rgba(255, 255, 255, 0.1)'
                      }}>
                        <div style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.5' }}>
                          Total searches: {result.agent_summary.total_searches || 0} • 
                          Successful: {result.agent_summary.successful_searches || 0} • 
                          Failed: {result.agent_summary.failed_searches || 0}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Sources Card */}
              {result.sources?.length > 0 && (
                <div className="glassmorphism hover-lift" style={{ 
                  borderRadius: '20px',
                  padding: '2rem'
                }}>
                  <h3 style={{ 
                    fontSize: '1.5rem',
                    marginBottom: '1.5rem',
                    color: '#ffffff',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem'
                  }}>
                    <span className="reddit-orange">🔗</span>
                    Sources
                  </h3>
                  <div style={{ display: 'grid', gap: '1rem' }}>
                    {result.sources.map((source, i) => (
                      <a
                        key={i}
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="hover-lift"
                        style={{
                          textDecoration: 'none',
                          display: 'block',
                          padding: '1.25rem',
                          borderRadius: '12px',
                          background: 'rgba(255, 255, 255, 0.05)',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                          e.currentTarget.style.borderColor = 'rgba(102, 126, 234, 0.5)'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        }}
                      >
                        <div style={{ 
                          fontSize: '1.1rem',
                          fontWeight: '600',
                          color: '#ffffff',
                          marginBottom: '0.5rem',
                          lineHeight: 1.4
                        }}>
                          {source.title}
                        </div>
                        <div style={{ 
                          display: 'flex',
                          alignItems: 'center',
                          gap: '1rem',
                          fontSize: '0.9rem',
                          color: '#a0a0a0',
                          flexWrap: 'wrap'
                        }}>
                          {source.subreddit && (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <span className="reddit-orange">r/</span>
                              {source.subreddit}
                            </span>
                          )}
                          {source.upvotes !== undefined && (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <span>👍</span>
                              {source.upvotes.toLocaleString()}
                            </span>
                          )}
                          {source.num_comments !== undefined && (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <span>💬</span>
                              {source.num_comments.toLocaleString()}
                            </span>
                          )}
                          {source.upvote_ratio !== undefined && (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <span>📊</span>
                              {Math.round(source.upvote_ratio * 100)}%
                            </span>
                          )}
                          {source.age_days !== undefined && (
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <span>⏰</span>
                              {source.age_days < 1 ? '<1 day' : 
                               source.age_days < 30 ? `${Math.round(source.age_days)} days` :
                               source.age_days < 365 ? `${Math.round(source.age_days/30)} months` :
                               `${Math.round(source.age_days/365)} years`}
                            </span>
                          )}
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
