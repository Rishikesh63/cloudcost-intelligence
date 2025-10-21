from text2sql_engine import Text2SQLEngine

engine = Text2SQLEngine(use_llm=False)

# Test 1: Query without date filter should not show warning
print("="*80)
print("TEST 1: Query WITHOUT date filter")
print("="*80)
sql1 = "SELECT SUM(billedcost) as total FROM aws_cost_usage"
fixed1, warn1 = engine._detect_and_fix_date_issues(sql1)
print(f"Original: {sql1}")
print(f"Fixed: {fixed1}")
print(f"Warning: {warn1}")
print(f"✓ PASS" if warn1 is None else "✗ FAIL - should not show warning")

# Test 2: Query with date filter should show warning
print("\n" + "="*80)
print("TEST 2: Query WITH date filter (BETWEEN)")
print("="*80)
sql2 = "SELECT * FROM aws_cost_usage WHERE billingperiodstart BETWEEN date('now', '-7 days') AND date('now')"
fixed2, warn2 = engine._detect_and_fix_date_issues(sql2)
print(f"Original: {sql2}")
print(f"Fixed: {fixed2}")
print(f"Warning: {warn2}")
print(f"✓ PASS" if warn2 is not None else "✗ FAIL - should show warning")

# Test 3: GROUP BY without column in SELECT
print("\n" + "="*80)
print("TEST 3: GROUP BY column not in SELECT")
print("="*80)
sql3 = "SELECT SUM(billedcost) as total FROM aws_cost_usage GROUP BY servicename"
fixed3 = engine._validate_and_fix_sql(sql3)
print(f"Original: {sql3}")
print(f"Fixed: {fixed3}")
print(f"✓ PASS" if 'servicename' in fixed3 else "✗ FAIL - servicename should be added to SELECT")

# Test execution
print("\n" + "="*80)
print("EXECUTION TEST")
print("="*80)
try:
    result = engine.db.execute_query(fixed3)
    if result is not None:
        print(f"✓ Query executed: {len(result)} rows")
        if len(result) > 0:
            print(result.head())
    else:
        print("✗ Query failed")
except Exception as e:
    print(f"✗ Error: {e}")
