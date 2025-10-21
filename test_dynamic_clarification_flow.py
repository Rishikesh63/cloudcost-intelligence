"""
Comprehensive test demonstrating dynamic clarification in action
"""

from agentic_clarification import AgenticClarifier

def test_clarification_flow():
    """Test the complete clarification workflow"""
    
    clarifier = AgenticClarifier()
    
    print("=" * 80)
    print("DYNAMIC CLARIFICATION - COMPREHENSIVE TEST")
    print("=" * 80)
    
    test_cases = [
        {
            "query": "Show me costs",
            "description": "Generic cost query - needs provider AND time range",
            "expected_first": "provider"
        },
        {
            "query": "What are the regional AWS costs?",
            "description": "Regional query for AWS - needs dynamic regions",
            "expected_first": "region"
        },
        {
            "query": "Show me Azure costs by region",
            "description": "Regional query for Azure - needs dynamic regions",
            "expected_first": "region"
        },
        {
            "query": "Show me top services",
            "description": "Top N query - needs provider, then limit",
            "expected_first": "provider"
        },
        {
            "query": "Show me top AWS services by cost for last month",
            "description": "Complete query - no clarification needed",
            "expected_first": None
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {test['description']}")
        print(f"{'='*80}")
        print(f"Query: '{test['query']}'")
        
        result = clarifier.analyze_query(test['query'])
        
        if result['needs_clarification']:
            print(f"\n✅ Clarification Required")
            print(f"   Question: {result['question']}")
            print(f"   Missing: {result['missing_context']}")
            print(f"\n   Options ({len(result['options'])}):")
            for idx, option in enumerate(result['options'][:5], 1):  # Show first 5
                print(f"      {idx}. {option['label']}")
            if len(result['options']) > 5:
                print(f"      ... and {len(result['options']) - 5} more")
            
            # Verify expected clarification type
            if test['expected_first']:
                actual = result['missing_context'][0] if result['missing_context'] else None
                if actual == test['expected_first']:
                    print(f"\n   ✓ Correct clarification type: {actual}")
                else:
                    print(f"\n   ✗ Expected {test['expected_first']}, got {actual}")
        else:
            print(f"\n✅ No Clarification Needed - Query is complete")
            if test['expected_first'] is not None:
                print(f"   ✗ Expected clarification for: {test['expected_first']}")
            else:
                print(f"   ✓ Correctly identified as complete")
    
    print(f"\n{'='*80}")
    print("DYNAMIC OPTION VERIFICATION")
    print(f"{'='*80}")
    
    # Test dynamic region extraction
    print("\n🌍 Testing Dynamic Region Extraction...")
    result_aws = clarifier.analyze_query("What are the regional AWS costs?")
    result_azure = clarifier.analyze_query("Show me Azure costs by region")
    
    aws_regions = [opt['value'] for opt in result_aws['options'] if opt['value'] != 'all']
    azure_regions = [opt['value'] for opt in result_azure['options'] if opt['value'] != 'all']
    
    print(f"\nAWS Regions Found: {len(aws_regions)}")
    print(f"   Sample: {', '.join(aws_regions[:3])}")
    
    print(f"\nAzure Regions Found: {len(azure_regions)}")
    print(f"   Sample: {', '.join(azure_regions[:3])}")
    
    # Verify regions are different (provider-specific)
    common = set(aws_regions) & set(azure_regions)
    if len(common) < len(aws_regions) and len(common) < len(azure_regions):
        print(f"\n✓ Provider-specific regions confirmed ({len(common)} common)")
    else:
        print(f"\n✗ Warning: Too many common regions ({len(common)})")
    
    print(f"\n{'='*80}")
    print("✅ ALL TESTS COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    test_clarification_flow()
