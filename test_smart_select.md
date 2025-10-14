# Test Document for Smart Select Feature

## Instructions to Test Smart Select

### 1. Load the Application
- Navigate to http://localhost:5000

### 2. Provide Test RFP Content
Copy and paste this sample RFP into Step 1:

```
We need a comprehensive digital marketing campaign for our new product launch. 
This includes:
- Brand strategy development
- Creative concept and design
- Social media campaign
- Paid media planning and buying
- Website development
- Analytics and reporting
- Content creation
- Email marketing
- SEO optimization
```

### 3. Run AI Analysis
- Click "Analyze with AI" button
- Wait for the analysis to complete

### 4. Test Smart Select Feature
Once AI suggestions appear in Step 2, you'll see the new Smart Select section:

#### Test Scenarios:

**Test 1: High Threshold (80%)**
- Set threshold to 80%
- Click "Apply Smart Selection"
- Expected: Only deliverables with ≥80% confidence are selected

**Test 2: Medium Threshold (60%)**
- Set threshold to 60%
- Click "Apply Smart Selection" 
- Expected: Deliverables with ≥60% confidence are selected

**Test 3: Low Threshold (30%)**
- Set threshold to 30%
- Click "Apply Smart Selection"
- Expected: Most deliverables are selected

**Test 4: Zero Threshold (0%)**
- Set threshold to 0%
- Click "Apply Smart Selection"
- Expected: All deliverables are selected

**Test 5: 100% Threshold**
- Set threshold to 100%
- Click "Apply Smart Selection"
- Expected: Only deliverables with 100% confidence are selected (likely none or very few)

### 5. Verify Functionality

Check that:
✅ The Smart Select UI appears below the Select All/Deselect All buttons
✅ The threshold input accepts values 0-100
✅ The Apply Smart Selection button triggers the selection
✅ Visual feedback shows how many items were selected
✅ Deliverables with confidence below threshold are unselected
✅ Components and tasks are selected based on the parent deliverable's confidence
✅ Manual selection still works after using Smart Select

## Implementation Details

### UI Location
The Smart Select controls are added in the AI Suggestions panel:
- Background: Light purple gradient
- Contains: Label, number input (0-100), and button
- Shows feedback message after applying selection

### Selection Logic
```javascript
// For each deliverable:
if (confidence >= threshold) {
  - Select deliverable
  - Select all components (inherit deliverable confidence)
  - Select AI-selected tasks (100% confidence)
  - Unselect non-AI-selected tasks (0% confidence)
}
```

### Confidence Mapping
- **Deliverables**: Use `calibrated_confidence` field (shown as percentage)
- **Components**: Inherit parent deliverable's confidence
- **Tasks**: AI-selected = 100%, others = 0%