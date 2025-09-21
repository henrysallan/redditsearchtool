from firebase_functions import https_fn
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import praw
import anthropic
import os
import json
import logging
import time
import uuid
import traceback
import requests
import re
from datetime import datetime, timezone
from collections import Counter
import statistics

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("functions")

@app.before_request
def _before_request():
    request._start_time = time.time()
    request._req_id = str(uuid.uuid4())
    logger.info(
        json.dumps({
            "event": "request_start",
            "id": request._req_id,
            "method": request.method,
            "path": request.path,
            "remote_addr": request.headers.get('X-Forwarded-For', request.remote_addr),
            "user_agent": request.headers.get('User-Agent')
        })
    )

@app.after_request
def _after_request(response):
    try:
        duration_ms = int((time.time() - getattr(request, "_start_time", time.time())) * 1000)
        logger.info(
            json.dumps({
                "event": "request_end",
                "id": getattr(request, "_req_id", "n/a"),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            })
        )
    except Exception:
        pass
    return response

@app.route('/api/estimate-cost', methods=['POST'])
@app.route('/estimate-cost', methods=['POST'])
def estimate_cost():
    """Estimate the cost of a search request"""
    data = request.get_json(silent=True) or {}
    logger.info(json.dumps({
        "event": "estimate_cost_params",
        "id": getattr(request, "_req_id", "n/a"),
        "keys": list(data.keys()),
    }))
    max_posts = data.get('max_posts', 3)
    model = data.get('model', 'claude-3-5-sonnet-20241022')
    
    # New web search mode parameters
    use_web_search = data.get('use_web_search', False)
    agent_count = data.get('agent_count', 3)
    coordinator_model = data.get('coordinator_model', 'claude-3-5-sonnet-20241022')
    
    # Claude pricing (as of 2024) - per million tokens
    claude_pricing = {
        'claude-3-5-haiku-20241022': {'input': 0.25, 'output': 1.25},      # Haiku
        'claude-3-5-sonnet-20241022': {'input': 3.00, 'output': 15.00},    # Sonnet
        'claude-3-opus-20240229': {'input': 15.00, 'output': 75.00}        # Opus
    }
    
    if use_web_search:
        # Multi-agent web search cost estimation
        agent_input_tokens = agent_count * 1000
        agent_output_tokens = agent_count * 500
        coordinator_input_tokens = 3000
        coordinator_output_tokens = 1000
        
        # Calculate agent costs (all agents use Haiku)
        agent_pricing = claude_pricing['claude-3-5-haiku-20241022']
        agent_input_cost = (agent_input_tokens / 1_000_000) * agent_pricing['input']
        agent_output_cost = (agent_output_tokens / 1_000_000) * agent_pricing['output']
        
        # Calculate coordinator costs
        coordinator_pricing = claude_pricing.get(coordinator_model, claude_pricing['claude-3-5-sonnet-20241022'])
        coordinator_input_cost = (coordinator_input_tokens / 1_000_000) * coordinator_pricing['input']
        coordinator_output_cost = (coordinator_output_tokens / 1_000_000) * coordinator_pricing['output']
        
        total_cost = agent_input_cost + agent_output_cost + coordinator_input_cost + coordinator_output_cost
        
        return jsonify({
            'estimated_cost': round(total_cost, 4),
            'breakdown': {
                'agents_cost': round(agent_input_cost + agent_output_cost, 4),
                'coordinator_cost': round(coordinator_input_cost + coordinator_output_cost, 4),
                'total': round(total_cost, 4)
            },
            'agent_count': agent_count,
            'coordinator_model': coordinator_model,
            'agent_model': 'claude-3-5-haiku-20241022'
        })
    
    else:
        # Traditional Reddit search cost estimation
        estimated_input_tokens = max_posts * (300 + 5 * 50) + 500
        estimated_output_tokens = 400
        
        pricing = claude_pricing.get(model, claude_pricing['claude-3-5-sonnet-20241022'])
        
        input_cost = (estimated_input_tokens / 1_000_000) * pricing['input']
        output_cost = (estimated_output_tokens / 1_000_000) * pricing['output']
        total_cost = input_cost + output_cost
        
        return jsonify({
            'estimated_cost': round(total_cost, 4),
            'breakdown': {
                'input_tokens': estimated_input_tokens,
                'output_tokens': estimated_output_tokens,
                'input_cost': round(input_cost, 4),
                'output_cost': round(output_cost, 4),
                'total': round(total_cost, 4)
            },
            'model': model
        })

