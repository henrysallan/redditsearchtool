from firebase_functions import https_fn
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import praw
import anthropic
import google.generativeai as genai
import stripe
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
from urllib.parse import quote

# Load environment variables
load_dotenv()

# Stripe will be configured using Firebase Secrets
# stripe.api_key will be set in functions that need it

# Create Flask app
app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("functions")

def call_ai_model(model: str, prompt: str, max_tokens: int = 1500):
    """
    Universal function to call either Claude or Gemini based on model name
    """
    if model.startswith('gemini-'):
        # Use Gemini API
        try:
            # Configure Gemini API key
            genai.configure(api_key=os.environ.get("GOOGLE_AI_API_KEY"))
            gemini_model = genai.GenerativeModel(model)
            response = gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    else:
        # Use Claude API
        try:
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

# User tier and model access control
def get_user_tier(user_id=None):
    """Determine user tier - for now all authenticated users are 'free'"""
    if not user_id:
        return 'anonymous'
    # TODO: Add subscription logic here later
    return 'free'

def get_allowed_models(tier):
    """Get list of models allowed for each tier"""
    if tier == 'anonymous' or tier == 'free':
        return ['gemini-1.5-flash']
    elif tier == 'paid':
        return [
            'gemini-1.5-flash', 
            'gemini-1.5-pro',
            'claude-3-5-haiku-20241022',
            'claude-3-5-sonnet-20241022', 
            'claude-3-opus-20240229'
        ]
    return []

