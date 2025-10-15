#!/usr/bin/env python3
"""Test script to debug GPT-5 response format issue"""

import os
import json
from openai import OpenAI

# Initialize client
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("ERROR: No OPENAI_API_KEY found")
    exit(1)

client = OpenAI(api_key=api_key)

print("Testing GPT-5 Responses API directly...")
print("=" * 60)

try:
    # Make a simple test call
    response = client.responses.create(
        model="gpt-5-mini",
        input=[{"role": "user", "content": "Reply with just the word: WORKING"}],
        reasoning={"effort": "low"},
        max_output_tokens=50
    )
    
    print(f"Response type: {type(response)}")
    print(f"Response attributes: {[x for x in dir(response) if not x.startswith('_')][:30]}")
    
    # Try to get the response as a dict
    if hasattr(response, 'model_dump'):
        resp_dict = response.model_dump()
        print(f"\nResponse dict keys: {list(resp_dict.keys())}")
        
        # Check each key
        print("\n--- Checking key values ---")
        
        # Check 'text' field
        if 'text' in resp_dict:
            print(f"'text' field type: {type(resp_dict['text'])}")
            print(f"'text' field value: {resp_dict['text']}")
        
        # Check 'output' field
        if 'output' in resp_dict:
            output = resp_dict['output']
            print(f"\n'output' field type: {type(output)}")
            if isinstance(output, list):
                print(f"'output' has {len(output)} items")
                for i, item in enumerate(output):
                    if isinstance(item, dict):
                        print(f"\nOutput item {i}:")
                        print(f"  Keys: {list(item.keys())}")
                        print(f"  Type: {item.get('type')}")
                        print(f"  Content: {item.get('content')}")
                        print(f"  Status: {item.get('status')}")
                        
        # Check for incomplete details
        if 'incomplete_details' in resp_dict:
            print(f"\n'incomplete_details': {resp_dict['incomplete_details']}")
        
        # Print full response for debugging
        print("\n--- Full response (truncated) ---")
        full_str = json.dumps(resp_dict, default=str, indent=2)
        print(full_str[:2000])
        
    # Try direct attribute access
    print("\n--- Direct attribute access ---")
    
    # Check for text attribute
    if hasattr(response, 'text'):
        text_attr = getattr(response, 'text')
        print(f"response.text type: {type(text_attr)}")
        print(f"response.text value: {text_attr}")
        
    # Check for output attribute  
    if hasattr(response, 'output'):
        output_attr = getattr(response, 'output')
        print(f"response.output type: {type(output_attr)}")
        if output_attr:
            print(f"response.output value: {output_attr}")

    # Check for content attribute
    if hasattr(response, 'content'):
        content_attr = getattr(response, 'content')
        print(f"response.content type: {type(content_attr)}")
        print(f"response.content value: {content_attr}")
        
except Exception as e:
    print(f"Error calling GPT-5: {e}")
    import traceback
    traceback.print_exc()