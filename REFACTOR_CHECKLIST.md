# Refactor Checklist for Calculation Logic

This checklist must be followed when moving or restructuring calculation logic to prevent variable ordering bugs like the `comp_duration` issue.

## Pre-Refactor Analysis

### 1. Document Variable Dependencies
Before moving any calculation, list all variables and their dependencies:

```
Example:
- tg_target_month DEPENDS ON: comp_hours_month_display, tg_hours_month
- capacity_durations DEPENDS ON: tg_target_month, tg_in_comp
- comp_duration DEPENDS ON: capacity_durations, offset_by_tg, comp_offset
- component_row USES: comp_duration, comp_price, comp_hours_total_display
```

### 2. Map All Consumers
For each variable being moved, identify EVERY place it's used:
- Search for the variable name in the entire function
- Note line numbers and context
- Verify definition comes before ALL uses

### 3. Check Scope and Loops
- Is the variable inside a loop?
- Does it need to be recalculated per iteration?
- Are there multiple scopes (component loop vs task loop)?

## During Refactor

### 4. Move Calculations as Atomic Blocks
- Keep related calculations together
- Don't split dependency chains
- Maintain comments that explain the logic

### 5. Update Comments
- Add comments explaining WHY the calculation is at this specific location
- Note any ordering requirements
- Mark changes with clear labels (e.g., "CHANGE 4: Moved to ensure comp_duration available")

### 6. Verify Definition Order
After moving, manually trace execution:
1. Read through the code top-to-bottom
2. Verify each variable is defined before use
3. Check both normal flow and edge cases (empty lists, None values)

## Post-Refactor Validation

### 7. Static Analysis
Run linting tools to catch undefined variables:
```bash
# Check for undefined variables
ruff check --select F821 main.py

# Or use Python's built-in compiler
python -m py_compile main.py
```

### 8. Runtime Testing
Test the affected code path:
- Restart the server and check startup logs
- Execute the modified function with test data
- Check for UnboundLocalError or NameError exceptions

### 9. Integration Testing
Run end-to-end tests for the feature:
- For exports: Test actual XML/Excel export
- For calculations: Verify output matches expected values
- Test edge cases (empty data, multi-month, single component)

### 10. Code Review
Before marking complete:
- Have architect review the changes with full git diff
- Verify no regressions in related functionality
- Confirm all dependencies are correctly ordered

## Quick Reference: Common Mistakes

❌ **BAD**: Moving only part of a calculation chain
```python
# comp_duration calculated here
comp_duration = max(...)

# ... 50 lines later ...

# component row uses comp_duration (BEFORE it's defined)
rows.append({"Duration_Days": comp_duration})
```

✅ **GOOD**: Move entire dependency chain together
```python
# Calculate tg_target_month first
tg_target_month = _largest_remainder(...)

# Then capacity_durations (depends on tg_target_month)
capacity_durations = {tg: calc(...) for tg in tg_in_comp}

# Then comp_duration (depends on capacity_durations)
comp_duration = max(...)

# Now use comp_duration
rows.append({"Duration_Days": comp_duration})
```

## Automated Checks (Future)

- [ ] Set up pre-commit hooks with ruff/flake8
- [ ] Add unit tests for core calculation functions
- [ ] Create smoke test that runs export on sample data
- [ ] Add CI pipeline that runs linting and tests

## Emergency Fix Process

If you introduce a variable ordering bug:
1. **Stop**: Don't make more changes
2. **Identify**: Find the undefined variable from error message
3. **Trace**: Map out all dependencies of that variable
4. **Move**: Relocate entire dependency chain before first use
5. **Test**: Restart server and verify fix
6. **Review**: Have architect verify the ordering is correct
