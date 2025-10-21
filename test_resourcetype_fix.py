"""
Test script to verify resource type mapping fixes
"""

import sys
from text2sql_engine import Text2SQLEngine

def test_resourcetype_mappings():
    """Test that resource type translations work correctly"""
    
    print("="*80)
    print("Testing Resource Type Mapping Fixes")
    print("="*80)
    
    engine = Text2SQLEngine(use_llm=True)
    
    # Test cases with expected transformations
    test_cases = [
        {
            "query": "Show me top 10 EC2 and VM costs",
            "description": "EC2 should map to 'instance', VM to 'Virtual machine'"
        },
        {
            "query": "What are the costs for EC2 instances?",
            "description": "EC2 should map to 'instance' for AWS"
        },
        {
            "query": "Show Azure VM costs by service",
            "description": "VM should map to 'Virtual machine' for Azure"
        },
        {
            "query": "Compare S3 and blob storage costs",
            "description": "S3 should map to 'bucket', blob storage to 'Storage account'"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}: {test['description']}")
        print(f"Query: {test['query']}")
        print("-"*80)
        
        try:
            result = engine.execute_natural_query(test['query'])
            
            print(f"\nGenerated SQL:")
            print(result['sql_query'])
            print(f"\nConversion Method: {result['method']}")
            print(f"Rows Returned: {result['row_count']}")
            
            if result['warning']:
                print(f"\n⚠️  Warning: {result['warning']}")
            
            if result['row_count'] > 0:
                print(f"\n✅ SUCCESS - Query returned {result['row_count']} results")
                print("\nSample results:")
                print(result['results'].head(5))
            else:
                print("\n❌ ISSUE - Query returned 0 results")
                print("   This might indicate the resource type mapping didn't work")
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
    
    # Test the specific failing query from the user
    print(f"\n{'='*80}")
    print("Testing Original Failing Query")
    print("="*80)
    
    failing_query = "Show me top 10 most expensive EC2 and VM services"
    print(f"Query: {failing_query}")
    print("-"*80)
    
    try:
        result = engine.execute_natural_query(failing_query)
        
        print(f"\nGenerated SQL:")
        print(result['sql_query'])
        print(f"\nConversion Method: {result['method']}")
        print(f"Rows Returned: {result['row_count']}")
        
        if result['row_count'] > 0:
            print(f"\n✅ SUCCESS - Fixed! Query now returns {result['row_count']} results")
            print("\nResults:")
            print(result['results'])
        else:
            print("\n❌ Still returning 0 results - investigating...")
            
            # Try without resource type filter
            print("\n" + "-"*80)
            print("Testing without resourcetype filter to see if data exists...")
            alt_query = "Show me top 10 most expensive services from AWS and Azure"
            result2 = engine.execute_natural_query(alt_query)
            print(f"\nAlternative query rows: {result2['row_count']}")
            if result2['row_count'] > 0:
                print("Data exists! The issue was the resourcetype filter.")
                print(result2['results'])
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    engine.close()
    
    print("\n" + "="*80)
    print("Testing Complete")
    print("="*80)

if __name__ == "__main__":
    test_resourcetype_mappings()
