# CORE PRINCIPLES - NO PATCH FIXES EVER

## ABSOLUTE RULES - NEVER VIOLATE THESE

### 1. NO TIMEOUT PATCHES
❌ **NEVER** add timeouts as a "fix" for hanging operations
❌ **NEVER** use asyncio.wait_for() to mask blocking issues  
❌ **NEVER** add arbitrary time limits to avoid fixing root causes
✅ **ALWAYS** fix the actual async/blocking issue
✅ **ALWAYS** implement proper async patterns
✅ **ALWAYS** address the root cause of hangs

### 2. NO DATA TRUNCATION PATCHES
❌ **NEVER** reduce data size to make something "work"
❌ **NEVER** limit input arbitrarily (e.g., text[:8000])
❌ **NEVER** skip processing items to avoid issues
✅ **ALWAYS** handle full data volumes as requested
✅ **ALWAYS** implement proper streaming/chunking if needed
✅ **ALWAYS** fix memory/performance issues at the source

### 3. NO SILENCING ERRORS
❌ **NEVER** catch and ignore exceptions to make things "run smoothly"
❌ **NEVER** return fallback data when operations fail
❌ **NEVER** use try/except to hide problems
✅ **ALWAYS** fix the error at its source
✅ **ALWAYS** handle errors properly with user feedback
✅ **ALWAYS** investigate and resolve root causes

### 4. NO ARBITRARY LIMITS
❌ **NEVER** add max iterations/items to avoid issues
❌ **NEVER** limit functionality to make it "stable"
❌ **NEVER** reduce features to avoid complexity
✅ **ALWAYS** implement full functionality as designed
✅ **ALWAYS** handle edge cases properly
✅ **ALWAYS** scale solutions to requirements

### 5. NO FAKE PROGRESS
❌ **NEVER** show progress bars that don't reflect real work
❌ **NEVER** return success when operations partially fail
❌ **NEVER** give illusion of functionality without substance
✅ **ALWAYS** show accurate, real-time status
✅ **ALWAYS** complete operations fully
✅ **ALWAYS** be transparent about actual state

## ENFORCEMENT

### Code Review Checklist
Before ANY commit, check for these RED FLAGS:
- [ ] Any use of `asyncio.wait_for()` with timeout?
- [ ] Any arbitrary string slicing like `text[:8000]`?
- [ ] Any broad try/except blocks?
- [ ] Any artificial limits on iterations/processing?
- [ ] Any "fallback" returns when operations fail?
- [ ] Any comments mentioning "workaround" or "patch"?

### Violation Consequences
1. **IMMEDIATE REJECTION** - Code with patches must be reverted
2. **ROOT CAUSE ANALYSIS** - Identify why the real fix wasn't implemented
3. **PROPER IMPLEMENTATION** - Fix the actual issue, no matter how complex
4. **DOCUMENTATION** - Record the real fix for future reference

## THE GOLDEN RULE

**"If a fix makes the app appear to work while actually reducing functionality, it's not a fix - it's a lie."**

## Examples of Violations vs Proper Fixes

### VIOLATION: Timeout on API call
```python
# ❌ WRONG - Hiding the problem
response = await asyncio.wait_for(api_call(), timeout=30)
```

### PROPER FIX: Fix async handling
```python
# ✅ RIGHT - Using proper async client
async_client = AsyncOpenAI()
response = await async_client.responses.create(...)
```

### VIOLATION: Truncating input
```python
# ❌ WRONG - Reducing data to avoid issue
analyze_text(text[:8000])  # "Limit for stability"
```

### PROPER FIX: Handle full data
```python
# ✅ RIGHT - Process all data properly
async def analyze_text_chunked(text):
    chunks = split_intelligently(text)
    results = await asyncio.gather(*[process(c) for c in chunks])
    return merge_results(results)
```

### VIOLATION: Ignoring errors
```python
# ❌ WRONG - Hiding failures
try:
    result = process_data()
except:
    return "Processing..."  # Fake success
```

### PROPER FIX: Handle errors properly
```python
# ✅ RIGHT - Fix the issue causing errors
result = await properly_configured_process()
if not result:
    raise ProcessingError("Clear explanation")
```

## REMEMBER

**Every patch is a lie to the user and the PM. Fix the real problem or explain why it can't be fixed - never pretend it works when it doesn't.**

**This document is LAW. Violating these principles is unacceptable.**