@app.route('/api/search-summarize', methods=['POST'])
@app.route('/search-summarize', methods=['POST'])
def search_summarize():
    """Search Reddit and summarize using Anthropic API"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info(json.dumps({
            "event": "search_summarize_params",
            "id": getattr(request, "_req_id", "n/a"),
            "keys": list(data.keys()),
            "content_length": request.headers.get('Content-Length')
        }))
        
        query = data.get('query')
        max_posts = data.get('max_posts', 3)
        model = data.get('model', 'claude-3-5-sonnet-20241022')
        
        # New web search mode parameters
        use_web_search = data.get('use_web_search', False)
        agent_count = data.get('agent_count', 3)
        coordinator_model = data.get('coordinator_model', 'claude-3-5-sonnet-20241022')

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Validate max_posts
        if not isinstance(max_posts, int) or max_posts < 1 or max_posts > 10:
            return jsonify({'error': 'max_posts must be between 1 and 10'}), 400

        # Validate agent_count
        if not isinstance(agent_count, int) or agent_count < 1 or agent_count > 5:
            return jsonify({'error': 'agent_count must be between 1 and 5'}), 400

        # Validate models
        valid_models = [
            'claude-3-5-haiku-20241022',
            'claude-3-5-sonnet-20241022', 
            'claude-3-opus-20240229'
        ]
        if model not in valid_models:
            return jsonify({'error': f'Invalid model. Must be one of: {valid_models}'}), 400
        if coordinator_model not in valid_models:
            return jsonify({'error': f'Invalid coordinator_model. Must be one of: {valid_models}'}), 400

        logger.info(json.dumps({
            "event": "search_request",
            "id": getattr(request, "_req_id", "n/a"),
            "query": query,
            "max_posts": max_posts,
            "model": model,
            "use_web_search": use_web_search
        }))

        if use_web_search:
            # TODO: Implement multi-agent web search mode  
            logger.warning(json.dumps({
                "event": "feature_not_implemented",
                "id": getattr(request, "_req_id", "n/a"),
                "feature": "multi_agent_web_search"
            }))
            return jsonify({
                'error': 'Web search mode not yet implemented in Firebase Functions',
                'fallback': 'traditional_reddit_search'
            }), 501
        else:
            # Traditional Reddit search mode
            return handle_traditional_search_mode(query, max_posts, model)
            
    except Exception as e:
        logger.error(json.dumps({
            "event": "error",
            "id": getattr(request, "_req_id", "n/a"),
            "path": request.path,
            "message": str(e),
            "trace": traceback.format_exc()
        }))
        return jsonify({
            'error': 'Search failed',
            'details': str(e),
            'request_id': getattr(request, "_req_id", "n/a"),
            'env_present': {
                'ANTHROPIC_API_KEY': bool(os.environ.get('ANTHROPIC_API_KEY')),
                'REDDIT_CLIENT_ID': bool(os.environ.get('REDDIT_CLIENT_ID')),
                'REDDIT_CLIENT_SECRET': bool(os.environ.get('REDDIT_CLIENT_SECRET')),
                'REDDIT_USER_AGENT': bool(os.environ.get('REDDIT_USER_AGENT')),
            }
        }), 500

def handle_traditional_search_mode(query: str, max_posts: int, model: str):
    """Handle traditional Reddit search mode"""
    try:
        # Reddit API setup
        reddit = praw.Reddit(
            client_id=os.environ.get("REDDIT_CLIENT_ID"),
            client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
            user_agent=os.environ.get("REDDIT_USER_AGENT"),
        )

        logger.info(json.dumps({
            "event": "reddit_search_start",
            "id": getattr(request, "_req_id", "n/a"),
            "query": query
        }))

        # For Firebase Functions, we'll use a simplified search approach
        # Try multiple Reddit search strategies
        reddit_urls = []
        
        # Strategy 1: Direct Reddit search in popular subreddits
        try:
            search_subreddits = ["all", "AskReddit", "technology", "BuyItForLife", "reviews"]
            for sub_name in search_subreddits:
                try:
                    subreddit = reddit.subreddit(sub_name)
                    submissions = list(subreddit.search(query, sort="relevance", limit=max_posts))
                    if submissions:
                        reddit_urls.extend([f"https://reddit.com{sub.permalink}" for sub in submissions])
                        break  # Found results, stop searching other subreddits
                except Exception as sub_error:
                    logger.warning(json.dumps({
                        "event": "subreddit_search_error",
                        "id": getattr(request, "_req_id", "n/a"),
                        "subreddit": sub_name,
                        "error": str(sub_error)
                    }))
                    continue
                    
            logger.info(json.dumps({
                "event": "reddit_direct_search",
                "id": getattr(request, "_req_id", "n/a"),
                "found_count": len(reddit_urls)
            }))
        except Exception as e:
            logger.error(json.dumps({
                "event": "reddit_search_error",
                "id": getattr(request, "_req_id", "n/a"),
                "error": str(e)
            }))

        # Fallback to Google search if direct Reddit search fails
        if not reddit_urls:
            logger.info(json.dumps({
                "event": "fallback_google_search",
                "id": getattr(request, "_req_id", "n/a")
            }))
            reddit_urls = search_google_for_reddit_posts(query, num_results=max_posts * 2)

        if not reddit_urls:
            logger.warning(json.dumps({
                "event": "no_posts_found",
                "id": getattr(request, "_req_id", "n/a"),
                "query": query
            }))
            return jsonify({'error': 'No Reddit posts found for the given query.'}), 404

        # Get Reddit post objects from URLs
        submissions = []
        for url in reddit_urls:
            post = get_reddit_post_from_url(reddit, url)
            if post:
                submissions.append(post)
            if len(submissions) >= max_posts:
                break

        if not submissions:
            return jsonify({'error': 'Could not retrieve Reddit posts from found URLs.'}), 404

        logger.info(json.dumps({
            "event": "posts_retrieved",
            "id": getattr(request, "_req_id", "n/a"),
            "post_count": len(submissions)
        }))

        # Perform data analysis
        analysis = analyze_reddit_data(submissions, query)

        # Extract text from posts and comments  
        full_text = ""
        sources = []
        for submission in submissions:
            sources.append({
                'title': submission.title,
                'url': submission.url,
                'upvotes': submission.score,
                'subreddit': str(submission.subreddit),
                'num_comments': submission.num_comments,
                'upvote_ratio': submission.upvote_ratio
            })

            full_text += f"Title: {submission.title} (👍 {submission.score} upvotes, 💬 {submission.num_comments} comments)\n"
            if submission.selftext:
                full_text += f"Post: {submission.selftext[:1000]}\n"

            submission.comments.replace_more(limit=0)
            comments_text = ""
            comment_count = 0

            # Get top comments
            sorted_comments = sorted(submission.comments.list(), key=lambda x: x.score, reverse=True)
            for comment in sorted_comments:
                if comment_count >= 5:
                    break
                comments_text += f"Comment (👍 {comment.score}): {comment.body[:200]}\n"
                comment_count += 1

            full_text += f"Top Comments:\n{comments_text}\n\n"

        # Limit text length
        if len(full_text) > 8000:
            full_text = full_text[:8000] + "...\n[Text truncated to stay within API limits]"

        # Anthropic API setup
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        # Create comprehensive prompt
        prompt = f"""Please analyze the following Reddit data about '{query}' and provide a comprehensive summary.