def is_model_allowed(model, tier):
    """Check if a model is allowed for the given user tier"""
    return model in get_allowed_models(tier)

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
    
    # Gemini pricing (as of 2024) - per million tokens
    gemini_pricing = {
        'gemini-1.5-flash': {'input': 0.075, 'output': 0.30},             # Flash (free tier available)
        'gemini-1.5-pro': {'input': 3.50, 'output': 10.50}               # Pro
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
        
        # Total tokens
        total_input_tokens = agent_input_tokens + coordinator_input_tokens
        total_output_tokens = agent_output_tokens + coordinator_output_tokens
        
        return jsonify({
            'search_mode': 'multi_agent_web_search',
            'estimated_tokens': {
                'agent_input': agent_input_tokens,
                'agent_output': agent_output_tokens,
                'coordinator_input': coordinator_input_tokens,
                'coordinator_output': coordinator_output_tokens,
                'total_input': total_input_tokens,
                'total_output': total_output_tokens,
                'total': total_input_tokens + total_output_tokens
            },
            'costs': {
                'agent_cost': round(agent_input_cost + agent_output_cost, 4),
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
        
        # Determine pricing based on model
        if model.startswith('gemini-'):
            pricing = gemini_pricing.get(model, gemini_pricing['gemini-1.5-flash'])
            ai_provider = 'gemini'
        else:
            pricing = claude_pricing.get(model, claude_pricing['claude-3-5-sonnet-20241022'])
            ai_provider = 'claude'
        
        input_cost = (estimated_input_tokens / 1_000_000) * pricing['input']
        output_cost = (estimated_output_tokens / 1_000_000) * pricing['output']
        total_cost = input_cost + output_cost
        
        # Reddit API is free for reasonable usage
        reddit_cost = 0.0
        
        return jsonify({
            'search_mode': 'traditional_reddit_search',
            'estimated_tokens': {
                'input': estimated_input_tokens,
                'output': estimated_output_tokens,
                'total': estimated_input_tokens + estimated_output_tokens
            },
            'costs': {
                'reddit_api': reddit_cost,
                'claude_input': round(input_cost, 4),
                'claude_output': round(output_cost, 4),
                'claude_total': round(input_cost + output_cost, 4),
                'total': round(total_cost + reddit_cost, 4)
            },
            'model': model,
            'posts': max_posts
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
        model = data.get('model', 'gemini-1.5-flash')
        
        # New web search mode parameters
        use_web_search = data.get('use_web_search', False)
        agent_count = data.get('agent_count', 3)
        
        # Set coordinator model based on user tier
        user_tier = 'anonymous'  # This will be enhanced with proper auth
        allowed_models = get_allowed_models(user_tier)
        default_coordinator = allowed_models[0] if allowed_models else 'gemini-1.5-flash'
        coordinator_model = data.get('coordinator_model', default_coordinator)

        if not query:
            return jsonify({'error': 'Query is required'}), 400

        # Validate max_posts
        if not isinstance(max_posts, int) or max_posts < 1 or max_posts > 10:
            return jsonify({'error': 'max_posts must be between 1 and 10'}), 400

        # Validate agent_count
        if not isinstance(agent_count, int) or agent_count < 1 or agent_count > 5:
            return jsonify({'error': 'agent_count must be between 1 and 5'}), 400

        # Validate models with tier-based access
        # For now, we'll assume anonymous users (no auth header)
        # TODO: Add proper authentication header parsing
        user_tier = 'anonymous'  # This will be enhanced with proper auth
        
        all_valid_models = [
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'claude-3-5-haiku-20241022',
            'claude-3-5-sonnet-20241022', 
            'claude-3-opus-20240229'
        ]
        
        if model not in all_valid_models:
            return jsonify({'error': f'Invalid model. Must be one of: {all_valid_models}'}), 400
        
        # Check if user tier allows this model
        if not is_model_allowed(model, user_tier):
            if user_tier == 'anonymous':
                return jsonify({'error': 'This model requires sign-in. Please sign in to access more models.'}), 403
            elif user_tier == 'free':
                return jsonify({'error': 'This model requires a paid subscription. Please upgrade your account.'}), 403
        
        if coordinator_model not in all_valid_models:
            return jsonify({'error': f'Invalid coordinator_model. Must be one of: {all_valid_models}'}), 400
        
        if not is_model_allowed(coordinator_model, user_tier):
            if user_tier == 'anonymous':
                return jsonify({'error': 'This coordinator model requires sign-in.'}), 403
            elif user_tier == 'free':
                return jsonify({'error': 'This coordinator model requires a paid subscription.'}), 403

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
                'GOOGLE_AI_API_KEY': bool(os.environ.get('GOOGLE_AI_API_KEY')),
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
        
        # Primary strategy: Google search for Reddit posts (this was the working method)
        reddit_urls = search_google_for_reddit_posts(query, num_results=max_posts * 2)
        
        # Fallback: Direct Reddit search only if Google fails
        submissions = []
        if not reddit_urls:
            logger.info(json.dumps({
                "event": "fallback_reddit_search",
                "id": getattr(request, "_req_id", "n/a")
            }))
            try:
                # Try specific subreddits based on common search patterns
                search_subreddits = ["BuyItForLife", "reviews", "gadgets", "technology", "AskReddit"]
                
                for sub_name in search_subreddits:
                    try:
                        subreddit = reddit.subreddit(sub_name)
                        results = list(subreddit.search(query, sort="relevance", limit=3, time_filter="all"))
                        if results:
                            submissions.extend(results)
                            logger.info(json.dumps({
                                "event": "subreddit_search_success",
                                "id": getattr(request, "_req_id", "n/a"),
                                "subreddit": sub_name,
                                "found_count": len(results)
                            }))
                            if len(submissions) >= max_posts:
                                break
                    except Exception as sub_error:
                        logger.warning(json.dumps({
                            "event": "subreddit_search_error",
                            "id": getattr(request, "_req_id", "n/a"),
                            "subreddit": sub_name,
                            "error": str(sub_error)
                        }))
                        continue
                        
                # If we found submissions directly, convert to URLs for consistency
                if submissions:
                    reddit_urls = [f"https://reddit.com{sub.permalink}" for sub in submissions[:max_posts]]
                    
                logger.info(json.dumps({
                    "event": "reddit_direct_search",
                    "id": getattr(request, "_req_id", "n/a"),
                    "found_count": len(submissions)
                }))
            except Exception as e:
                logger.error(json.dumps({
                    "event": "reddit_search_error",
                    "id": getattr(request, "_req_id", "n/a"),
                    "error": str(e)
                }))

        if not reddit_urls:
            logger.warning(json.dumps({
                "event": "no_posts_found",
                "id": getattr(request, "_req_id", "n/a"),
                "query": query
            }))
            return jsonify({'error': 'No Reddit posts found for the given query.'}), 404

        logger.info(json.dumps({
            "event": "reddit_urls_found",
            "id": getattr(request, "_req_id", "n/a"),
            "urls": reddit_urls,
            "total_count": len(reddit_urls)
        }))

        # Get Reddit post objects from URLs or use direct submissions
        if submissions:
            # We already have submission objects from direct search
            final_submissions = submissions[:max_posts]
        else:
            # Process URLs from Google search
            final_submissions = []
            for i, url in enumerate(reddit_urls):
                logger.info(json.dumps({
                    "event": "processing_url",
                    "id": getattr(request, "_req_id", "n/a"),
                    "url_index": i + 1,
                    "url": url
                }))
                
                post = get_reddit_post_from_url(reddit, url)
                if post:
                    final_submissions.append(post)
                    logger.info(json.dumps({
                        "event": "url_processed_successfully",
                        "id": getattr(request, "_req_id", "n/a"),
                        "url_index": i + 1,
                        "post_title": post.title[:50] + "..." if len(post.title) > 50 else post.title
                    }))
                else:
                    logger.warning(json.dumps({
                        "event": "url_processing_failed",
                        "id": getattr(request, "_req_id", "n/a"),
                        "url_index": i + 1,
                        "url": url
                    }))
                
                if len(final_submissions) >= max_posts:
                    break

        if not final_submissions:
            return jsonify({'error': 'Could not retrieve Reddit posts from search results.'}), 404

        logger.info(json.dumps({
            "event": "posts_retrieved",
            "id": getattr(request, "_req_id", "n/a"),
            "post_count": len(final_submissions)
        }))

        # Perform data analysis
        analysis = analyze_reddit_data(final_submissions, query)

        # Extract text from posts and comments  
        full_text = ""
        sources = []
        for submission in final_submissions:
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

        # Get summary using universal AI model with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                message = call_ai_model(model, prompt, max_tokens=1500)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(json.dumps({
                        "event": "ai_model_error",
                        "id": getattr(request, "_req_id", "n/a"),
                        "model": model,
                        "error": str(e),
                        "attempt": attempt + 1
                    }))
                    return jsonify({'error': f'AI API error: {str(e)}'}), 500
                
                # Wait before retry
                wait_time = (2 ** attempt) + 0.5
                logger.warning(json.dumps({
                    "event": "ai_model_retry",
                    "id": getattr(request, "_req_id", "n/a"),
                    "model": model,
                    "attempt": attempt + 1,
                    "wait_time": wait_time
                }))
                time.sleep(wait_time)

        logger.info(json.dumps({
            "event": "search_completed",
            "id": getattr(request, "_req_id", "n/a"),
            "post_count": len(final_submissions),
            "sources_count": len(sources)
        }))

        # AI-powered enhanced links generation
        extracted_terms = []
        enhanced_links = {}
        
        try:
            # Step 1: Use AI to extract meaningful search terms from the summary
            extraction_prompt = f"""Based on this Reddit discussion summary, extract 3-5 specific and useful search terms that would help someone learn more about the topic. Focus on:
- Product names, brand names, model numbers
- Specific locations, restaurants, services
- Technical terms, concepts, or methodologies
- Specific titles (books, movies, games, etc.)

Summary: {message}

Return only a comma-separated list of terms, no explanations:"""
            
            ai_extracted_terms = call_ai_model(model, extraction_prompt, max_tokens=100)
            extracted_terms = [term.strip() for term in ai_extracted_terms.split(',') if term.strip()][:5]
            
            logger.info(json.dumps({
                "event": "ai_terms_extracted",
                "id": getattr(request, "_req_id", "n/a"),
                "terms": extracted_terms
            }))
            
            # Step 2: Use Google Search API to find external links for each term
            api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
            search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
            
            if api_key and search_engine_id and extracted_terms:
                for term in extracted_terms[:3]:  # Limit to 3 terms
                    # Search Google for general web results (not Reddit)
                    search_query = term
                    api_url = "https://www.googleapis.com/customsearch/v1"
                    params = {
                        'key': api_key,
                        'cx': search_engine_id,
                        'q': search_query,
                        'num': 5,  # Get 5 results to choose from
                        'fields': 'items(title,link,snippet)'
                    }
                    
                    try:
                        response = requests.get(api_url, params=params, timeout=10)
                        response.raise_for_status()
                        search_data = response.json()
                        
                        if 'items' in search_data:
                            # Step 3: Use AI to curate the best links
                            search_results = search_data['items']
                            results_text = "\n".join([f"{i+1}. {item['title']} - {item['link']} - {item.get('snippet', '')[:100]}" 
                                                    for i, item in enumerate(search_results)])
                            
                            curation_prompt = f"""From these search results for "{term}", select the 2 most helpful and relevant links. Consider:
- Authoritative sources (official sites, reputable publications)
- Practical value (reviews, guides, comparisons)
- Avoid spam, low-quality, or overly promotional content

Search results:
{results_text}

Return only the numbers (e.g., "1,3") of the best links:"""
                            
                            ai_selection = call_ai_model(model, curation_prompt, max_tokens=50)
                            selected_indices = []
                            for num in ai_selection.split(','):
                                try:
                                    idx = int(num.strip()) - 1
                                    if 0 <= idx < len(search_results):
                                        selected_indices.append(idx)
                                except:
                                    pass
                            
                            # Build curated links
                            curated_links = []
                            for idx in selected_indices[:2]:  # Max 2 links per term
                                item = search_results[idx]
                                curated_links.append({
                                    'url': item['link'],
                                    'title': item['title'],
                                    'snippet': item.get('snippet', '')[:200],
                                    'relevance_score': 0.9  # High score for AI-curated links
                                })
                            
                            if curated_links:
                                enhanced_links[term] = curated_links
                                
                    except Exception as search_error:
                        logger.warning(json.dumps({
                            "event": "google_search_error",
                            "id": getattr(request, "_req_id", "n/a"),
                            "term": term,
                            "error": str(search_error)
                        }))
                        
        except Exception as extraction_error:
            logger.warning(json.dumps({
                "event": "enhanced_links_error", 
                "id": getattr(request, "_req_id", "n/a"),
                "error": str(extraction_error)
            }))
            # Fallback to basic term extraction
            import re
            terms = re.findall(r'\b\w+\b', query.lower())
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'what', 'how', 'where', 'when', 'why', 'who'}
            extracted_terms = [term for term in terms if len(term) > 2 and term not in stop_words][:3]

        return jsonify({
            'summary': message,
            'sources': sources,
            'analysis': analysis,
            'enhanced_links': enhanced_links,
            'extracted_search_terms': extracted_terms,
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
                # For server applications, we don't need username/password
                # This will use client credentials flow
            )
            
            # Test basic subreddit access first
            subreddit = reddit.subreddit("test")
            _ = subreddit.display_name  # This will trigger API call
            
            # Test if we can read a post (this requires different permissions)
            try:
                test_post = reddit.submission(id='vg2jen')
                _ = test_post.title
                reddit_status = "connected (full access)"
            except Exception as post_error:
                reddit_status = f"connected (subreddit only) - post error: {str(post_error)}"
                
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
                'GOOGLE_AI_API_KEY': bool(os.environ.get('GOOGLE_AI_API_KEY')),
                'REDDIT_CLIENT_ID': bool(os.environ.get('REDDIT_CLIENT_ID')),
                'REDDIT_CLIENT_SECRET': bool(os.environ.get('REDDIT_CLIENT_SECRET')),
                'REDDIT_USER_AGENT': bool(os.environ.get('REDDIT_USER_AGENT')),
                'GOOGLE_SEARCH_API_KEY': bool(os.environ.get('GOOGLE_SEARCH_API_KEY')),
                'GOOGLE_SEARCH_ENGINE_ID': bool(os.environ.get('GOOGLE_SEARCH_ENGINE_ID')),
            },
            'reddit_api_status': reddit_status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': int(time.time())
        }), 500

