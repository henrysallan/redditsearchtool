from flask import Flask, request, jsonify
from dotenv import load_dotenv
import praw
import anthropic
import google.generativeai as genai
import os
import time
import random
import requests
import re
import asyncio
from urllib.parse import urlparse, parse_qs, quote, urlencode
from datetime import datetime, timezone
from collections import Counter
import statistics
from playwright.async_api import async_playwright

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))

app = Flask(__name__)

@app.route('/api/estimate-cost', methods=['POST'])
def estimate_cost():
    """Estimate the cost of a search request"""
    data = request.get_json()
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
        
        # Each Haiku agent: ~1000 tokens input + 500 tokens output per agent
        agent_input_tokens = agent_count * 1000
        agent_output_tokens = agent_count * 500
        
        # Coordinator model: ~3000 tokens input (agent results) + 1000 tokens output
        coordinator_input_tokens = 3000
        coordinator_output_tokens = 1000
        
        # Total tokens
        total_input_tokens = agent_input_tokens + coordinator_input_tokens
        total_output_tokens = agent_output_tokens + coordinator_output_tokens
        
        # Calculate agent costs (always Haiku)
        haiku_pricing = claude_pricing['claude-3-5-haiku-20241022']
        agent_input_cost = (agent_input_tokens / 1_000_000) * haiku_pricing['input']
        agent_output_cost = (agent_output_tokens / 1_000_000) * haiku_pricing['output']
        
        # Calculate coordinator costs
        coordinator_pricing = claude_pricing.get(coordinator_model, claude_pricing['claude-3-5-sonnet-20241022'])
        coordinator_input_cost = (coordinator_input_tokens / 1_000_000) * coordinator_pricing['input']
        coordinator_output_cost = (coordinator_output_tokens / 1_000_000) * coordinator_pricing['output']
        
        total_cost = agent_input_cost + agent_output_cost + coordinator_input_cost + coordinator_output_cost
        
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
        
        # Estimate token usage based on posts
        # Rough estimates: each post ~300 tokens, each comment ~50 tokens, 5 comments per post
        estimated_input_tokens = max_posts * (300 + 5 * 50) + 500  # +500 for prompt overhead
        estimated_output_tokens = 400  # Typical summary length
        
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
        
        # Handle free tier for Gemini
        if model == 'gemini-1.5-flash':
            # Check if within free tier limits (simplified check)
            total_cost = 0.0  # Assume free tier for cost estimation
            input_cost = 0.0
            output_cost = 0.0
        
        return jsonify({
            'search_mode': 'traditional_reddit_search',
            'estimated_tokens': {
                'input': estimated_input_tokens,
                'output': estimated_output_tokens,
                'total': estimated_input_tokens + estimated_output_tokens
            },
            'costs': {
                'reddit_api': reddit_cost,
                f'{ai_provider}_input': round(input_cost, 4),
                f'{ai_provider}_output': round(output_cost, 4),
                f'{ai_provider}_total': round(input_cost + output_cost, 4),
                'total': round(total_cost + reddit_cost, 4)
            },
            'model': model,
            'ai_provider': ai_provider,
            'posts': max_posts
        })

def call_ai_model(model: str, prompt: str, max_tokens: int = 1500):
    """
    Universal function to call either Claude or Gemini based on model name
    """
    if model.startswith('gemini-'):
        # Use Gemini API
        try:
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
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
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

# Multi-Agent Web Search System

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

def extract_subreddit_from_url(url: str) -> str:
    """Extract subreddit name from Reddit URL"""
    if 'reddit.com/r/' in url:
        try:
            return url.split('/r/')[1].split('/')[0]
        except IndexError:
            return 'unknown'
    return 'unknown'

