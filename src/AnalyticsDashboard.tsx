import React from 'react';

interface PostMetrics {
  total_posts: number;
  avg_score: number;
  median_score: number;
  total_upvotes: number;
  total_comments: number;
  avg_upvote_ratio: number;
}

interface EngagementAnalysis {
  total_comments_analyzed: number;
  avg_comments_per_post: number;
}

interface CommunityAnalysis {
  subreddits_involved: string[];
  primary_subreddit: string;
}

interface TemporalAnalysis {
  avg_age_days: number;
  freshness_score: number;
}

interface ContentAnalysis {
  unique_brands: number;
  total_brand_mentions: number;
}

interface Source {
  title: string;
  url: string;
  upvotes: number;
  subreddit: string;
  num_comments: number;
  upvote_ratio: number;
}

interface AnalyticsData {
  post_metrics: PostMetrics;
  engagement_analysis: EngagementAnalysis;
  community_analysis: CommunityAnalysis;
  temporal_analysis: TemporalAnalysis;
  content_analysis: ContentAnalysis;
}

interface AnalyticsDashboardProps {
  data: AnalyticsData;
  sources: Source[];
  isVisible: boolean;
}

const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
}> = ({ title, value, subtitle, color = '#3b82f6' }) => (
  <div style={{
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '20px',
    textAlign: 'center' as const,
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
  }}>
    <h3 style={{
      margin: '0 0 8px 0',
      fontSize: '14px',
      fontWeight: '500',
      color: '#6b7280',
      textTransform: 'uppercase' as const,
      letterSpacing: '0.5px'
    }}>
      {title}
    </h3>
    <div style={{
      fontSize: '32px',
      fontWeight: 'bold',
      color: color,
      marginBottom: '4px'
    }}>
      {value}
    </div>
    {subtitle && (
      <div style={{
        fontSize: '12px',
        color: '#9ca3af'
      }}>
        {subtitle}
      </div>
    )}
  </div>
);

const ProgressBar: React.FC<{
  percentage: number;
  color?: string;
  label: string;
}> = ({ percentage, color = '#3b82f6', label }) => (
  <div style={{ marginBottom: '16px' }}>
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      marginBottom: '8px',
      fontSize: '14px',
      fontWeight: '500',
      color: '#374151'
    }}>
      <span>{label}</span>
      <span>{percentage}%</span>
    </div>
    <div style={{
      width: '100%',
      backgroundColor: '#f3f4f6',
      borderRadius: '4px',
      height: '8px',
      overflow: 'hidden'
    }}>
      <div style={{
        width: `${Math.min(percentage, 100)}%`,
        height: '100%',
        backgroundColor: color,
        borderRadius: '4px',
        transition: 'width 0.3s ease'
      }} />
    </div>
  </div>
);