=== DATA ANALYSIS ===
Post Metrics:
- Total posts analyzed: {analysis['post_metrics']['total_posts']}
- Average upvotes: {analysis['post_metrics']['avg_score']}
- Total engagement: {analysis['post_metrics']['total_upvotes']} upvotes, {analysis['post_metrics']['total_comments']} comments

Based on this analysis and the content below, provide:
1. **SUMMARY**: Main findings and recommendations
2. **TOP RECOMMENDATIONS**: Specific products/brands with community consensus  
3. **COMMUNITY CONSENSUS**: What the Reddit community agrees on

=== RAW CONTENT ===
{full_text}"""

        # Get summary from Claude with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                message = client.messages.create(
                    model=model,
                    max_tokens=1500,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                ).content[0].text
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(json.dumps({
                        "event": "anthropic_error",
                        "id": getattr(request, "_req_id", "n/a"),
                        "error": str(e),
                        "attempt": attempt + 1
                    }))
                    return jsonify({'error': f'API error: {str(e)}'}), 500
                
                # Wait before retry
                wait_time = (2 ** attempt) + 0.5
                logger.warning(json.dumps({
                    "event": "anthropic_retry",
                    "id": getattr(request, "_req_id", "n/a"),
                    "attempt": attempt + 1,
                    "wait_time": wait_time
                }))
                time.sleep(wait_time)

        logger.info(json.dumps({
            "event": "search_completed",
            "id": getattr(request, "_req_id", "n/a"),
            "post_count": len(submissions),
            "sources_count": len(sources)
        }))

        return jsonify({
            'summary': message,
            'sources': sources,
            'analysis': analysis,
            'search_mode': 'traditional_reddit_search'
        })

    except Exception as e:
        logger.error(json.dumps({
            "event": "traditional_search_error",
            "id": getattr(request, "_req_id", "n/a"),
            "error": str(e),
            "trace": traceback.format_exc()
        }))
        return jsonify({'error': f'Traditional search failed: {str(e)}'}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test Reddit API connection
        reddit_status = "unknown"
        try:
            reddit = praw.Reddit(
                client_id=os.environ.get("REDDIT_CLIENT_ID"),
                client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
                user_agent=os.environ.get("REDDIT_USER_AGENT"),
            )
            # Try to access Reddit API
            subreddit = reddit.subreddit("test")
            _ = subreddit.display_name  # This will trigger API call
            reddit_status = "connected"
        except Exception as e:
            reddit_status = f"error: {str(e)}"
            
        return jsonify({
            'status': 'healthy',
            'message': 'Firebase Functions backend is running',
            'timestamp': int(time.time()),
            'version': '1.0.0',
            'region': 'local',
            'env_present': {
                'ANTHROPIC_API_KEY': bool(os.environ.get('ANTHROPIC_API_KEY')),
                'REDDIT_CLIENT_ID': bool(os.environ.get('REDDIT_CLIENT_ID')),
                'REDDIT_CLIENT_SECRET': bool(os.environ.get('REDDIT_CLIENT_SECRET')),
                'REDDIT_USER_AGENT': bool(os.environ.get('REDDIT_USER_AGENT')),
            },
            'reddit_api_status': reddit_status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': int(time.time())
        }), 500

def search_google_for_reddit_posts(query, num_results=5):
    """Search Google for Reddit posts related to the query"""
    try:
        import requests
        from urllib.parse import quote
        
        search_query = f"site:reddit.com {query}"
        encoded_query = quote(search_query)
        
        # Using Google Custom Search API or basic search
        # For Firebase Functions, we'll use a simple approach
        url = f"https://www.google.com/search?q={encoded_query}&num={num_results}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Basic URL extraction (simplified for Firebase Functions)
        import re
        reddit_urls = re.findall(r'https://(?:www\.)?reddit\.com/r/[^/]+/comments/[^/]+/[^"\s]*', response.text)
        
        # Clean and deduplicate URLs
        clean_urls = []
        seen = set()
        for url in reddit_urls:
            if url not in seen and len(clean_urls) < num_results:
                clean_urls.append(url)
                seen.add(url)
        
        logger.info(json.dumps({
            "event": "google_search_results",
            "id": getattr(request, "_req_id", "n/a"),
            "found_count": len(clean_urls)
        }))
        
        return clean_urls
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "google_search_error", 
            "id": getattr(request, "_req_id", "n/a"),
            "error": str(e)
        }))
        return []

def get_reddit_post_from_url(reddit, url):
    """Get Reddit post object from URL"""
    try:
        # Extract post ID from URL  
        url_parts = url.split('/')
        
        if 'comments' in url_parts:
            post_id_index = url_parts.index('comments') + 1
            if post_id_index < len(url_parts):
                post_id = url_parts[post_id_index]
                
                submission = reddit.submission(id=post_id)
                # Access a property to ensure the post exists
                _ = submission.title
                return submission
        
        return None
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "reddit_post_error",
            "id": getattr(request, "_req_id", "n/a"),
            "url": url,
            "error": str(e)
        }))
        return None

def analyze_reddit_data(submissions, query):
    """Perform comprehensive analysis of Reddit data"""
    from datetime import datetime, timezone
    from collections import Counter
    import statistics
    
    if not submissions:
        return {
            'post_metrics': {'total_posts': 0},
            'engagement_analysis': {},
            'content_analysis': {},
            'community_analysis': {},
            'temporal_analysis': {}
        }
    
    # Post metrics
    scores = [sub.score for sub in submissions]
    comments = [sub.num_comments for sub in submissions]
    
    post_metrics = {
        'total_posts': len(submissions),
        'avg_score': round(statistics.mean(scores), 1) if scores else 0,
        'median_score': round(statistics.median(scores), 1) if scores else 0,
        'total_upvotes': sum(scores),
        'total_comments': sum(comments),
        'avg_upvote_ratio': round(statistics.mean([sub.upvote_ratio for sub in submissions if hasattr(sub, 'upvote_ratio') and sub.upvote_ratio]), 3) if submissions else 0
    }
    
    # Community analysis
    subreddits = [str(sub.subreddit) for sub in submissions]
    subreddit_counts = Counter(subreddits)
    
    community_analysis = {
        'subreddits_involved': list(set(subreddits)),
        'primary_subreddit': subreddit_counts.most_common(1)[0][0] if subreddit_counts else 'unknown'
    }
    
    # Temporal analysis  
    now = datetime.now(timezone.utc).timestamp()
    ages = [(now - sub.created_utc) / (24 * 3600) for sub in submissions]  # Age in days
    
    temporal_analysis = {
        'avg_age_days': round(statistics.mean(ages), 1) if ages else 0,
        'freshness_score': round(len([age for age in ages if age <= 30]) / len(ages) * 100, 1) if ages else 0
    }
    
    # Simple engagement analysis
    engagement_analysis = {
        'total_comments_analyzed': sum(comments),
        'avg_comments_per_post': round(statistics.mean(comments), 1) if comments else 0
    }
    
    # Basic content analysis
    content_analysis = {
        'unique_brands': 0,  # Simplified for Firebase Functions
        'total_brand_mentions': 0
    }
    
    return {
        'post_metrics': post_metrics,
        'engagement_analysis': engagement_analysis,
        'content_analysis': content_analysis,
        'community_analysis': community_analysis,
        'temporal_analysis': temporal_analysis
    }

# Firebase Functions entry point
@https_fn.on_request(
    secrets=[
        "ANTHROPIC_API_KEY",
        "REDDIT_CLIENT_ID", 
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT"
    ]
)
def api(req: https_fn.Request) -> https_fn.Response:
    """Firebase Functions HTTP entry point"""
    # Create a Flask request context
    with app.test_request_context(
        path=req.path,
        method=req.method,
        headers=dict(req.headers),
        query_string=req.query_string.encode() if req.query_string else b'',
        data=req.get_data()
    ):
        try:
            response = app.full_dispatch_request()
            return response
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {"error": "Internal server error"}, 500

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))