"""
Test UNION query syntax fix
"""

from text2sql_engine import Text2SQLEngine

# Initialize engine
engine = Text2SQLEngine(use_llm=False)

# Test query with ORDER BY and LIMIT in individual SELECT statements
problematic_sql = """SELECT 'AWS' as provider, regionname, SUM(billedcost) as total_cost 
  FROM aws_cost_usage
  WHERE regionname LIKE '%East%'
  GROUP BY regionname
  ORDER BY total_cost DESC
  LIMIT 5
UNION ALL
SELECT 'Azure' as provider, regionname, SUM(billedcost) as total_cost
  FROM azure_cost_usage
  WHERE regionname LIKE '%East%'
  GROUP BY regionname
  ORDER BY total_cost DESC
  LIMIT 5
"""

print("=" * 80)
print("TESTING UNION QUERY SYNTAX FIX")
print("=" * 80)

print("\n📝 ORIGINAL PROBLEMATIC SQL:")
print("-" * 80)
print(problematic_sql)

print("\n🔧 AFTER FIX:")
print("-" * 80)
fixed_sql = engine._fix_union_syntax(problematic_sql)
print(fixed_sql)

print("\n✅ EXECUTING FIXED QUERY:")
print("-" * 80)
try:
    result = engine.db.execute_query(fixed_sql)
    if result is not None:
        print(f"✓ Query executed successfully!")
        print(f"✓ Returned {len(result)} rows")
        print("\nResults:")
        print(result.to_string())
    else:
        print("✗ Query returned None")
except Exception as e:
    print(f"✗ Error: {str(e)}")

print("\n" + "=" * 80)
