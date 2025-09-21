#!/usr/bin/env python3
"""
Simple test script to verify Claude web search API is working
"""
import asyncio
import anthropic
import os
import json

async def test_simple_web_search():
    """Test a simple web search to debug the issue"""
    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        print('🔑 API key loaded successfully')
        
        # Simple test query
        message = client.messages.create(
            model='claude-3-5-haiku-latest',
            max_tokens=1000,
            messages=[{
                'role': 'user', 
                'content': 'Search for "Magnus Carlsen chess reddit" and find any Reddit URLs. List any reddit.com links you find.'
            }],
            tools=[{
                'type': 'web_search_20250305',
                'name': 'web_search',
                'max_uses': 2
            }],
            extra_headers={
                'anthropic-beta': 'web-search-2025-03-05'
            }
        )
        
        print('✅ Message created successfully')
        print(f'📊 Response type: {type(message)}')
        print(f'📏 Content length: {len(message.content) if message.content else 0}')
        
        if message.content:
            for i, block in enumerate(message.content):
                print(f'\n--- Block {i}: {block.type} ---')
                if hasattr(block, 'text'):
                    print(f'Text content: {block.text}')
                if hasattr(block, 'name'):
                    print(f'Tool name: {block.name}')
                if hasattr(block, 'input'):
                    print(f'Tool input: {block.input}')
                    
        # Look for Reddit URLs in the response
        full_text = ""
        if message.content:
            for block in message.content:
                if hasattr(block, 'text'):
                    full_text += block.text
        
        import re
        reddit_urls = re.findall(r'https?://(?:www\.)?reddit\.com/r/[\w\-]+/comments/[\w\-]+/?[\w\-]*/?', full_text)
        print(f'\n🔗 Found {len(reddit_urls)} Reddit URLs:')
        for url in reddit_urls:
            print(f'  - {url}')
                    
    except Exception as e:
        print(f'❌ Error: {type(e).__name__}: {e}')
        import traceback
        print(f'📍 Traceback: {traceback.format_exc()}')

if __name__ == '__main__':
    asyncio.run(test_simple_web_search())