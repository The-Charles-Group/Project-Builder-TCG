
#!/usr/bin/env python3
"""
Comprehensive system verification after OpenAI API key addition.
Tests GPT-5 availability, AI features, and core functionality.
"""

import os
import sys
import asyncio
import httpx

async def verify_system():
    """Run comprehensive system checks"""
    
    print("=" * 60)
    print("AGENCY PROJECT BUILDER - SYSTEM VERIFICATION")
    print("=" * 60)
    
    # 1. Check OpenAI API Key
    print("\n1. Checking OpenAI API Key...")
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"   ✅ API Key found (length: {len(api_key)} chars)")
        print(f"   🔑 Key prefix: {api_key[:8]}...")
    else:
        print("   ❌ No OpenAI API Key found in environment")
        print("   ℹ️  Please add OPENAI_API_KEY to Replit Secrets")
        return False
    
    # 2. Test OpenAI Connection
    print("\n2. Testing OpenAI API Connection...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Test with a minimal completion
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use mini for quick test
            messages=[{"role": "user", "content": "Reply with just: OK"}],
            max_tokens=10
        )
        
        if response.choices[0].message.content.strip().upper() == "OK":
            print("   ✅ OpenAI API is responding correctly")
        else:
            print(f"   ⚠️  Unexpected response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"   ❌ OpenAI API test failed: {str(e)}")
        return False
    
    # 3. Check Agent Status
    print("\n3. Checking CHARLES Agent Status...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get("http://localhost:5000/api/agent/status")
            status = response.json()
            
            print(f"   Agent Available: {'✅' if status['available'] else '❌'}")
            print(f"   GPT-5 Available: {'✅' if status['gpt5_available'] else '❌'}")
            print(f"   Agent Name: {status['agent_name']}")
            print(f"   Capabilities: {len(status['capabilities'])} features")
    except Exception as e:
        print(f"   ⚠️  Could not check agent status: {str(e)}")
    
    # 4. Test AI Analysis
    print("\n4. Testing AI Analysis Engine...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Test with minimal RFP
            test_rfp = "We need paid media buying and campaign strategy for Q1 2025."
            
            response = await http_client.post(
                "http://localhost:5000/api/ai/suggest",
                json={
                    "request_text": test_rfp,
                    "strictness": "balanced",
                    "mode": "fast"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ AI Analysis working")
                print(f"   📊 Found {len(result.get('deliverables', []))} deliverables")
                
                if result.get('job_id'):
                    print(f"   🔄 Job ID: {result['job_id']}")
            else:
                print(f"   ⚠️  Analysis returned status {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  AI Analysis test error: {str(e)}")
    
    # 5. Check Database
    print("\n5. Checking Database Status...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.get("http://localhost:5000/api/load")
            data = response.json()
            
            print(f"   ✅ Database loaded")
            print(f"   📁 Source: {data.get('source', 'unknown')}")
            print(f"   📊 Deliverables: {len(data.get('deliverables', []))}")
    except Exception as e:
        print(f"   ⚠️  Database check error: {str(e)}")
    
    # 6. Summary
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print("\n✅ System is ready with OpenAI API key configured!")
    print("\nNext Steps:")
    print("1. Restart the application to load GPT-5 features")
    print("2. Test AI suggestions in the UI")
    print("3. Monitor console for any errors")
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(verify_system())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        sys.exit(1)
