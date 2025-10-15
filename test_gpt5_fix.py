#!/usr/bin/env python3
"""Test GPT-5 response and fix extraction logic"""

import os
import json
from openai import OpenAI

# Initialize client  
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("ERROR: No OPENAI_API_KEY found")
    exit(1)

client = OpenAI(api_key=api_key)

print("Testing GPT-5 Responses API...")
print("=" * 60)

# Make a simple test call
response = client.responses.create(
    model="gpt-5-mini",
    input=[{"role": "user", "content": "Reply with just: WORKING"}],
    reasoning={"effort": "low"},
    max_output_tokens=100
)

# Debug the response structure
print(f"Response type: {type(response)}")

# Get response as dict
resp_dict = response.model_dump() if hasattr(response, 'model_dump') else response

print(f"\nResponse keys: {list(resp_dict.keys())}")

# Check output field
if 'output' in resp_dict:
    output = resp_dict['output']
    print(f"\nOutput has {len(output)} items:")
    for i, item in enumerate(output):
        if isinstance(item, dict):
            print(f"\nItem {i}:")
            print(f"  Type: {item.get('type')}")
            print(f"  ID: {item.get('id', '')[:20]}...")
            
            # Check content
            if 'content' in item:
                content = item['content']
                if content is None:
                    print(f"  Content: None")
                elif isinstance(content, list):
                    print(f"  Content: List with {len(content)} items")
                    # Extract text from content list
                    for j, content_item in enumerate(content[:3]):  # First 3 items
                        if isinstance(content_item, dict):
                            print(f"    Content[{j}] keys: {list(content_item.keys())}")
                            # Look for text field
                            if 'text' in content_item:
                                text = content_item['text']
                                print(f"    Content[{j}].text: '{text}'")
                                print(f"\n✅ FOUND THE TEXT: '{text}'")
                            # Look for value field
                            if 'value' in content_item:
                                value = content_item['value']
                                print(f"    Content[{j}].value: '{value}'")
                elif isinstance(content, str):
                    print(f"  Content: '{content}'")