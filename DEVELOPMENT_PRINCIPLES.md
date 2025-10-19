# TCG Workspace Development Principles

**Last Updated:** October 19, 2025

## Core Principle: Never Destroy Functionality

This document establishes **non-negotiable development principles** for all work in the TCG workspace and specifically for the Agency Project Builder application.

---

## The Golden Rule

### NEVER remove functionality to fix bugs or simplify code.

When encountering bugs, freezes, performance issues, or complex code:

✅ **DO THIS:**
- Debug thoroughly to identify the root cause
- Fix the actual problem while preserving all functionality
- Add more code, logic, or features if needed to solve it properly
- Build additional error handling, retry logic, or safeguards
- Refactor for clarity while maintaining behavior
- Add comprehensive logging and monitoring

❌ **NEVER DO THIS:**
- Remove features to "simplify" the codebase
- Comment out complex logic to make bugs go away
- Delete error-handling code because it's "too complex"
- Strip out user selections, state management, or data flows
- Take shortcuts that break existing functionality
- Choose "simpler code" over "working code"

---

## Why This Matters

**User Trust:** Every feature was built because users need it. Removing functionality to fix a bug destroys user trust and workflow.

**Technical Debt:** Shortcuts create more problems than they solve. Proper debugging prevents recurring issues.

**System Integrity:** Complex systems have complex logic for good reasons. Simplifying without understanding causes cascading failures.

---

## When Debugging Issues

### Step 1: Understand Before Changing
- Read and comprehend ALL related code
- Trace the full data flow
- Identify what each piece of logic does
- Document dependencies and side effects

### Step 2: Identify Root Cause
- Add comprehensive logging
- Use debugging tools and techniques
- Test hypotheses systematically
- Don't assume - verify with evidence

### Step 3: Fix Properly
- Preserve ALL existing functionality
- Add code/logic as needed to solve the problem
- Implement proper error handling
- Add safeguards to prevent recurrence

### Step 4: Verify Completely
- Test the fix thoroughly
- Verify ALL features still work
- Check edge cases and error scenarios
- Confirm no regression in functionality

---

## Specific Examples for This Project

### ❌ BAD: Taking Shortcuts
```javascript
// WRONG: Removing component/L3 selection logic because buildFromCurrentSelection freezes
async function buildFromCurrentSelection() {
  const codes = readSelectedCodesFromUI();
  await callAPI(codes); // Lost all component and L3 selections!
  showStep3();
}
```

### ✅ GOOD: Debugging and Fixing Properly
```javascript
// RIGHT: Keep all logic, find and fix the actual freeze cause
async function buildFromCurrentSelection() {
  console.log('[DEBUG] Starting...');
  const codes = readSelectedCodesFromUI();
  console.log('[DEBUG] Codes:', codes);
  
  // Build component payload (KEEP THIS - users need it!)
  const componentPayload = buildComponentPayload(codes);
  console.log('[DEBUG] Components:', componentPayload);
  
  // Build L3 payload (KEEP THIS - users need it!)
  const l3Payload = buildL3Payload(codes);
  console.log('[DEBUG] L3:', l3Payload);
  
  // FIND WHY IT FREEZES HERE - maybe infinite loop in buildL3Payload?
  // FIX THE ROOT CAUSE - don't remove the feature!
  
  await callAPI(codes, componentPayload, l3Payload);
  showStep3();
}
```

---

## Code Review Checklist

Before marking any task complete, verify:

- [ ] ALL original functionality is preserved
- [ ] No features were removed or commented out
- [ ] User selections and state are fully maintained
- [ ] Error handling is comprehensive, not removed
- [ ] The fix addresses the root cause, not symptoms
- [ ] Added code improves robustness
- [ ] Testing confirms everything works

---

## Enforcement

This principle applies to:
- **All bug fixes** - Debug properly, never remove features
- **All refactoring** - Preserve behavior completely
- **All performance optimization** - Keep functionality intact
- **All code simplification** - Only if behavior unchanged
- **All feature additions** - Build on top, don't replace

**If you're ever tempted to delete logic to fix an issue:**
1. Stop immediately
2. Read this document again
3. Debug the root cause instead
4. Ask for help if needed
5. Build the proper fix

---

## Remember

> **"Working code with all features" beats "simple code with missing features" every single time.**

The user chose this system because it has the functionality they need. Our job is to make that functionality work reliably, not to delete it because debugging is hard.

---

**Signed:** Replit Agent  
**Binding:** This principle is permanently hard-wired into all development work for TCG workspace projects.
