"""
Comprehensive test for SQL validation and fixing
"""

from text2sql_engine import Text2SQLEngine

# Initialize engine
engine = Text2SQLEngine(use_llm=False)

print("=" * 80)
print("SQL VALIDATION AND AUTO-FIX TESTING")
print("=" * 80)

test_cases = [
    {
        "name": "UNION with ORDER BY before UNION (Common LLM Error)",
        "sql": """SELECT 'AWS' as provider, regionname, SUM(billedcost) as cost
FROM aws_cost_usage
GROUP BY regionname
ORDER BY cost DESC
LIMIT 5
UNION ALL
SELECT 'Azure' as provider, regionname, SUM(billedcost) as cost
FROM azure_cost_usage
GROUP BY regionname
ORDER BY cost DESC
LIMIT 5""",
        "should_fix": True
    },
    {
        "name": "UNION with parentheses (SQLite incompatible)",
        "sql": """(SELECT 'AWS' as provider, servicename, SUM(billedcost) as cost
FROM aws_cost_usage
GROUP BY servicename)
UNION ALL
(SELECT 'Azure' as provider, servicename, SUM(billedcost) as cost
FROM azure_cost_usage
GROUP BY servicename)
ORDER BY cost DESC""",
        "should_fix": True
    },
    {
        "name": "Extra semicolons and whitespace",
        "sql": """SELECT servicename, SUM(billedcost) as cost
FROM aws_cost_usage
GROUP BY servicename;;;  
  
""",
        "should_fix": True
    },
    {
        "name": "Unbalanced parentheses",
        "sql": """SELECT servicename, SUM(billedcost) as cost
FROM aws_cost_usage
GROUP BY servicename)""",
        "should_fix": True
    },
    {
        "name": "Valid query (should pass through)",
        "sql": """SELECT servicename, SUM(billedcost) as total_cost
FROM aws_cost_usage
GROUP BY servicename
ORDER BY total_cost DESC
LIMIT 10""",
        "should_fix": False
    }
]

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"TEST {i}: {test['name']}")
    print(f"{'='*80}")
    
    print("\n📝 ORIGINAL SQL:")
    print("-" * 80)
    print(test['sql'])
    
    try:
        fixed_sql = engine._validate_and_fix_sql(test['sql'])
        
        print("\n🔧 AFTER VALIDATION/FIX:")
        print("-" * 80)
        print(fixed_sql)
        
        if fixed_sql != test['sql'].strip().rstrip(';').strip():
            print("\n✓ SQL was modified (as expected)" if test['should_fix'] else "\n⚠️ SQL was modified (unexpected)")
        else:
            print("\n✓ SQL unchanged (as expected)" if not test['should_fix'] else "\n⚠️ SQL unchanged (unexpected)")
        
        # Try to execute
        print("\n✅ EXECUTION TEST:")
        print("-" * 80)
        result = engine.db.execute_query(fixed_sql)
        if result is not None:
            print(f"✓ Query executed successfully! ({len(result)} rows)")
            if len(result) > 0:
                print(f"✓ Sample result: {result.iloc[0].to_dict()}")
        else:
            print("✗ Query returned None")
            
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")

print("\n" + "=" * 80)
print("✅ ALL VALIDATION TESTS COMPLETE")
print("=" * 80)