async def web_search_agent(client, query: str, agent_id: int, search_focus: str):
    """
    Enhanced agent that searches for Reddit posts AND fetches their actual content
    """
    print(f"🤖 Agent {agent_id} STARTING: Web search + content analysis with focus '{search_focus}'")
    print(f"📝 Agent {agent_id} Query: '{query}'")
    
    try:
        # Create a focused search query based on the agent's specialty
        focused_query = f"{query} {search_focus} site:reddit.com"
        print(f"🔍 Agent {agent_id} Focused query: '{focused_query}'")
        
        # Enhanced prompt for web search + fetch workflow
        prompt_content = f"""You are a Reddit research specialist analyzing discussions about: "{query}"

Your search focus: {search_focus}

COMPREHENSIVE RESEARCH WORKFLOW:
1. SEARCH PHASE: Use web_search to find relevant Reddit discussions about "{query} {search_focus} site:reddit.com"
2. FETCH PHASE: Use web_fetch to access the actual content of the most relevant Reddit posts you find
3. ANALYSIS PHASE: Analyze the full discussions, comments, and community insights

Your specific focus: {search_focus}

DETAILED INSTRUCTIONS:
- Search for Reddit posts that match your focus area: {search_focus}
- Access the actual content of the most promising posts (up to 3-4 posts)
- Read through post content, top comments, and community discussions
- Extract specific recommendations, product mentions, prices, and consensus
- Identify patterns in community sentiment and advice

ANALYSIS GOALS:
- Find concrete recommendations related to "{query}"
- Extract specific product/brand names and prices mentioned
- Identify community consensus and popular opinions
- Note any warnings or common concerns raised
- Capture the overall sentiment and confidence level of recommendations

After your research, provide a detailed summary including:
- Key findings from the Reddit discussions you accessed
- Specific recommendations with context from the communities
- Product mentions with details and community feedback
- Price information and value assessments if mentioned
- Overall community sentiment and consensus level
- Citations to the specific posts you analyzed

Focus on providing actionable insights from real Reddit discussions about "{query}" with emphasis on {search_focus}."""

        print(f"📤 Agent {agent_id} Sending request to Claude with web search + fetch tools...")
        print(f"🔧 Agent {agent_id} Using model: claude-3-5-haiku-latest")
        print(f"🎯 Agent {agent_id} Max tokens: 3000")
        
        message = await asyncio.to_thread(
            client.messages.create,
            model="claude-3-5-haiku-latest",
            max_tokens=3000,  # Increased for content analysis
            messages=[{
                "role": "user", 
                "content": prompt_content
            }],
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 3
                },
                {
                    "type": "web_fetch_20250910",  # Add web fetch tool
                    "name": "web_fetch", 
                    "max_uses": 5,  # Allow fetching multiple pages
                    "citations": {"enabled": True}
                }
            ],
            extra_headers={
                "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"  # Both tools
            }
        )
        
        print(f"✅ Agent {agent_id} Received response from Claude")
        print(f"📊 Agent {agent_id} Response type: {type(message)}")
        print(f"📏 Agent {agent_id} Response content length: {len(message.content) if message.content else 0}")
        
        # Handle Claude response with tool use and text
        response_text = ""
        reddit_posts = []
        
        if message.content:
            for content_block in message.content:
                if content_block.type == "text":
                    response_text += content_block.text
                    print(f"� Agent {agent_id} Text response: {content_block.text[:200]}...")
                elif content_block.type == "tool_use":
                    print(f"🔧 Agent {agent_id} Tool use detected: {content_block.name}")
                    if content_block.name == "web_search":
                        print(f"🔍 Agent {agent_id} Web search tool executed")
                    elif content_block.name == "web_fetch":
                        print(f"📄 Agent {agent_id} Web fetch tool executed")
                        # Log fetch details for Reddit URLs
                        if hasattr(content_block, 'input') and content_block.input:
                            fetch_url = content_block.input.get('url', '')
                            if 'reddit.com' in fetch_url:
                                print(f"📄 Agent {agent_id} Fetching Reddit URL: {fetch_url}")
                        # The actual search results will be in the tool_result block
                        # For now, we'll process the text response that follows
        
        # Look for tool results in subsequent messages if needed
        # For now, parse any Reddit URLs found in the text response
        if response_text:
            import re
            reddit_urls = re.findall(r'https?://(?:www\.)?reddit\.com/r/\w+/comments/[\w/]+', response_text)
            print(f"� Agent {agent_id} Found {len(reddit_urls)} Reddit URLs in response")
            
            for url in reddit_urls[:5]:  # Limit to 5 URLs per agent
                # Extract basic info from URL structure
                subreddit = extract_subreddit_from_url(url)
                reddit_posts.append({
                    'url': url,
                    'title': f"Reddit post from r/{subreddit}",
                    'summary': "Post found via web search",
                    'subreddit': subreddit,
                    'relevance_score': 7,
                    'estimated_engagement': 'medium'
                })
                print(f"🎯 Agent {agent_id} Added Reddit post: {url}")
        
        # Add fallback error handling if no results found
        if len(reddit_posts) == 0:
            print(f"⚠️ Agent {agent_id} No Reddit posts found - debugging response structure")
            if message.content:
                for i, block in enumerate(message.content):
                    print(f"   Block {i}: type={block.type}")
                    if hasattr(block, 'text'):
                        print(f"   Text content: {block.text[:100]}...")
                    if hasattr(block, 'name'):
                        print(f"   Tool name: {block.name}")
                    if hasattr(block, 'input'):
                        print(f"   Tool input: {block.input}")
            
            # Still return a valid result even if no posts found
            result_data = {
                "agent_id": agent_id,
                "search_focus": search_focus,
                "reddit_posts": [],
                "search_strategy": f"Web search attempted for '{query}' with focus '{search_focus}' but no Reddit posts found",
                "total_posts_found": 0,
                "response_text": response_text[:500] if response_text else "No text response",
                "debug_info": {
                    "search_performed": True,  # Fixed: add default value
                    "response_length": len(response_text),
                    "content_blocks": len(message.content) if message.content else 0
                }
            }
        else:
            result_data = {
                "agent_id": agent_id,
                "search_focus": search_focus,
                "reddit_posts": reddit_posts,
                "search_strategy": f"Used web search to find Reddit posts about '{query}' with focus on {search_focus}",
                "total_posts_found": len(reddit_posts),
                "response_text": response_text[:500] if response_text else "No text response"
            }
        
        print(f"🎯 Agent {agent_id} COMPLETED successfully")
        print(f"📊 Agent {agent_id} Final result - Found {len(reddit_posts)} Reddit posts")
        for post in reddit_posts:
            print(f"   📌 {post['title'][:60]}... ({post['url']})")
        
        return {
            "agent_id": agent_id,
            "search_focus": search_focus,
            "response": response_text,
            "parsed_data": result_data,
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Agent {agent_id} FAILED with exception: {type(e).__name__}: {e}")
        import traceback
        print(f"📍 Agent {agent_id} Traceback: {traceback.format_exc()}")
        return {
            "agent_id": agent_id,
            "search_focus": search_focus,
            "error": str(e),
            "error_type": type(e).__name__,
            "success": False
        }

async def multi_agent_web_search(query: str, agent_count: int = 3):
    """
    Deploy multiple Haiku agents to search the web in parallel
    """
    print(f"🚀 MULTI-AGENT SEARCH STARTING")
    print(f"📝 Query: '{query}'")
    print(f"🤖 Agent count: {agent_count}")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define different search focuses for agents
    search_focuses = [
        "recent discussions 2024 2023",
        "best recommendations highly upvoted",
        "detailed reviews comparison",
        "community consensus popular",
        "expert opinions detailed analysis"
    ]
    
    print(f"🎯 Available search focuses: {search_focuses}")
    
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        print(f"✅ Anthropic client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Anthropic client: {e}")
        return {
            "agent_results": [],
            "success_rate": 0,
            "error": f"Client initialization failed: {e}"
        }
    
    # Create tasks for parallel execution
    tasks = []
    print(f"🏗️ Creating agent tasks...")
    for i in range(agent_count):
        focus = search_focuses[i % len(search_focuses)]
        print(f"📋 Agent {i+1}: Focus = '{focus}'")
        task = web_search_agent(client, query, i+1, focus)
        tasks.append(task)
    
    print(f"⚡ LAUNCHING {len(tasks)} agents in parallel...")
    start_time = datetime.now()
    
    try:
        # Execute all agents in parallel
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        print(f"⏱️ All agents completed in {execution_time:.2f} seconds")
        
    except Exception as e:
        print(f"❌ Error during parallel execution: {e}")
        return {
            "agent_results": [],
            "success_rate": 0,
            "error": f"Parallel execution failed: {e}"
        }
    
    # Process results with detailed logging
    print(f"📊 PROCESSING AGENT RESULTS")
    successful_results = []
    failed_results = []
    total_reddit_posts = 0
    
    for i, result in enumerate(agent_results):
        agent_num = i + 1
        print(f"\n--- Agent {agent_num} Result Analysis ---")
        
        if isinstance(result, Exception):
            print(f"❌ Agent {agent_num}: Exception occurred: {result}")
            failed_results.append({
                "agent_id": agent_num,
                "error": str(result),
                "error_type": "Exception"
            })
        elif isinstance(result, dict):
            if result.get("success", False):
                print(f"✅ Agent {agent_num}: SUCCESS")
                parsed_data = result.get("parsed_data", {})
                reddit_posts = parsed_data.get("reddit_posts", [])
                print(f"📊 Agent {agent_num}: Found {len(reddit_posts)} Reddit posts")
                
                if reddit_posts:
                    for j, post in enumerate(reddit_posts):
                        print(f"   📌 Post {j+1}: {post.get('title', 'No title')[:50]}...")
                        print(f"      🔗 URL: {post.get('url', 'No URL')}")
                        print(f"      📍 Subreddit: r/{post.get('subreddit', 'unknown')}")
                        
                total_reddit_posts += len(reddit_posts)
                successful_results.append(result)
            else:
                print(f"❌ Agent {agent_num}: FAILED")
                error_msg = result.get("error", "Unknown error")
                error_type = result.get("error_type", "Unknown")
                print(f"   💥 Error: {error_type}: {error_msg}")
                failed_results.append(result)
        else:
            print(f"❌ Agent {agent_num}: Invalid result type: {type(result)}")
            failed_results.append({
                "agent_id": agent_num,
                "error": f"Invalid result type: {type(result)}",
                "error_type": "TypeError"
            })
    
    success_rate = len(successful_results) / len(agent_results) if agent_results else 0
    
    print(f"\n🎯 MULTI-AGENT SEARCH SUMMARY")
    print(f"✅ Successful agents: {len(successful_results)}/{len(agent_results)}")
    print(f"❌ Failed agents: {len(failed_results)}/{len(agent_results)}")
    print(f"📊 Success rate: {success_rate*100:.1f}%")
    print(f"🔗 Total Reddit posts found: {total_reddit_posts}")
    print(f"⏱️ Total execution time: {execution_time:.2f}s")
    
    return {
        "agent_results": agent_results,
        "successful_results": successful_results,
        "failed_results": failed_results,
        "success_rate": success_rate,
        "total_reddit_posts": total_reddit_posts,
        "execution_time": execution_time
    }
    
    for result in agent_results:
        if isinstance(result, Exception):
            failed_results.append({"error": str(result)})
        elif result.get("success"):
            successful_results.append(result)
        else:
            failed_results.append(result)
    
    print(f"📊 Agent Results: {len(successful_results)} succeeded, {len(failed_results)} failed")
    
    return {
        "successful_agents": successful_results,
        "failed_agents": failed_results,
        "total_agents": agent_count,
        "success_rate": len(successful_results) / agent_count
    }

async def coordinate_agent_results(agent_results: dict, query: str, coordinator_model: str):
    """
    Use a Sonnet/Opus agent to synthesize all agent findings
    """
    print(f"\n🧠 COORDINATOR STARTING")
    print(f"🤖 Model: {coordinator_model}")
    print(f"📝 Query: '{query}'")
    print(f"📊 Processing results from {len(agent_results.get('agent_results', []))} agents")
    
    successful_agents = agent_results.get("successful_results", [])
    failed_agents = agent_results.get("failed_results", [])
    
    print(f"✅ Successful agents: {len(successful_agents)}")
    print(f"❌ Failed agents: {len(failed_agents)}")
    
    if not successful_agents:
        print(f"💥 No successful agents - cannot coordinate results")
        return {
            "success": False,
            "error": "No successful agents to coordinate",
            "agent_summary": {
                "total_searches": len(agent_results.get('agent_results', [])),
                "successful_searches": 0,
                "failed_searches": len(failed_agents)
            }
        }
    
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        print(f"✅ Anthropic client initialized for coordinator")
    except Exception as e:
        print(f"❌ Failed to initialize coordinator client: {e}")
        return {
            "success": False,
            "error": f"Coordinator client initialization failed: {e}",
            "agent_summary": {
                "total_searches": len(agent_results.get('agent_results', [])),
                "successful_searches": len(successful_agents),
                "failed_searches": len(failed_agents)
            }
        }
    
    # Prepare agent data for coordinator with detailed extraction
    print(f"📋 Preparing agent data for coordinator...")
    agent_data = ""
    total_reddit_posts = 0
    all_reddit_urls = []
    
    for i, agent in enumerate(successful_agents):
        agent_id = agent.get('agent_id', i+1)
        search_focus = agent.get('search_focus', 'Unknown focus')
        parsed_data = agent.get('parsed_data', {})
        reddit_posts = parsed_data.get('reddit_posts', [])
        
        print(f"📊 Agent {agent_id}: {len(reddit_posts)} Reddit posts found")
        
        agent_data += f"\n=== AGENT {agent_id} FINDINGS ===\n"
        agent_data += f"Search Focus: {search_focus}\n"
        agent_data += f"Posts Found: {len(reddit_posts)}\n"
        
        if reddit_posts:
            agent_data += "Reddit Posts:\n"
            for j, post in enumerate(reddit_posts):
                url = post.get('url', '')
                title = post.get('title', 'No title')
                subreddit = post.get('subreddit', 'unknown')
                summary = post.get('summary', 'No summary')
                
                agent_data += f"  {j+1}. {title}\n"
                agent_data += f"     URL: {url}\n"
                agent_data += f"     Subreddit: r/{subreddit}\n"
                agent_data += f"     Summary: {summary}\n\n"
                
                if url and 'reddit.com' in url:
                    all_reddit_urls.append(url)
                    
            total_reddit_posts += len(reddit_posts)
        else:
            agent_data += "No Reddit posts found\n"
            
        search_strategy = parsed_data.get('search_strategy', 'No strategy provided')
        agent_data += f"Search Strategy: {search_strategy}\n\n"
    
    if failed_agents:
        agent_data += f"\n=== FAILED AGENTS ({len(failed_agents)}) ===\n"
        for agent in failed_agents:
            agent_id = agent.get('agent_id', 'Unknown')
            error = agent.get('error', 'Unknown error')
            error_type = agent.get('error_type', 'Unknown type')
            agent_data += f"Agent {agent_id}: {error_type} - {error}\n"
    
    print(f"🔗 Total Reddit URLs collected: {len(all_reddit_urls)}")
    print(f"📊 Total Reddit posts: {total_reddit_posts}")
    
    coordinator_prompt = f"""You are the coordinator agent responsible for synthesizing findings from multiple web search agents.

QUERY: "{query}"

SEARCH SUMMARY:
- Total agents deployed: {len(agent_results.get('agent_results', []))}
- Successful agents: {len(successful_agents)}
- Failed agents: {len(failed_agents)}
- Total Reddit posts found: {total_reddit_posts}
- Total Reddit URLs: {len(all_reddit_urls)}

AGENT SEARCH RESULTS:
{agent_data}

CRITICAL ANALYSIS REQUIRED:
Based on the agent findings above, provide a comprehensive analysis that includes:

1. **SEARCH EFFECTIVENESS**: How well did the agents perform? Were they able to find relevant Reddit content?

2. **REDDIT CONTENT ANALYSIS**: Analyze the quality and relevance of Reddit posts found
   - Extract key themes and recommendations
   - Identify most valuable discussions
   - Note community consensus where present

3. **RECOMMENDATIONS**: Based on the Reddit discussions found, what are the top recommendations for "{query}"?

4. **LIMITATIONS**: What limitations exist in this search (failed agents, lack of results, etc.)?

5. **CONFIDENCE LEVEL**: How confident are you in these recommendations given the available data?

If agents failed to find meaningful Reddit content, clearly state this and explain why the search was ineffective.

Please provide a thorough analysis even if the search results were limited."""

    print(f"📤 Sending coordination request to {coordinator_model}...")
    
    try:
        message = await asyncio.to_thread(
            client.messages.create,
            model=coordinator_model,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": coordinator_prompt
            }]
        )
        
        print(f"✅ Coordinator response received")
        print(f"📏 Response length: {len(message.content[0].text) if message.content else 0}")
        
        coordinator_analysis = message.content[0].text if message.content else "No response from coordinator"
        
        agent_summary = {
            "total_searches": len(agent_results.get('agent_results', [])),
            "successful_searches": len(successful_agents),
            "failed_searches": len(failed_agents),
            "total_reddit_posts": total_reddit_posts,
            "total_reddit_urls": len(all_reddit_urls),
            "execution_time": agent_results.get('execution_time', 0)
        }
        
        print(f"🎯 COORDINATION COMPLETE")
        print(f"📊 Agent summary: {agent_summary}")
        
        return {
            "success": True,
            "coordinator_analysis": coordinator_analysis,
            "agent_summary": agent_summary,
            "reddit_urls_found": all_reddit_urls
        }
        
    except Exception as e:
        print(f"❌ Coordinator failed: {type(e).__name__}: {e}")
        import traceback
        print(f"📍 Coordinator traceback: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": f"Coordinator failed: {e}",
            "agent_summary": {
                "total_searches": len(agent_results.get('agent_results', [])),
                "successful_searches": len(successful_agents),
                "failed_searches": len(failed_agents),
                "total_reddit_posts": total_reddit_posts,
                "total_reddit_urls": len(all_reddit_urls)
            }
        }

