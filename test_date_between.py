from text2sql_engine import Text2SQLEngine

engine = Text2SQLEngine(use_llm=False)

sql = """SELECT 'AWS' as provider, regionname, SUM(billedcost) as cost 
FROM aws_cost_usage 
WHERE billingperiodstart BETWEEN date('now', '-7 days') AND date('now')
GROUP BY regionname
UNION ALL
SELECT 'Azure' as provider, regionname, SUM(billedcost) as cost
FROM azure_cost_usage 
WHERE billingperiodstart BETWEEN date('now', '-7 days') AND date('now')
GROUP BY regionname
ORDER BY cost DESC
LIMIT 5"""

print("ORIGINAL SQL:")
print(sql)
print("\n" + "="*80 + "\n")

fixed, warn = engine._detect_and_fix_date_issues(sql)

print("FIXED SQL:")
print(fixed)
print("\n" + "="*80 + "\n")

if warn:
    print("WARNING:", warn)
    print("\n" + "="*80 + "\n")

# Test execution
print("EXECUTING...")
result = engine.db.execute_query(fixed)
if result is not None:
    print(f"SUCCESS: {len(result)} rows returned")
    if len(result) > 0:
        print(result)
else:
    print("FAILED: No results")