const SubredditChip: React.FC<{ subreddit: string; isPrimary?: boolean }> = ({ 
  subreddit, 
  isPrimary = false 
}) => (
  <span style={{
    display: 'inline-block',
    backgroundColor: isPrimary ? '#3b82f6' : '#f3f4f6',
    color: isPrimary ? '#ffffff' : '#374151',
    padding: '4px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '500',
    margin: '4px 4px 4px 0',
    border: '1px solid',
    borderColor: isPrimary ? '#3b82f6' : '#e5e7eb'
  }}>
    r/{subreddit}
    {isPrimary && ' ⭐'}
  </span>
);

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  data,
  sources,
  isVisible
}) => {
  if (!isVisible || !data) return null;

  const {
    post_metrics,
    engagement_analysis,
    community_analysis,
    temporal_analysis,
    content_analysis
  } = data;

  // Calculate derived metrics
  const engagementRate = post_metrics.total_comments / post_metrics.total_upvotes * 100;
  const qualityScore = (post_metrics.avg_upvote_ratio * 100);

  return (
    <div style={{
      backgroundColor: '#f9fafb',
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      padding: '24px',
      margin: '24px 0',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif'
    }}>
      <h2 style={{
        margin: '0 0 24px 0',
        fontSize: '24px',
        fontWeight: 'bold',
        color: '#111827',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        📊 Data Analytics
        <span style={{
          fontSize: '14px',
          fontWeight: 'normal',
          color: '#6b7280',
          backgroundColor: '#e5e7eb',
          padding: '4px 8px',
          borderRadius: '12px'
        }}>
          {post_metrics.total_posts} posts analyzed
        </span>
      </h2>

      {/* Key Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        marginBottom: '32px'
      }}>
        <MetricCard
          title="Total Engagement"
          value={post_metrics.total_upvotes + post_metrics.total_comments}
          subtitle={`${post_metrics.total_upvotes} upvotes, ${post_metrics.total_comments} comments`}
          color="#059669"
        />
        <MetricCard
          title="Avg Score"
          value={post_metrics.avg_score}
          subtitle={`Median: ${post_metrics.median_score}`}
          color="#dc2626"
        />
        <MetricCard
          title="Quality Score"
          value={`${qualityScore.toFixed(1)}%`}
          subtitle="Average upvote ratio"
          color="#7c3aed"
        />
        <MetricCard
          title="Discussion Level"
          value={engagement_analysis.avg_comments_per_post.toFixed(1)}
          subtitle="Comments per post"
          color="#ea580c"
        />
      </div>

      {/* Two Column Layout */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '24px'
      }}>
        
        {/* Left Column */}
        <div>
          {/* Community Analysis */}
          <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '24px'
          }}>
            <h3 style={{
              margin: '0 0 16px 0',
              fontSize: '18px',
              fontWeight: '600',
              color: '#111827'
            }}>
              🏘️ Community Distribution
            </h3>
            <div style={{ marginBottom: '16px' }}>
              {community_analysis.subreddits_involved.map((subreddit) => (
                <SubredditChip
                  key={subreddit}
                  subreddit={subreddit}
                  isPrimary={subreddit === community_analysis.primary_subreddit}
                />
              ))}
            </div>
            <div style={{
              fontSize: '14px',
              color: '#6b7280'
            }}>
              Primary community: <strong>r/{community_analysis.primary_subreddit}</strong>
            </div>
          </div>

          {/* Temporal Analysis */}
          <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '20px'
          }}>
            <h3 style={{
              margin: '0 0 16px 0',
              fontSize: '18px',
              fontWeight: '600',
              color: '#111827'
            }}>
              ⏰ Content Freshness
            </h3>
            <ProgressBar
              percentage={temporal_analysis.freshness_score}
              color="#22c55e"
              label="Recent Posts (< 30 days)"
            />
            <div style={{
              fontSize: '14px',
              color: '#6b7280',
              marginTop: '8px'
            }}>
              Average post age: <strong>{temporal_analysis.avg_age_days.toFixed(0)} days</strong>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div>
          {/* Top Posts */}
          <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '20px'
          }}>
            <h3 style={{
              margin: '0 0 16px 0',
              fontSize: '18px',
              fontWeight: '600',
              color: '#111827'
            }}>
              🏆 Top Performing Posts
            </h3>
            <div style={{ maxHeight: '300px', overflowY: 'auto' as const }}>
              {sources
                .sort((a, b) => b.upvotes - a.upvotes)
                .slice(0, 5)
                .map((source, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '12px',
                      borderBottom: '1px solid #f3f4f6',
                      marginBottom: '8px'
                    }}
                  >
                    <div style={{
                      fontSize: '14px',
                      fontWeight: '500',
                      color: '#111827',
                      marginBottom: '4px',
                      lineHeight: '1.4'
                    }}>
                      {source.title.length > 60
                        ? source.title.substring(0, 60) + '...'
                        : source.title
                      }
                    </div>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '12px',
                      color: '#6b7280'
                    }}>
                      <span>r/{source.subreddit}</span>
                      <div style={{ display: 'flex', gap: '12px' }}>
                        <span>👍 {source.upvotes}</span>
                        <span>💬 {source.num_comments}</span>
                        <span>{(source.upvote_ratio * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                ))
              }
            </div>
          </div>
        </div>
      </div>

      {/* Summary Stats Bar */}
      <div style={{
        marginTop: '24px',
        padding: '16px',
        backgroundColor: '#f3f4f6',
        borderRadius: '8px',
        display: 'flex',
        justifyContent: 'space-around',
        fontSize: '14px',
        color: '#374151'
      }}>
        <div style={{ textAlign: 'center' as const }}>
          <div style={{ fontWeight: '600', color: '#111827' }}>
            {((post_metrics.total_comments / post_metrics.total_upvotes) * 100).toFixed(1)}%
          </div>
          <div>Comments/Upvotes Ratio</div>
        </div>
        <div style={{ textAlign: 'center' as const }}>
          <div style={{ fontWeight: '600', color: '#111827' }}>
            {community_analysis.subreddits_involved.length}
          </div>
          <div>Communities Involved</div>
        </div>
        <div style={{ textAlign: 'center' as const }}>
          <div style={{ fontWeight: '600', color: '#111827' }}>
            {Math.round((post_metrics.avg_upvote_ratio) * 100)}%
          </div>
          <div>Average Quality Score</div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;