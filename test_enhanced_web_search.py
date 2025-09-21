#!/usr/bin/env python3
"""
Test the enhanced web search + fetch agent
"""
import asyncio
import anthropic
import os

async def test_enhanced_web_search_agent():
    """Test the enhanced web search + fetch workflow"""
    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        print('🔑 API key loaded successfully')
        
        # Enhanced prompt for web search + fetch workflow
        prompt_content = """You are a Reddit research specialist analyzing discussions about: "best budget hiking shoes"

Your search focus: recent discussions 2024 2023

COMPREHENSIVE RESEARCH WORKFLOW:
1. SEARCH PHASE: Use web_search to find relevant Reddit discussions about "best budget hiking shoes recent discussions 2024 2023 site:reddit.com"
2. FETCH PHASE: Use web_fetch to access the actual content of the most relevant Reddit posts you find
3. ANALYSIS PHASE: Analyze the full discussions, comments, and community insights

DETAILED INSTRUCTIONS:
- Search for Reddit posts that match recent discussions about budget hiking shoes
- Access the actual content of the most promising posts (up to 3-4 posts)
- Read through post content, top comments, and community discussions
- Extract specific recommendations, product mentions, prices, and consensus

After your research, provide a detailed summary including:
- Key findings from the Reddit discussions you accessed
- Specific recommendations with context from the communities
- Product mentions with details and community feedback
- Overall community sentiment and consensus level
"""
        
        message = client.messages.create(
            model='claude-3-5-haiku-latest',
            max_tokens=3000,
            messages=[{
                'role': 'user', 
                'content': prompt_content
            }],
            tools=[
                {
                    'type': 'web_search_20250305',
                    'name': 'web_search',
                    'max_uses': 3
                },
                {
                    'type': 'web_fetch_20250910',
                    'name': 'web_fetch', 
                    'max_uses': 5,
                    'citations': {'enabled': True}
                }
            ],
            extra_headers={
                'anthropic-beta': 'web-search-2025-03-05,web-fetch-2025-09-10'
            }
        )
        
        print('✅ Message created successfully')
        print(f'📊 Response type: {type(message)}')
        print(f'📏 Content length: {len(message.content) if message.content else 0}')
        
        search_performed = False
        fetch_performed = False
        citations_found = []
        
        if message.content:
            for i, block in enumerate(message.content):
                print(f'\n--- Block {i}: {block.type} ---')
                if hasattr(block, 'text'):
                    print(f'Text content: {block.text[:300]}...')
                if hasattr(block, 'name'):
                    print(f'Tool name: {block.name}')
                    if block.name == 'web_search':
                        search_performed = True
                    elif block.name == 'web_fetch':
                        fetch_performed = True
                if hasattr(block, 'input'):
                    print(f'Tool input: {block.input}')
                    if 'url' in str(block.input):
                        url = str(block.input).split("'url': '")[1].split("'")[0] if "'url': '" in str(block.input) else 'unknown'
                        if 'reddit.com' in url:
                            citations_found.append(url)
                            print(f'📄 Found Reddit URL being fetched: {url}')
        
        print(f'\n🎯 SUMMARY:')
        print(f'Search performed: {search_performed}')
        print(f'Fetch performed: {fetch_performed}')
        print(f'Reddit URLs found for fetching: {len(citations_found)}')
        for url in citations_found:
            print(f'  - {url}')
                    
    except Exception as e:
        print(f'❌ Error: {type(e).__name__}: {e}')
        import traceback
        print(f'📍 Traceback: {traceback.format_exc()}')

if __name__ == '__main__':
    asyncio.run(test_enhanced_web_search_agent())