# Enhanced search functions with browser automation and recency scoring

def calculate_recency_score(post_age_days: int) -> float:
    """
    Calculate recency score (0-1) based on post age
    """
    if post_age_days <= 30:      # Last month
        return 1.0
    elif post_age_days <= 90:    # Last 3 months  
        return 0.8
    elif post_age_days <= 365:   # Last year
        return 0.6
    elif post_age_days <= 730:   # Last 2 years
        return 0.4
    else:                        # Older than 2 years
        return 0.1

async def search_google_with_browser(query: str, max_posts: int = 5):
    """
    Use headless browser to search Google for Reddit posts with better filtering
    """
    print(f"🎭 Starting browser search for: '{query}'")
    
    try:
        async with async_playwright() as p:
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            # Construct search with time filtering for recent results
            search_params = {
                'q': f'{query} site:reddit.com',
                'num': str(max_posts * 2),  # Get more to filter
                'tbs': 'qdr:y2',  # Last 2 years for more current results
                'hl': 'en'
            }
            
            search_url = f"https://www.google.com/search?{urlencode(search_params)}"
            print(f"🔍 Browser search URL: {search_url}")
            
            # Navigate to Google search
            await page.goto(search_url, wait_until='networkidle', timeout=30000)
            
            # Wait for results to load
            await page.wait_for_selector('div[data-ved]', timeout=15000)
            
            # Extract search result links
            links = await page.evaluate('''
                () => {
                    const results = [];
                    const searchResults = document.querySelectorAll('div[data-ved] a[href*="reddit.com"]');
                    
                    for (const link of searchResults) {
                        const href = link.href;
                        const title = link.textContent || '';
                        const parent = link.closest('div[data-ved]');
                        const snippet = parent?.querySelector('span[style*="-webkit-line-clamp"]')?.textContent || '';
                        
                        if (href && href.includes('reddit.com/r/') && href.includes('/comments/')) {
                            results.push({
                                url: href,
                                title: title,
                                snippet: snippet
                            });
                        }
                    }
                    
                    return results;
                }
            ''')
            
            await browser.close()
            
            print(f"🔗 Browser found {len(links)} Reddit links")
            for i, link in enumerate(links[:3]):
                print(f"  {i+1}. {link['title'][:80]}...")
                print(f"     URL: {link['url']}")
            
            # Extract Reddit URLs and limit to max_posts
            reddit_urls = [link['url'] for link in links][:max_posts]
            
            return reddit_urls
            
    except Exception as e:
        print(f"❌ Browser search failed: {e}")
        print(f"📚 Falling back to requests-based search...")
        return await search_google_with_fallback(query, max_posts)