# Simple test endpoint
@app.route('/api/test-json', methods=['GET'])
@app.route('/test-json', methods=['GET'])
def test_json():
    """Test Reddit JSON API directly"""
    try:
        url = "https://www.reddit.com/r/functionalprogramming/comments/1hzlszu/which_functional_programming_language_should_i/"
        
        # Test URL construction
        if '/comments/' in url:
            parts = url.split('/comments/')
            if len(parts) >= 2:
                base_part = parts[0]  # https://www.reddit.com/r/subreddit
                post_part = parts[1].split('/')[0]  # post_id
                
                json_url = f"{base_part}/comments/{post_part}.json"
                
                # Make request
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; RedditSearchBot/1.0)'}
                response = requests.get(json_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0 and 'data' in data[0]:
                        post_data = data[0]['data']['children'][0]['data']
                        return jsonify({
                            'success': True,
                            'original_url': url,
                            'json_url': json_url,
                            'title': post_data.get('title', '')[:50],
                            'subreddit': post_data.get('subreddit', ''),
                            'score': post_data.get('score', 0)
                        })
                
                return jsonify({
                    'success': False,
                    'json_url': json_url,
                    'status_code': response.status_code,
                    'response_text': response.text[:200]
                })
        
        return jsonify({'error': 'Invalid URL format'})
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# Debug endpoint for Google search
@app.route('/api/debug-search', methods=['POST'])
@app.route('/debug-search', methods=['POST'])
def debug_search():
    """Debug endpoint to test Google search"""
    try:
        data = request.get_json(silent=True) or {}
        query = data.get('query', 'test')
        
        # Test Google Custom Search API
        reddit_urls = search_google_for_reddit_posts(query, num_results=3)
        
        # Test Reddit API connection
        reddit = praw.Reddit(
            client_id=os.environ.get("REDDIT_CLIENT_ID"),
            client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
            user_agent=os.environ.get("REDDIT_USER_AGENT"),
        )
        
        # Test basic Reddit API access
        try:
            test_post = reddit.submission(id='vg2jen')  # Known post ID from above
            test_title = test_post.title
            reddit_test_result = {
                'success': True,
                'test_post_title': test_title[:50],
                'test_post_score': test_post.score
            }
        except Exception as e:
            reddit_test_result = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
        
        # Test URL processing with detailed logging
        url_processing_results = []
        for url in reddit_urls:
            print(f"DEBUG: Processing URL: {url}")
            
            # Use the updated get_reddit_post_from_url function
            try:
                post = get_reddit_post_from_url(reddit, url)
                if post:
                    url_processing_results.append({
                        'url': url,
                        'success': True,
                        'title': post.title[:50],
                        'subreddit': str(post.subreddit) if hasattr(post, 'subreddit') else getattr(post, 'subreddit', 'unknown'),
                        'score': post.score,
                        'method': 'json_api' if hasattr(post, 'id') and not hasattr(post, 'author') else 'praw'
                    })
                else:
                    url_processing_results.append({
                        'url': url,
                        'success': False,
                        'error': 'Function returned None'
                    })
            except Exception as e:
                url_processing_results.append({
                    'url': url,
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc()
                })
        
        return jsonify({
            'query': query,
            'google_search_results': {
                'found_urls': reddit_urls,
                'count': len(reddit_urls)
            },
            'reddit_api_test': reddit_test_result,
            'url_processing': url_processing_results,
            'api_credentials': {
                'google_api_key_present': bool(os.environ.get('GOOGLE_SEARCH_API_KEY')),
                'google_engine_id_present': bool(os.environ.get('GOOGLE_SEARCH_ENGINE_ID')),
                'reddit_credentials_present': bool(os.environ.get('REDDIT_CLIENT_ID'))
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

def search_google_for_reddit_posts(query, num_results=5):
    """Search Google Custom Search API for Reddit posts related to the query"""
    try:
        # Check if Google Search API credentials are available
        api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
        search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
        
        if not api_key or not search_engine_id:
            logger.warning(json.dumps({
                "event": "google_api_not_configured",
                "id": getattr(request, "_req_id", "n/a"),
                "api_key_present": bool(api_key),
                "engine_id_present": bool(search_engine_id)
            }))
            return []
        
        # Use Google Custom Search API
        search_query = f"{query} site:reddit.com"
        
        api_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': search_query,
            'num': min(num_results, 10),  # API max is 10
            'fields': 'items(title,link)'  # Only get what we need
        }
        
        logger.info(json.dumps({
            "event": "google_api_request",
            "id": getattr(request, "_req_id", "n/a"),
            "query": search_query,
            "num_results": params['num']
        }))
        
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract Reddit URLs from API results
        reddit_urls = []
        if 'items' in data:
            for item in data['items']:
                url = item.get('link', '')
                # Verify it's a Reddit post URL
                if re.match(r'https://(?:www\.)?reddit\.com/r/[^/]+/comments/', url):
                    reddit_urls.append(url)
        
        logger.info(json.dumps({
            "event": "google_api_results",
            "id": getattr(request, "_req_id", "n/a"),
            "found_count": len(reddit_urls),
            "total_items": len(data.get('items', [])),
            "urls": reddit_urls[:3]  # Log first 3 URLs for debugging
        }))
        
        return reddit_urls
        
    except requests.exceptions.RequestException as e:
        logger.error(json.dumps({
            "event": "google_api_request_error", 
            "id": getattr(request, "_req_id", "n/a"),
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }))
        return []
    except Exception as e:
        logger.error(json.dumps({
            "event": "google_api_error", 
            "id": getattr(request, "_req_id", "n/a"),
            "error": str(e),
            "trace": traceback.format_exc()
        }))
        return []

def get_reddit_post_from_url_json(url):
    """Get Reddit post data using Reddit JSON API (no auth required)"""
    try:
        logger.info(json.dumps({
            "event": "processing_reddit_url_json",
            "id": getattr(request, "_req_id", "n/a"),
            "url": url
        }))
        
        # Convert reddit.com URL to JSON API URL
        # https://www.reddit.com/r/subreddit/comments/post_id/title/ -> 
        # https://www.reddit.com/r/subreddit/comments/post_id.json
        
        if '/comments/' in url:
            # Extract the parts we need
            parts = url.split('/comments/')
            if len(parts) >= 2:
                base_part = parts[0]  # https://www.reddit.com/r/subreddit
                post_part = parts[1].split('/')[0]  # post_id
                
                json_url = f"{base_part}/comments/{post_part}.json"
                
                logger.info(json.dumps({
                    "event": "reddit_json_url_constructed",
                    "id": getattr(request, "_req_id", "n/a"),
                    "original_url": url,
                    "json_url": json_url
                }))
                
                # Make request to Reddit JSON API
                headers = {
                    'User-Agent': 'RedditSearchTool/1.0 (by /u/YourUsername)'
                }
                
                logger.info(json.dumps({
                    "event": "making_reddit_json_request",
                    "id": getattr(request, "_req_id", "n/a"),
                    "json_url": json_url
                }))
                
                response = requests.get(json_url, headers=headers, timeout=10)
                
                logger.info(json.dumps({
                    "event": "reddit_json_response",
                    "id": getattr(request, "_req_id", "n/a"),
                    "status_code": response.status_code,
                    "content_length": len(response.text)
                }))
                
                response.raise_for_status()
                
                data = response.json()
                
                logger.info(json.dumps({
                    "event": "reddit_json_parsed",
                    "id": getattr(request, "_req_id", "n/a"),
                    "data_type": type(data).__name__,
                    "data_length": len(data) if isinstance(data, list) else "not_list"
                }))
                
                # Reddit JSON API returns [listing, comments]
                # We want the post data from the first listing
                if data and len(data) > 0 and 'data' in data[0]:
                    post_data = data[0]['data']['children'][0]['data']
                    
                    logger.info(json.dumps({
                        "event": "reddit_post_retrieved_json",
                        "id": getattr(request, "_req_id", "n/a"),
                        "title": post_data.get('title', '')[:50],
                        "subreddit": post_data.get('subreddit', ''),
                        "score": post_data.get('score', 0)
                    }))
                    
                    # Return a simplified object that matches what we expect
                    class SimplePost:
                        def __init__(self, data):
                            self.title = data.get('title', '')
                            self.selftext = data.get('selftext', '')
                            self.subreddit = data.get('subreddit', '')
                            self.score = data.get('score', 0)
                            self.num_comments = data.get('num_comments', 0)
                            self.created_utc = data.get('created_utc', 0)
                            self.author = data.get('author', '[deleted]')
                            self.url = data.get('url', '')
                    
                    return SimplePost(post_data)
        
        logger.warning(json.dumps({
            "event": "reddit_json_parse_failed",
            "id": getattr(request, "_req_id", "n/a"),
            "url": url,
            "reason": "Could not parse URL or extract post data"
        }))
        return None
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "reddit_json_error",
            "id": getattr(request, "_req_id", "n/a"),
            "url": url,
            "error": str(e),
            "error_type": type(e).__name__
        }))
        return None

