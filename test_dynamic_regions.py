from agentic_clarification import AgenticClarifier

# Test dynamic region extraction
clarifier = AgenticClarifier()

print("Testing: 'What are the regional AWS costs?'")
result = clarifier.analyze_query('What are the regional AWS costs?')

print(f"\nQuestion: {result['question']}")
print("\nDynamic Region Options:")
for option in result['options']:
    print(f"  - {option['label']} ({option['value']})")

print("\n" + "="*70)
print("Testing: 'Show me Azure costs by region'")
result2 = clarifier.analyze_query('Show me Azure costs by region')

print(f"\nQuestion: {result2['question']}")
print("\nDynamic Region Options:")
for option in result2['options']:
    print(f"  - {option['label']} ({option['value']})")