async def search_google_with_fallback(query: str, max_posts: int = 5):
    """
    Fallback to requests-based search with better time filtering
    """
    try:
        # Try multiple search strategies for current content
        search_queries = [
            f'{query} site:reddit.com after:2022',  # Recent content
            f'{query} site:reddit.com 2024',        # This year
            f'{query} site:reddit.com recent',      # Recent discussions
            f'{query} site:reddit.com',             # Fallback
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        all_urls = []
        
        for search_query in search_queries:
            if len(all_urls) >= max_posts:
                break
                
            print(f"🔍 Trying fallback search: {search_query}")
            
            search_url = f"https://www.google.com/search?q={quote(search_query)}&num={max_posts}"
            
            try:
                response = requests.get(search_url, headers=headers, timeout=10)
                
                # Extract Reddit URLs using regex
                patterns = [
                    r'https://(?:www\.)?reddit\.com/r/[^/]+/comments/[^/\s"\'<>&]+',
                    r'reddit\.com/r/[^/]+/comments/[^/\s"\'<>&]+',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, response.text)
                    for match in matches:
                        if match.startswith('reddit.com'):
                            match = f"https://{match}"
                        
                        if match not in all_urls and len(all_urls) < max_posts:
                            all_urls.append(match)
                            print(f"  ✅ Fallback found: {match}")
                            
            except Exception as e:
                print(f"  ❌ Fallback query failed: {e}")
                continue
        
        return all_urls[:max_posts]
        
    except Exception as e:
        print(f"❌ All fallback searches failed: {e}")
        return []

def search_google_for_reddit_posts(query, num_results=5):
    """Search Google for Reddit posts related to the query"""
    try:
        # Add site:reddit.com to search only Reddit
        google_query = f"{query} site:reddit.com"
        print(f"🔍 Google search query: {google_query}")
        
        # Use a simple Google search approach
        # Note: For production, you'd want to use Google Custom Search API
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # Search Google (this is a simplified approach)
        search_url = f"https://www.google.com/search?q={requests.utils.quote(google_query)}&num={num_results}"
        print(f"🌐 Search URL: {search_url}")
        
        print("📡 Making request to Google...")
        response = requests.get(search_url, headers=headers, timeout=15)
        print(f"📊 Response status: {response.status_code}")
        print(f"📏 Response length: {len(response.text)} characters")
        
        response.raise_for_status()
        
        # Save response for debugging
        print("💾 Saving response snippet for debugging...")
        response_snippet = response.text[:2000]
        print(f"📄 Response snippet: {response_snippet}")
        
        # Extract Reddit URLs from the search results
        reddit_urls = []
        
        # Try multiple patterns to find Reddit URLs
        patterns = [
            r'https://(?:www\.)?reddit\.com/r/[^/]+/comments/[^/\s"\'<>&]+',
            r'reddit\.com/r/[^/]+/comments/[^/\s"\'<>&]+',
            r'/r/[^/]+/comments/[^/\s"\'<>&]+',
        ]
        
        print("🔎 Searching for Reddit URLs with patterns...")
        all_matches = []
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, response.text)
            print(f"Pattern {i+1}: Found {len(matches)} matches")
            if matches:
                print(f"  First few matches: {matches[:3]}")
            all_matches.extend(matches)
        
        # Normalize URLs
        for match in all_matches:
            if match.startswith('http'):
                url = match
            elif match.startswith('reddit.com'):
                url = f"https://{match}"
            elif match.startswith('/r/'):
                url = f"https://reddit.com{match}"
            else:
                continue
                
            # Clean up URL (remove trailing characters)
            url = re.sub(r'[^\w\-\./:]', '', url.split()[0])
            
            if url not in [u for u in reddit_urls] and len(reddit_urls) < num_results:
                reddit_urls.append(url)
                print(f"✅ Added URL: {url}")
        
        print(f"🎯 Final Reddit URLs found: {len(reddit_urls)}")
        for i, url in enumerate(reddit_urls):
            print(f"  {i+1}. {url}")
        
        return reddit_urls
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return []
    except Exception as e:
        print(f"❌ Error searching Google: {e}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return []

def search_duckduckgo_for_reddit_posts(query, num_results=5):
    """Fallback: Search DuckDuckGo for Reddit posts"""
    try:
        search_query = f"{query} site:reddit.com"
        print(f"🦆 DuckDuckGo search query: {search_query}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        search_url = f"https://duckduckgo.com/html/?q={requests.utils.quote(search_query)}"
        print(f"🌐 DuckDuckGo URL: {search_url}")
        
        response = requests.get(search_url, headers=headers, timeout=15)
        print(f"📊 DuckDuckGo response status: {response.status_code}")
        
        response.raise_for_status()
        
        # Extract Reddit URLs
        reddit_urls = []
        pattern = r'https://(?:www\.)?reddit\.com/r/[^/]+/comments/[^/\s"\'<>&]+'
        matches = re.findall(pattern, response.text)
        
        seen_urls = set()
        for match in matches:
            if match not in seen_urls and len(reddit_urls) < num_results:
                seen_urls.add(match)
                reddit_urls.append(match)
                print(f"✅ DuckDuckGo found: {match}")
        
        print(f"🦆 DuckDuckGo found {len(reddit_urls)} URLs")
        return reddit_urls
        
    except Exception as e:
        print(f"❌ DuckDuckGo search error: {e}")
        return []

def get_reddit_post_from_url(reddit, url):
    """Get Reddit post object from URL"""
    try:
        print(f"🔗 Processing URL: {url}")
        
        # Extract post ID from URL
        # URL format: https://reddit.com/r/subreddit/comments/post_id/title/
        url_parts = url.split('/')
        print(f"📂 URL parts: {url_parts}")
        
        if 'comments' in url_parts:
            post_id_index = url_parts.index('comments') + 1
            if post_id_index < len(url_parts):
                post_id = url_parts[post_id_index]
                print(f"🆔 Extracted post ID: {post_id}")
                
                print(f"📡 Fetching Reddit post...")
                submission = reddit.submission(id=post_id)
                
                # Try to access a property to ensure the post exists
                title = submission.title
                print(f"✅ Successfully got post: {title[:50]}...")
                return submission
        
        print(f"❌ Could not extract post ID from URL: {url}")
        return None
        
    except Exception as e:
        print(f"❌ Error getting post from URL {url}: {e}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return None

# Enhanced Link Discovery Functions

def extract_link_enhancement_data(ai_response):
    """Extract structured JSON data from AI response for link enhancement"""
    try:
        # Look for JSON block in the response
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, ai_response, re.DOTALL)
        
        if match:
            import json
            json_str = match.group(1)
            data = json.loads(json_str)
            print(f"🔗 Extracted link enhancement data: {len(data.get('search_terms', []))} search terms, {len(data.get('reddit_links', []))} Reddit links")
            return data
        else:
            print("⚠️ No JSON block found in AI response for link enhancement")
            return {"reddit_links": [], "search_terms": []}
    
    except Exception as e:
        print(f"❌ Error extracting link enhancement data: {e}")
        return {"reddit_links": [], "search_terms": []}

def get_firebase_secret(secret_name):
    """Get Firebase secret value for local development"""
    try:
        import subprocess
        result = subprocess.run(
            ["firebase", "functions:secrets:access", secret_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"⚠️ Failed to get Firebase secret '{secret_name}': {result.stderr}")
            return None
    except Exception as e:
        print(f"⚠️ Error accessing Firebase secret '{secret_name}': {e}")
        return None

def search_google_for_product_links(search_term, max_results=3):
    """Search Google Custom Search API for product links related to a search term"""
    try:
        # Get Google Search API credentials from Firebase secrets
        api_key = get_firebase_secret("GOOGLE_SEARCH_API_KEY")
        search_engine_id = get_firebase_secret("GOOGLE_SEARCH_ENGINE_ID")
        
        if not api_key or not search_engine_id:
            print(f"⚠️ Google Search API credentials not available from Firebase secrets. API key: {bool(api_key)}, Engine ID: {bool(search_engine_id)}")
            # Fallback to creating basic links without search
            return create_fallback_product_links(search_term)
        
        # Create a focused product search query
        product_query = f"{search_term} buy review store price"
        print(f"🛍️ Searching Google Custom Search API for: '{product_query}'")
        
        # Use Google Custom Search API
        api_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': product_query,
            'num': min(max_results * 2, 10),  # API max is 10, get extra to filter
            'fields': 'items(title,link,snippet)'  # Get what we need for filtering
        }
        
        response = requests.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        found_links = []
        
        # Filter for e-commerce and review sites
        target_domains = {
            'amazon.com', 'bestbuy.com', 'target.com', 'walmart.com', 
            'newegg.com', 'ebay.com', 'wirecutter.com', 'cnet.com', 
            'techradar.com', 'pcmag.com', 'tomsguide.com', 'tomshardware.com'
        }
        
        if 'items' in data:
            seen_domains = set()
            for item in data['items']:
                link = item.get('link', '')
                title = item.get('title', '')
                
                # Extract domain from URL
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(link).netloc.lower()
                    # Remove 'www.' prefix
                    domain = domain.replace('www.', '')
                    
                    # Check if it's a target domain and we haven't seen this domain yet
                    if domain in target_domains and domain not in seen_domains:
                        found_links.append(link)
                        seen_domains.add(domain)
                        print(f"✅ Found product link: {link}")
                        
                        if len(found_links) >= max_results:
                            break
                            
                except Exception as e:
                    print(f"⚠️ Error parsing URL {link}: {e}")
                    continue
        
        print(f"🎯 Found {len(found_links)} product links for '{search_term}'")
        
        # If no links found via API, use fallback links
        if not found_links:
            print(f"🔄 No API links found for '{search_term}', using fallback links")
            return create_fallback_product_links(search_term)
            
        return found_links
        
    except Exception as e:
        print(f"❌ Error searching Google API for '{search_term}': {e}")
        return create_fallback_product_links(search_term)

def create_fallback_product_links(search_term):
    """Create fallback product links when Google API is not available"""
    # Create basic search links for major retailers
    from urllib.parse import quote
    encoded_term = quote(search_term)
    
    fallback_links = [
        f"https://www.amazon.com/s?k={encoded_term}",
        f"https://www.bestbuy.com/site/searchpage.jsp?st={encoded_term}",
        f"https://www.target.com/s?searchTerm={encoded_term}"
    ]
    
    print(f"🔗 Created {len(fallback_links)} fallback links for '{search_term}'")
    return fallback_links

def curate_links_with_ai(search_term, found_links, model="gemini-1.5-flash"):
    """Use AI to evaluate and curate the best links for a search term"""
    if not found_links:
        return []
    
    try:
        prompt = f"""Evaluate these links for the search term "{search_term}" and select the most relevant and helpful ones.

Search term: {search_term}
Found links: {found_links}

Please evaluate each link and select only the most relevant ones based on:
1. Relevance to the search term
2. Trustworthiness of the domain
3. Likelihood to be helpful for someone researching "{search_term}"

Return a JSON array of the best links (maximum 2-3 links) in this format:
```json
[
  {{
    "url": "https://example.com/product",
    "relevance_score": 9,
    "description": "Official product page with detailed specs"
  }}
]
```

Focus on official stores, reputable review sites, and direct product pages. Avoid affiliate or spam links."""

        response = call_ai_model(model, prompt, max_tokens=500)
        
        # Extract JSON from response
        json_pattern = r'```json\s*(\[.*?\])\s*```'
        match = re.search(json_pattern, response, re.DOTALL)
        
        if match:
            import json
            curated_links = json.loads(match.group(1))
            print(f"🎯 AI curated {len(curated_links)} links for '{search_term}'")
            return curated_links
        else:
            print(f"⚠️ No valid JSON found in AI response for '{search_term}'")
            return [{"url": link, "relevance_score": 5, "description": "Product link"} for link in found_links[:2]]
    
    except Exception as e:
        print(f"❌ Error curating links for '{search_term}': {e}")
        # Return basic structure if AI fails
        return [{"url": link, "relevance_score": 5, "description": "Product link"} for link in found_links[:2]]

def enhance_summary_with_links(summary, search_terms, enhanced_links):
    """Add enhanced link data to the response"""
    return {
        "enhanced_summary": summary,
        "extracted_terms": search_terms,
        "enhanced_links": enhanced_links,
        "link_enhancement_enabled": True
    }

def analyze_reddit_data(submissions, query):
    """Perform comprehensive analysis of Reddit data"""
    analysis = {
        'post_metrics': {},
        'engagement_analysis': {},
        'content_analysis': {},
        'temporal_analysis': {},
        'community_analysis': {},
        'sentiment_indicators': {}
    }
    
    print("📊 Starting comprehensive data analysis...")
    
    # Collect all data points
    all_posts = []
    all_comments = []
    brands_mentioned = []
    price_mentions = []
    sentiment_words = {
        'positive': ['great', 'excellent', 'amazing', 'perfect', 'best', 'love', 'awesome', 'fantastic', 'recommend', 'good'],
        'negative': ['terrible', 'awful', 'worst', 'hate', 'bad', 'horrible', 'disappointing', 'cheap', 'poor', 'avoid']
    }
    
    for submission in submissions:
        # Post-level data
        post_data = {
            'id': submission.id,
            'title': submission.title,
            'score': submission.score,
            'upvote_ratio': submission.upvote_ratio,
            'num_comments': submission.num_comments,
            'created_utc': submission.created_utc,
            'subreddit': str(submission.subreddit),
            'author': str(submission.author) if submission.author else '[deleted]',
            'selftext': submission.selftext,
            'url': submission.url,
            'is_self': submission.is_self,
            'comments': []
        }
        
        # Age calculation
        post_age_days = (datetime.now(timezone.utc).timestamp() - submission.created_utc) / (24 * 3600)
        post_data['age_days'] = post_age_days
        
        # Extract brand mentions and prices from post
        text_content = f"{submission.title} {submission.selftext}".lower()
        
        # Common brands (expandable)
        brand_patterns = [
            r'\b(uniqlo|nike|adidas|gap|h&m|zara|target|walmart|amazon|costco)\b',
            r'\b(everlane|patagonia|levi\'?s?|wrangler|carhartt|dickies)\b',
            r'\b(supreme|palace|off-white|gucci|prada|louis vuitton)\b',
            r'\b(next level|bella canvas|hanes|fruit of the loom|gildan)\b'
        ]
        
        for pattern in brand_patterns:
            brands_mentioned.extend(re.findall(pattern, text_content))
        
        # Price extraction
        price_patterns = [
            r'\$(\d+(?:\.\d{2})?)',
            r'(\d+(?:\.\d{2})?) dollars?',
            r'(\d+(?:\.\d{2})?) bucks?'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                try:
                    price = float(match)
                    if 1 <= price <= 1000:  # Reasonable t-shirt price range
                        price_mentions.append(price)
                except:
                    pass
        
        # Process comments
        submission.comments.replace_more(limit=0)
        comment_scores = []
        comment_count = 0
        
        for comment in submission.comments.list():
            if comment_count >= 10:  # Analyze top 10 comments
                break
                
            comment_data = {
                'id': comment.id,
                'body': comment.body,
                'score': comment.score,
                'created_utc': comment.created_utc,
                'author': str(comment.author) if comment.author else '[deleted]',
                'is_submitter': comment.is_submitter
            }
            
            # Comment age
            comment_age_days = (datetime.now(timezone.utc).timestamp() - comment.created_utc) / (24 * 3600)
            comment_data['age_days'] = comment_age_days
            
            # Extract brands and prices from comments
            comment_text = comment.body.lower()
            for pattern in brand_patterns:
                brands_mentioned.extend(re.findall(pattern, comment_text))
            
            for pattern in price_patterns:
                matches = re.findall(pattern, comment_text)
                for match in matches:
                    try:
                        price = float(match)
                        if 1 <= price <= 1000:
                            price_mentions.append(price)
                    except:
                        pass
            
            comment_scores.append(comment.score)
            post_data['comments'].append(comment_data)
            all_comments.append(comment_data)
            comment_count += 1
        
        post_data['comment_scores'] = comment_scores
        all_posts.append(post_data)
    
    # POST METRICS ANALYSIS
    post_scores = [p['score'] for p in all_posts]
    post_comment_counts = [p['num_comments'] for p in all_posts]
    post_ages = [p['age_days'] for p in all_posts]
    upvote_ratios = [p['upvote_ratio'] for p in all_posts]
    
    analysis['post_metrics'] = {
        'total_posts': len(all_posts),
        'avg_score': round(statistics.mean(post_scores), 1) if post_scores else 0,
        'median_score': round(statistics.median(post_scores), 1) if post_scores else 0,
        'max_score': max(post_scores) if post_scores else 0,
        'total_upvotes': sum(post_scores),
        'avg_comments': round(statistics.mean(post_comment_counts), 1) if post_comment_counts else 0,
        'total_comments': sum(post_comment_counts),
        'avg_upvote_ratio': round(statistics.mean(upvote_ratios), 2) if upvote_ratios else 0,
        'avg_post_age_days': round(statistics.mean(post_ages), 1) if post_ages else 0
    }
    
    # ENGAGEMENT ANALYSIS
    all_comment_scores = [c['score'] for c in all_comments]
    analysis['engagement_analysis'] = {
        'total_comments_analyzed': len(all_comments),
        'avg_comment_score': round(statistics.mean(all_comment_scores), 1) if all_comment_scores else 0,
        'median_comment_score': round(statistics.median(all_comment_scores), 1) if all_comment_scores else 0,
        'highly_upvoted_comments': len([s for s in all_comment_scores if s >= 10]),
        'engagement_rate': round(sum(post_comment_counts) / sum(post_scores) * 100, 2) if sum(post_scores) > 0 else 0,
        'comments_per_post': round(statistics.mean(post_comment_counts), 1) if post_comment_counts else 0
    }
    
    # CONTENT ANALYSIS
    brand_counter = Counter(brands_mentioned)
    top_brands = brand_counter.most_common(10)
    
    price_analysis = {}
    if price_mentions:
        price_analysis = {
            'prices_found': len(price_mentions),
            'avg_price': round(statistics.mean(price_mentions), 2),
            'median_price': round(statistics.median(price_mentions), 2),
            'min_price': min(price_mentions),
            'max_price': max(price_mentions),
            'price_range': f"${min(price_mentions):.2f} - ${max(price_mentions):.2f}"
        }
    
    analysis['content_analysis'] = {
        'top_brands': top_brands,
        'total_brand_mentions': len(brands_mentioned),
        'unique_brands': len(brand_counter),
        'price_analysis': price_analysis
    }
    
    # TEMPORAL ANALYSIS with enhanced recency scoring
    recent_posts = [p for p in all_posts if p['age_days'] <= 30]
    old_posts = [p for p in all_posts if p['age_days'] > 365]
    
    # Calculate recency-weighted metrics
    total_weighted_score = 0
    total_weight = 0
    post_recency_data = []
    
    for post in all_posts:
        age_days = post['age_days']
        recency_score = calculate_recency_score(age_days)
        weight = post['score'] * recency_score  # Weight by both upvotes and recency
        
        total_weighted_score += weight
        total_weight += post['score']
        
        post_recency_data.append({
            'id': post['id'],
            'age_days': age_days,
            'recency_score': recency_score,
            'weighted_score': weight,
            'age_category': 'recent' if age_days <= 365 else 'historical'
        })
    
    # Calculate recency-weighted freshness
    recency_weighted_freshness = (total_weighted_score / total_weight * 100) if total_weight > 0 else 0
    
    analysis['temporal_analysis'] = {
        'recent_posts_30d': len(recent_posts),
        'old_posts_1y+': len(old_posts),
        'avg_recent_score': round(statistics.mean([p['score'] for p in recent_posts]), 1) if recent_posts else 0,
        'freshness_score': round((len(recent_posts) / len(all_posts)) * 100, 1) if all_posts else 0,
        'recency_weighted_freshness': round(recency_weighted_freshness, 1),
        'post_recency_data': post_recency_data,
        'data_age_warning': recency_weighted_freshness < 30  # Flag if mostly outdated content
    }
    
    # COMMUNITY ANALYSIS
    subreddits = [p['subreddit'] for p in all_posts]
    subreddit_counter = Counter(subreddits)
    
    analysis['community_analysis'] = {
        'subreddits_involved': list(subreddit_counter.keys()),
        'primary_subreddit': subreddit_counter.most_common(1)[0] if subreddit_counter else None,
        'community_diversity': len(subreddit_counter)
    }
    
    # SENTIMENT INDICATORS
    all_text = " ".join([p['title'] + " " + p['selftext'] for p in all_posts] + 
                       [c['body'] for c in all_comments]).lower()
    
    positive_count = sum(all_text.count(word) for word in sentiment_words['positive'])
    negative_count = sum(all_text.count(word) for word in sentiment_words['negative'])
    
    analysis['sentiment_indicators'] = {
        'positive_word_count': positive_count,
        'negative_word_count': negative_count,
        'sentiment_ratio': round(positive_count / max(negative_count, 1), 2),
        'overall_sentiment': 'positive' if positive_count > negative_count else 'negative' if negative_count > positive_count else 'neutral'
    }
    
    print(f"✅ Analysis complete: {len(all_posts)} posts, {len(all_comments)} comments analyzed")
    return analysis

@app.route('/api/search-summarize', methods=['POST'])
def search_summarize():
    data = request.get_json()
    query = data.get('query')
    max_posts = data.get('max_posts', 3)  # Default to 3 posts
    model = data.get('model', 'claude-3-5-sonnet-20241022')  # Default to latest Sonnet
    
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
    
    # Only validate coordinator model for web search mode
    if use_web_search and not is_model_allowed(coordinator_model, user_tier):
        if user_tier == 'anonymous':
            return jsonify({'error': 'This coordinator model requires sign-in.'}), 403
        elif user_tier == 'free':
            return jsonify({'error': 'This coordinator model requires a paid subscription.'}), 403

    print(f"🔍 Search request: query='{query}', max_posts={max_posts}, model={model}")
    if use_web_search:
        print(f"🌐 Web search mode: {agent_count} agents, coordinator={coordinator_model}")

    try:
        if use_web_search:
            # Multi-agent web search mode
            return handle_web_search_mode(query, max_posts, model, agent_count, coordinator_model)
        else:
            # Traditional Reddit search mode
            return handle_traditional_search_mode(query, max_posts, model)
            
    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

def handle_web_search_mode(query: str, max_posts: int, model: str, agent_count: int, coordinator_model: str):
    """
    Handle multi-agent web search mode
    """
    print(f"🌐 Starting multi-agent web search mode...")
    
    try:
        # Deploy multiple Haiku agents for web search
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run multi-agent search
        agent_results = loop.run_until_complete(multi_agent_web_search(query, agent_count))
        
        # Coordinate results with Sonnet/Opus
        coordinator_results = loop.run_until_complete(
            coordinate_agent_results(agent_results, query, coordinator_model)
        )
        
        loop.close()
        
        if not coordinator_results.get("success"):
            return jsonify({
                'error': 'Web search coordination failed',
                'details': coordinator_results.get("error", "Unknown error"),
                'agent_summary': coordinator_results.get("agent_summary", {})
            }), 500
        
        # Return web search results
        return jsonify({
            'summary': coordinator_results["coordinator_analysis"],
            'sources': [],  # Web search doesn't use traditional sources
            'search_mode': 'multi_agent_web_search',
            'agent_summary': coordinator_results["agent_summary"],
            'analysis': {
                'search_method': 'multi_agent_web_search',
                'agent_count': agent_count,
                'coordinator_model': coordinator_model,
                'success_rate': agent_results["success_rate"]
            }
        })
        
    except Exception as e:
        print(f"❌ Web search mode failed: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': f'Web search mode failed: {str(e)}',
            'search_mode': 'multi_agent_web_search'
        }), 500

def handle_traditional_search_mode(query: str, max_posts: int, model: str):
    """
    Handle traditional Reddit search mode (existing logic)
    """
    try:
        # Reddit API setup
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT"),
        )

        # Search with enhanced browser-based approach for better recency
        print(f"🔍 Starting enhanced search for query: '{query}'")
        
        # Try browser search first for better results
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            reddit_urls = loop.run_until_complete(search_google_with_browser(query, max_posts*2))
            loop.close()
        except Exception as e:
            print(f"❌ Browser search failed: {e}")
            reddit_urls = []
        
        # Fallback to original Google search if browser failed
        if not reddit_urls:
            print("🔄 Browser search failed, trying original Google search...")
            reddit_urls = search_google_for_reddit_posts(query, num_results=max_posts*2)
        
        # If Google didn't work, try DuckDuckGo
        if not reddit_urls:
            print("🦆 Google search failed, trying DuckDuckGo...")
            reddit_urls = search_duckduckgo_for_reddit_posts(query, num_results=max_posts*2)
        
        # If both failed, try a direct Reddit search as final fallback
        if not reddit_urls:
            print("🔄 Both search engines failed, trying direct Reddit search...")
            try:
                subreddit = reddit.subreddit("all")
                reddit_submissions = list(subreddit.search(query, sort="relevance", limit=max_posts))
                reddit_urls = [f"https://reddit.com{sub.permalink}" for sub in reddit_submissions]
                print(f"📋 Direct Reddit search found {len(reddit_urls)} posts")
            except Exception as e:
                print(f"❌ Direct Reddit search also failed: {e}")
        
        if not reddit_urls:
            print("❌ All search methods failed")
            return jsonify({'error': 'No Reddit posts found via any search method for the given query.'}), 404
        
        print(f"🎯 Total URLs to process: {len(reddit_urls)}")
        
        # Get Reddit post objects from URLs
        submissions = []
        for url in reddit_urls:
            post = get_reddit_post_from_url(reddit, url)
            if post:
                submissions.append(post)
            if len(submissions) >= max_posts:  # Limit to requested number
                break
        
        if not submissions:
            return jsonify({'error': 'Could not retrieve Reddit posts from found URLs.'}), 404
        
        print(f"Successfully retrieved {len(submissions)} Reddit posts:")
        for i, submission in enumerate(submissions):
            print(f"{i+1}. {submission.title} (r/{submission.subreddit})")

        # Perform comprehensive data analysis
        analysis = analyze_reddit_data(submissions, query)
        
        # Extract text from posts and comments with enhanced data
        full_text = ""
        sources = []
        for submission in submissions:
            # Add enhanced upvote data to sources
            sources.append({
                'title': submission.title, 
                'url': submission.url,
                'upvotes': submission.score,
                'subreddit': str(submission.subreddit),
                'num_comments': submission.num_comments,
                'upvote_ratio': submission.upvote_ratio,
                'age_days': round((datetime.now(timezone.utc).timestamp() - submission.created_utc) / (24 * 3600), 1)
            })
            
            # Include comprehensive info in the text for AI analysis
            full_text += f"Title: {submission.title} (👍 {submission.score} upvotes, 💬 {submission.num_comments} comments, {submission.upvote_ratio*100:.0f}% upvoted)\n"
            if submission.selftext:
                full_text += f"Post: {submission.selftext[:1000]}\n"
            
            submission.comments.replace_more(limit=0)
            comments_text = ""
            comment_count = 0
            
            # Sort comments by score (upvotes) to get the best ones first
            sorted_comments = sorted(submission.comments.list(), key=lambda x: x.score, reverse=True)
            
            for comment in sorted_comments:
                if comment_count >= 5:  # Limit to top 5 comments per post
                    break
                # Include upvote data for comments too
                comments_text += f"Comment (👍 {comment.score}): {comment.body[:200]}\n"
                comment_count += 1
            
            full_text += f"Top Comments:\n{comments_text}\n\n"

        # Limit total text length to avoid rate limits
        if len(full_text) > 8000:  # Rough token limit
            full_text = full_text[:8000] + "...\n[Text truncated to stay within API limits]"

        # Create a comprehensive prompt with analysis data
        prompt = f"""Please analyze the following Reddit data about '{query}' and provide a comprehensive summary and evaluation.

=== DATA ANALYSIS ===
Post Metrics:
- Total posts analyzed: {analysis['post_metrics']['total_posts']}
- Average upvotes: {analysis['post_metrics']['avg_score']} (median: {analysis['post_metrics']['median_score']})
- Total engagement: {analysis['post_metrics']['total_upvotes']} upvotes, {analysis['post_metrics']['total_comments']} comments
- Average upvote ratio: {analysis['post_metrics']['avg_upvote_ratio']*100:.0f}%

Engagement Analysis:
- Comments analyzed: {analysis['engagement_analysis']['total_comments_analyzed']}
- Highly upvoted comments (10+ upvotes): {analysis['engagement_analysis']['highly_upvoted_comments']}
- Engagement rate: {analysis['engagement_analysis']['engagement_rate']}% (comments per upvote)

Content Analysis:
- Brands mentioned: {analysis['content_analysis']['unique_brands']} unique brands, {analysis['content_analysis']['total_brand_mentions']} total mentions
- Top brands: {', '.join([f"{brand} ({count}x)" for brand, count in analysis['content_analysis']['top_brands'][:5]])}
{f"- Price analysis: {analysis['content_analysis']['price_analysis']['prices_found']} prices found, avg ${analysis['content_analysis']['price_analysis']['avg_price']}, range {analysis['content_analysis']['price_analysis']['price_range']}" if analysis['content_analysis']['price_analysis'] else "- No clear pricing information found"}

Community & Freshness:
- Communities: {', '.join(analysis['community_analysis']['subreddits_involved'])}
- Content freshness: {analysis['temporal_analysis']['freshness_score']}% recent (within 30 days)
- Recency-weighted relevance: {analysis['temporal_analysis']['recency_weighted_freshness']}%
- Overall sentiment: {analysis['sentiment_indicators']['overall_sentiment']} (positive/negative ratio: {analysis['sentiment_indicators']['sentiment_ratio']})

{('⚠️ DATA FRESHNESS WARNING: Most content is outdated (low recency score). Recommendations may not reflect current market/community state. Consider data age in your analysis.' if analysis['temporal_analysis']['data_age_warning'] else '')}

=== INSTRUCTIONS ===
Based on this analysis and the raw content below, provide:

1. **SUMMARY**: Main findings and recommendations with confidence levels
2. **TOP RECOMMENDATIONS**: Specific products/brands with community consensus
3. **PRICE INSIGHTS**: Cost analysis and value recommendations  
4. **COMMUNITY CONSENSUS**: What the Reddit community agrees on
5. **RELIABILITY ASSESSMENT**: How trustworthy this data is based on engagement metrics

{('IMPORTANT: Include data age limitations in your reliability assessment. Note that older posts may not reflect current conditions.' if analysis['temporal_analysis']['data_age_warning'] else '')}

Pay special attention to:
- High-upvoted content (more reliable)
- Recent posts (more current)
- Consistent brand mentions across multiple sources
- Price points with community validation

After your analysis, please also provide structured data for link enhancement by including the following JSON block at the end:

=== LINK ENHANCEMENT DATA ===
```json
{{
  "reddit_links": [
    // List of key Reddit URLs from the analysis that contain valuable information
  ],
  "search_terms": [
    // List of specific product names, brands, or search terms that would benefit from external links
    // Focus on concrete products, specific models, brand names, or services mentioned
    // Examples: "Sony WH-1000XM4", "iPhone 15 Pro", "Toyota Camry 2024", "Best Buy"
  ]
}}
```

=== RAW CONTENT ===
{full_text}

Please provide actionable insights based on both the quantitative analysis and qualitative content, followed by the JSON data for link enhancement."""

        # Get summary from AI model with retry logic for rate limiting
        max_retries = 3
        for attempt in range(max_retries):
            try:
                message = call_ai_model(model, prompt, max_tokens=1500)
                break
            except Exception as e:
                if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                    if attempt == max_retries - 1:
                        return jsonify({'error': f'Rate limit exceeded. Please try again in a few minutes. Details: {str(e)}'}), 429
                    
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Rate limit hit, waiting {wait_time:.2f} seconds before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    return jsonify({'error': f'AI API error: {str(e)}'}), 500

        # Enhanced link discovery process
        print("🔗 Starting enhanced link discovery...")
        
        # Extract link enhancement data from AI response
        link_data = extract_link_enhancement_data(message)
        search_terms = link_data.get('search_terms', [])
        
        # Search for relevant links for each term
        enhanced_links = {}
        for term in search_terms[:5]:  # Limit to 5 terms to avoid too many API calls
            print(f"🔍 Searching for links for term: '{term}'")
            product_links = search_google_for_product_links(term, max_results=3)
            
            if product_links:
                # Use AI to curate the best links
                curated_links = curate_links_with_ai(term, product_links, model)
                enhanced_links[term] = curated_links
            else:
                enhanced_links[term] = []
        
        print(f"✅ Enhanced link discovery complete. Found links for {len([k for k, v in enhanced_links.items() if v])} terms")

        return jsonify({
            'summary': message, 
            'sources': sources,
            'analysis': analysis,  # Include the comprehensive analysis
            'search_mode': 'traditional_reddit_search',
            'enhanced_links': enhanced_links,  # Add enhanced links
            'extracted_search_terms': search_terms,  # Add extracted terms
            'link_enhancement_enabled': True
        })

    except Exception as e:
        print(f"❌ Traditional search failed: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Traditional search failed: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True)