def get_reddit_post_from_url(reddit, url):
    """Get Reddit post object from URL with fallback to JSON API"""
    try:
        logger.info(json.dumps({
            "event": "processing_reddit_url",
            "id": getattr(request, "_req_id", "n/a"),
            "url": url
        }))
        
        # First try the JSON API approach (no auth required)
        post = get_reddit_post_from_url_json(url)
        if post:
            return post
        
        # Fallback to PRAW approach (requires auth)
        # Extract post ID from URL  
        url_parts = url.split('/')
        
        logger.info(json.dumps({
            "event": "url_parts_analysis",
            "id": getattr(request, "_req_id", "n/a"),
            "url_parts": url_parts,
            "url_parts_count": len(url_parts)
        }))
        
        if 'comments' in url_parts:
            post_id_index = url_parts.index('comments') + 1
            if post_id_index < len(url_parts):
                post_id = url_parts[post_id_index]
                
                logger.info(json.dumps({
                    "event": "extracted_post_id",
                    "id": getattr(request, "_req_id", "n/a"),
                    "post_id": post_id,
                    "url": url
                }))
                
                # Get submission from Reddit API
                submission = reddit.submission(id=post_id)
                
                # Access a property to ensure the post exists and trigger API call
                title = submission.title
                
                logger.info(json.dumps({
                    "event": "reddit_post_retrieved",
                    "id": getattr(request, "_req_id", "n/a"),
                    "post_id": post_id,
                    "title": title[:50] + "..." if len(title) > 50 else title,
                    "subreddit": str(submission.subreddit),
                    "score": submission.score
                }))
                
                return submission
        
        logger.warning(json.dumps({
            "event": "post_id_extraction_failed",
            "id": getattr(request, "_req_id", "n/a"),
            "url": url,
            "reason": "comments not found in URL or no post_id after comments"
        }))
        return None
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "reddit_post_error",
            "id": getattr(request, "_req_id", "n/a"),
            "url": url,
            "error": str(e),
            "error_type": type(e).__name__,
            "trace": traceback.format_exc()
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

