#!/bin/bash

# Simple test script for timeline generation

echo "===== Testing Timeline Generation with Large Deliverable Set ====="
echo ""

# Generate test deliverables JSON
cat > test_deliverables.json << 'EOF'
{
  "deliverables": [
EOF

# Add 25 test deliverables
for i in {1..25}; do
  if [ $i -ne 1 ]; then
    echo "," >> test_deliverables.json
  fi
  cat >> test_deliverables.json << EOF
    {
      "deliverable_code": "DEL-$(printf '%04d' $i)",
      "deliverable": "Test Deliverable $i",
      "department": "Strategy",
      "hours": $((20 + i * 2)),
      "price": $((3000 + i * 100)),
      "components": []
    }
EOF
done

# Close the JSON
cat >> test_deliverables.json << 'EOF'
  ],
  "rfp_text": "Test RFP for large deliverable set testing",
  "project_start": "2025-01-01",
  "optimization_mode": "balanced",
  "use_intelligent_scheduler": false
}
EOF

echo "📝 Created test payload with 25 deliverables"
echo ""

# Start timeline generation
echo "🚀 Starting timeline generation..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/ai/generate_timeline \
  -H "Content-Type: application/json" \
  -d @test_deliverables.json)

# Extract job_id
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))" 2>/dev/null)

if [ -z "$JOB_ID" ]; then
  echo "❌ Failed to start timeline generation"
  echo "Response: $RESPONSE"
  exit 1
fi

echo "✅ Job created: $JOB_ID"
echo ""

# Monitor SSE stream
echo "📡 Monitoring SSE stream for progress..."
echo ""

# Use curl to monitor SSE stream for 60 seconds
timeout 60 curl -N -s http://localhost:5000/api/stream/$JOB_ID | while IFS= read -r line; do
  if [[ $line == data:* ]]; then
    # Extract JSON from SSE data
    json=${line:5}
    
    # Try to parse and display key fields
    if command -v python3 >/dev/null; then
      echo "$json" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'progress' in data:
        print(f\"📊 Progress: {data['progress']:.1f}% - {data.get('message', '')} [{data.get('current_stage', '')}]\")
        if data.get('processed_items'):
            print(f\"   Items: {data['processed_items']}/{data.get('total_items', '?')}\")
    elif data.get('type') == 'heartbeat':
        # Don't print heartbeats to reduce noise
        pass
    elif data.get('status') == 'completed':
        print(f\"✅ Timeline generation completed!\")
        if 'result' in data and 'tasks' in data['result']:
            print(f\"   Generated {len(data['result']['tasks'])} tasks\")
    elif data.get('status') == 'failed':
        print(f\"❌ Generation failed: {data.get('error', 'Unknown error')}\")
except:
    pass
" 2>/dev/null
    fi
    
    # Check for completion
    if [[ $json == *'"status":"completed"'* ]]; then
      echo ""
      echo "🎉 Test completed successfully!"
      rm -f test_deliverables.json
      exit 0
    elif [[ $json == *'"status":"failed"'* ]]; then
      echo ""
      echo "❌ Test failed!"
      rm -f test_deliverables.json
      exit 1
    fi
  fi
done

echo ""
echo "⏰ Test timed out after 60 seconds (this might be normal for very large sets)"
rm -f test_deliverables.json