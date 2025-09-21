import functions_framework
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import praw
import anthropic
import os
import json

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/estimate-cost', methods=['POST'])
@app.route('/estimate-cost', methods=['POST'])
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
    """Simplified search and summarize endpoint for Firebase Functions"""
    try:
        data = request.get_json()
        query = data.get('query')
        max_posts = data.get('max_posts', 3)
        model = data.get('model', 'claude-3-5-sonnet-20241022')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # For now, return a placeholder response
        # TODO: Implement full Reddit search functionality
        return jsonify({
            'summary': f'Firebase Functions deployment successful! Searched for: "{query}"\n\nThis is a simplified response while we migrate the full Reddit search functionality to Firebase Functions. The backend is now running on Firebase!',
            'sources': [
                {
                    'title': 'Firebase Functions Test',
                    'url': 'https://firebase.google.com',
                    'upvotes': 1,
                    'subreddit': 'firebase',
                    'num_comments': 0
                }
            ],
            'search_mode': 'firebase_functions_test',
            'analysis': {
                'message': 'Firebase Functions backend is working! Full Reddit integration coming soon.',
                'query': query,
                'model': model,
                'max_posts': max_posts
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Search failed: {str(e)}',
            'details': 'Firebase Functions error'
        }), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Firebase Functions backend is running',
        'timestamp': str(os.environ.get('FUNCTION_REGION', 'local')),
        'version': '1.0.0',
        'env_present': {
            'ANTHROPIC_API_KEY': bool(os.environ.get('ANTHROPIC_API_KEY')),
            'REDDIT_CLIENT_ID': bool(os.environ.get('REDDIT_CLIENT_ID')),
            'REDDIT_CLIENT_SECRET': bool(os.environ.get('REDDIT_CLIENT_SECRET')),
            'REDDIT_USER_AGENT': bool(os.environ.get('REDDIT_USER_AGENT')),
        }
    })

# Firebase Functions entry point
@functions_framework.http
def api(request):
    """Firebase Functions HTTP entry point"""
    with app.app_context():
        return app.full_dispatch_request()

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))