@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe checkout session for subscription"""
    try:
        # Set Stripe API key from Firebase Secrets
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
        
        data = request.get_json()
        user_id = data.get('userId')
        user_email = data.get('userEmail')
        price_id = data.get('priceId')
        coupon_code = data.get('couponCode')  # Optional coupon code
        
        if not all([user_id, user_email, price_id]):
            return {"error": "Missing required fields"}, 400
        
        # Build checkout session parameters
        session_params = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price': price_id,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': 'https://redditsearchtool.web.app/?success=true&session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': 'https://redditsearchtool.web.app/?canceled=true',
            'customer_email': user_email,
            'metadata': {
                'user_id': user_id
            },
            'subscription_data': {
                'metadata': {
                    'user_id': user_id
                }
            }
        }
        
        # Either use coupon or allow promotion codes, but not both
        if coupon_code:
            session_params['discounts'] = [{
                'coupon': coupon_code
            }]
        else:
            session_params['allow_promotion_codes'] = True  # Allow users to enter promo codes
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(**session_params)
        
        return {"sessionId": checkout_session.id}
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return {"error": str(e)}, 500

@app.route('/api/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    # Set Stripe API key from Firebase Secrets
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    
    payload = request.get_data()
    sig_header = request.headers.get('stripe-signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return {"error": "Invalid payload"}, 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return {"error": "Invalid signature"}, 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_successful_payment(session)
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_subscription_renewal(invoice)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_cancelled(subscription)
    
    return {"status": "success"}

@app.route('/api/admin/grant-access', methods=['POST'])
def grant_user_access():
    """Admin function to grant free access to specific users"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        admin_key = data.get('adminKey')
        
        # Simple admin authentication (you should change this key)
        ADMIN_KEY = "reddit_search_admin_2025"  # Change this to something secure
        
        if admin_key != ADMIN_KEY:
            return {"error": "Unauthorized"}, 401
            
        if not user_id:
            return {"error": "Missing userId"}, 400
        
        # Update user's subscription status in Firestore
        from google.cloud import firestore
        db = firestore.Client()
        
        user_ref = db.collection('users').document(user_id)
        user_ref.set({
            'subscription': {
                'status': 'active',
                'customer_id': 'manual_admin_grant',
                'subscription_id': 'manual_admin_grant',
                'created_at': firestore.SERVER_TIMESTAMP,
                'granted_by': 'admin'
            }
        }, merge=True)
        
        logger.info(f"Admin granted free access to user {user_id}")
        
        return {
            "status": "success",
            "message": f"Free access granted to user {user_id}"
        }
        
    except Exception as e:
        logger.error(f"Error granting admin access: {str(e)}")
        return {"error": str(e)}, 500

@app.route('/api/test-stripe', methods=['GET'])
def test_stripe():
    """Test endpoint to check Stripe products and prices"""
    try:
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
        
        # List all products
        products = stripe.Product.list(limit=10)
        
        # List all prices
        prices = stripe.Price.list(limit=10)
        
        return {
            "products": [{"id": p.id, "name": p.name} for p in products.data],
            "prices": [{"id": p.id, "product": p.product, "amount": p.unit_amount, "currency": p.currency} for p in prices.data]
        }
        
    except Exception as e:
        logger.error(f"Error testing Stripe: {str(e)}")
        return {"error": str(e)}, 500

@app.route('/api/unsubscribe', methods=['POST'])
def unsubscribe():
    """Cancel user's subscription"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        if not user_id:
            return {"error": "User ID is required"}, 400
        
        # Configure Stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
        
        # Get user's subscription info from Firestore
        from google.cloud import firestore
        db = firestore.Client()
        
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return {"error": "User not found"}, 404
        
        user_data = user_doc.to_dict()
        subscription_info = user_data.get('subscription', {})
        subscription_id = subscription_info.get('subscription_id')
        
        if not subscription_id:
            return {"error": "No active subscription found"}, 400
        
        # Cancel the subscription in Stripe
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        # Update user's subscription status in Firestore
        user_ref.update({
            'subscription.status': 'cancelled',
            'subscription.cancelled_at': firestore.SERVER_TIMESTAMP,
            'subscription.cancel_at_period_end': True,
            'subscription.current_period_end': subscription.current_period_end
        })
        
        logger.info(f"Subscription cancelled for user {user_id}")
        
        return {
            "success": True,
            "message": "Subscription cancelled successfully",
            "current_period_end": subscription.current_period_end
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error during unsubscribe: {str(e)}")
        return {"error": f"Payment processing error: {str(e)}"}, 500
    except Exception as e:
        logger.error(f"Error during unsubscribe: {str(e)}")
        return {"error": "Failed to cancel subscription"}, 500

@app.route('/api/delete-account', methods=['POST'])
def delete_account():
    """Delete user account and all associated data"""
    try:
        data = request.get_json()
        user_id = data.get('userId')
        
        if not user_id:
            return {"error": "User ID is required"}, 400
        
        # Configure Stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
        
        # Get user's data from Firestore
        from google.cloud import firestore
        db = firestore.Client()
        
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            subscription_info = user_data.get('subscription', {})
            customer_id = subscription_info.get('customer_id')
            subscription_id = subscription_info.get('subscription_id')
            
            # Cancel subscription if it exists
            if subscription_id:
                try:
                    stripe.Subscription.delete(subscription_id)
                    logger.info(f"Deleted subscription {subscription_id} for user {user_id}")
                except stripe.error.StripeError as e:
                    logger.warning(f"Could not delete subscription: {str(e)}")
            
            # Delete customer if it exists
            if customer_id:
                try:
                    stripe.Customer.delete(customer_id)
                    logger.info(f"Deleted customer {customer_id} for user {user_id}")
                except stripe.error.StripeError as e:
                    logger.warning(f"Could not delete customer: {str(e)}")
        
        # Delete user data from Firestore
        user_ref.delete()
        
        # Delete search history
        search_history_ref = db.collection('search_history').where('user_id', '==', user_id)
        for doc in search_history_ref.stream():
            doc.reference.delete()
        
        logger.info(f"Account deleted for user {user_id}")
        
        return {
            "success": True,
            "message": "Account deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error during account deletion: {str(e)}")
        return {"error": "Failed to delete account"}, 500

def handle_successful_payment(session):
    """Handle successful payment and activate subscription"""
    try:
        user_id = session['metadata']['user_id']
        customer_id = session['customer']
        subscription_id = session['subscription']
        
        # Update user's subscription status in Firestore
        from google.cloud import firestore
        db = firestore.Client()
        
        user_ref = db.collection('users').document(user_id)
        user_ref.set({
            'subscription': {
                'status': 'active',
                'customer_id': customer_id,
                'subscription_id': subscription_id,
                'created_at': firestore.SERVER_TIMESTAMP
            }
        }, merge=True)
        
        logger.info(f"Activated subscription for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling successful payment: {str(e)}")

def handle_subscription_renewal(invoice):
    """Handle subscription renewal"""
    try:
        customer_id = invoice['customer']
        # Find user by customer_id and update renewal date
        # Implementation depends on your needs
        logger.info(f"Subscription renewed for customer {customer_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription renewal: {str(e)}")

def handle_subscription_cancelled(subscription):
    """Handle subscription cancellation"""
    try:
        customer_id = subscription['customer']
        
        # Find and update user's subscription status
        from google.cloud import firestore
        db = firestore.Client()
        
        # Query to find user by customer_id
        users_ref = db.collection('users')
        query = users_ref.where('subscription.customer_id', '==', customer_id).limit(1)
        docs = query.stream()
        
        for doc in docs:
            doc.reference.update({
                'subscription.status': 'cancelled',
                'subscription.cancelled_at': firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Cancelled subscription for user {doc.id}")
            break
        
    except Exception as e:
        logger.error(f"Error handling subscription cancellation: {str(e)}")

# Firebase Functions entry point
@https_fn.on_request(
    secrets=[
        "ANTHROPIC_API_KEY",
        "REDDIT_CLIENT_ID", 
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
        "GOOGLE_SEARCH_API_KEY",
        "GOOGLE_SEARCH_ENGINE_ID",
        "GOOGLE_AI_API_KEY",
        "STRIPE_SECRET_KEY",        # Stripe secrets configured
        "STRIPE_WEBHOOK_SECRET"     # Stripe secrets configured
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