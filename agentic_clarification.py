"""
Agentic Clarification Module
Detects ambiguous queries and asks follow-up questions before execution
"""

from typing import Dict
import re


class AgenticClarifier:
    """
    Intelligent query clarification agent that detects ambiguous queries
    and asks follow-up questions to gather missing context
    """
    
    def __init__(self):
        self.clarification_needed = False
        self.clarification_question = None
        self.clarification_options = []
        self.missing_context = []
    
    def analyze_query(self, query: str) -> Dict:
        """
        Analyze a natural language query for ambiguities
        
        Returns:
            Dict with:
            - needs_clarification: bool
            - question: str (follow-up question)
            - options: list (available options)
            - missing_context: list (what's missing)
        """
        query_lower = query.lower()
        
        # Reset state
        self.clarification_needed = False
        self.clarification_question = None
        self.clarification_options = []
        self.missing_context = []
        
        # Check 1: Missing time range for cost queries
        if self._is_cost_query(query_lower) and not self._has_time_range(query_lower):
            self.clarification_needed = True
            self.missing_context.append("time_range")
            self.clarification_question = "Which time range would you like me to use?"
            self.clarification_options = [
                {"value": "last_7_days", "label": "Last 7 days"},
                {"value": "last_30_days", "label": "Last 30 days"},
                {"value": "last_90_days", "label": "Last 90 days"},
                {"value": "this_month", "label": "This month"},
                {"value": "last_month", "label": "Last month"},
                {"value": "year_to_date", "label": "Year to date (YTD)"},
                {"value": "all_time", "label": "All available data"}
            ]
            return self._build_response()
        
        # Check 2: Missing cloud provider (AWS vs Azure)
        if self._mentions_service(query_lower) and not self._has_provider(query_lower):
            self.clarification_needed = True
            self.missing_context.append("provider")
            self.clarification_question = "Which cloud provider would you like to analyze?"
            self.clarification_options = [
                {"value": "aws", "label": "AWS (Amazon Web Services)"},
                {"value": "azure", "label": "Azure (Microsoft Azure)"},
                {"value": "both", "label": "Both AWS and Azure"}
            ]
            return self._build_response()
        
        # Check 3: Ambiguous "cost" without specifying metric type
        if self._has_multiple_cost_types_available(query_lower):
            self.clarification_needed = True
            self.missing_context.append("cost_metric")
            self.clarification_question = "Which cost metric would you like to use?"
            self.clarification_options = [
                {"value": "billedcost", "label": "Billed Cost (actual invoice amount)"},
                {"value": "effectivecost", "label": "Effective Cost (with discounts applied)"}
            ]
            return self._build_response()
        
        # Check 4: Top N queries without specifying N
        if self._is_top_query(query_lower) and not self._has_limit_number(query_lower):
            self.clarification_needed = True
            self.missing_context.append("limit")
            self.clarification_question = "How many results would you like to see?"
            self.clarification_options = [
                {"value": "5", "label": "Top 5"},
                {"value": "10", "label": "Top 10"},
                {"value": "20", "label": "Top 20"},
                {"value": "50", "label": "Top 50"}
            ]
            return self._build_response()
        
        # Check 5: Regional queries without specifying region
        if self._is_regional_query(query_lower) and not self._has_specific_region(query_lower):
            self.clarification_needed = True
            self.missing_context.append("region")
            self.clarification_question = "Which region would you like to analyze?"
            self.clarification_options = [
                {"value": "all", "label": "All regions"},
                {"value": "us-east-1", "label": "US East (N. Virginia)"},
                {"value": "us-west-2", "label": "US West (Oregon)"},
                {"value": "eu-west-1", "label": "EU (Ireland)"},
                {"value": "ap-southeast-2", "label": "Asia Pacific (Sydney)"}
            ]
            return self._build_response()
        
        # No clarification needed
        return {
            "needs_clarification": False,
            "question": None,
            "options": [],
            "missing_context": []
        }
    
    def _build_response(self) -> Dict:
        """Build clarification response"""
        return {
            "needs_clarification": self.clarification_needed,
            "question": self.clarification_question,
            "options": self.clarification_options,
            "missing_context": self.missing_context
        }
    
    def _is_cost_query(self, query: str) -> bool:
        """Check if query is asking about costs"""
        cost_keywords = ["cost", "spend", "bill", "charge", "expense", "price"]
        return any(keyword in query for keyword in cost_keywords)
    
    def _has_time_range(self, query: str) -> bool:
        """Check if query specifies a time range"""
        time_patterns = [
            r'\blast\s+\d+\s+days?\b',
            r'\blast\s+\d+\s+months?\b',
            r'\bthis\s+month\b',
            r'\blast\s+month\b',
            r'\bthis\s+year\b',
            r'\blast\s+year\b',
            r'\bytd\b',
            r'\byear\s+to\s+date\b',
            r'\bq[1-4]\b',
            r'\bquarter\b',
            r'\bjanuary\b|\bfebruary\b|\bmarch\b|\bapril\b|\bmay\b|\bjune\b',
            r'\bjuly\b|\baugust\b|\bseptember\b|\boctober\b|\bnovember\b|\bdecember\b',
            r'\b\d{4}-\d{2}-\d{2}\b',  # Date format
            r'\bbetween\b.*\band\b',    # Between dates
        ]
        return any(re.search(pattern, query) for pattern in time_patterns)
    
    def _mentions_service(self, query: str) -> bool:
        """Check if query mentions a specific service"""
        service_keywords = ["ec2", "s3", "rds", "lambda", "vm", "virtual machine", "storage"]
        return any(keyword in query for keyword in service_keywords)
    
    def _has_provider(self, query: str) -> bool:
        """Check if query specifies cloud provider"""
        providers = ["aws", "amazon", "azure", "microsoft"]
        return any(provider in query for provider in providers)
    
    def _has_multiple_cost_types_available(self, query: str) -> bool:
        """Check if multiple cost types are available and not specified"""
        # If query just says "cost" without specifying type
        has_generic_cost = any(word in query for word in ["cost", "spend"])
        has_specific_type = any(word in query for word in ["billed", "effective", "list", "invoice"])
        return has_generic_cost and not has_specific_type
    
    def _is_top_query(self, query: str) -> bool:
        """Check if query is asking for top N results"""
        top_keywords = ["top", "highest", "most expensive", "biggest", "largest"]
        return any(keyword in query for keyword in top_keywords)
    
    def _has_limit_number(self, query: str) -> bool:
        """Check if query specifies a number limit"""
        # Check for patterns like "top 5", "top 10", etc.
        return bool(re.search(r'\b(top|first|highest)\s+\d+\b', query))
    
    def _is_regional_query(self, query: str) -> bool:
        """Check if query is about regions"""
        region_keywords = ["region", "location", "geography", "where"]
        return any(keyword in query for keyword in region_keywords)
    
    def _has_specific_region(self, query: str) -> bool:
        """Check if query specifies a specific region"""
        region_patterns = [
            r'\bus-east-\d+\b',
            r'\bus-west-\d+\b',
            r'\beu-\w+-\d+\b',
            r'\bap-\w+-\d+\b',
            r'\bvirginia\b',
            r'\boregon\b',
            r'\bireland\b',
            r'\bsydney\b'
        ]
        return any(re.search(pattern, query) for pattern in region_patterns)
    
    def apply_context(self, original_query: str, context_key: str, context_value: str) -> str:
        """
        Apply the clarified context to the original query
        
        Args:
            original_query: Original user query
            context_key: Type of context (time_range, provider, etc.)
            context_value: Selected value
        
        Returns:
            Enhanced query with context
        """
        if context_key == "time_range":
            return self._apply_time_range(original_query, context_value)
        elif context_key == "provider":
            return self._apply_provider(original_query, context_value)
        elif context_key == "cost_metric":
            return self._apply_cost_metric(original_query, context_value)
        elif context_key == "limit":
            return self._apply_limit(original_query, context_value)
        elif context_key == "region":
            return self._apply_region(original_query, context_value)
        
        return original_query
    
    def _apply_time_range(self, query: str, time_range: str) -> str:
        """Apply time range context to query"""
        time_range_map = {
            "last_7_days": "in the last 7 days",
            "last_30_days": "in the last 30 days",
            "last_90_days": "in the last 90 days",
            "this_month": "this month",
            "last_month": "last month",
            "year_to_date": "year to date",
            "all_time": "for all available data"
        }
        time_phrase = time_range_map.get(time_range, time_range)
        return f"{query} {time_phrase}"
    
    def _apply_provider(self, query: str, provider: str) -> str:
        """Apply cloud provider context to query"""
        if provider == "both":
            return f"{query} for both AWS and Azure"
        elif provider == "aws":
            return f"{query} for AWS"
        elif provider == "azure":
            return f"{query} for Azure"
        return query
    
    def _apply_cost_metric(self, query: str, metric: str) -> str:
        """Apply cost metric context to query"""
        # Replace generic "cost" with specific metric
        if metric == "billedcost":
            query = query.replace("cost", "billed cost")
        elif metric == "effectivecost":
            query = query.replace("cost", "effective cost")
        return query
    
    def _apply_limit(self, query: str, limit: str) -> str:
        """Apply limit context to query"""
        if "top" in query.lower():
            # Replace "top" with "top N"
            query = re.sub(r'\btop\b', f'top {limit}', query, flags=re.IGNORECASE)
        else:
            # Add limit to query
            query = f"top {limit} {query}"
        return query
    
    def _apply_region(self, query: str, region: str) -> str:
        """Apply region context to query"""
        if region == "all":
            return query
        return f"{query} in region {region}"


# Example usage and testing
if __name__ == "__main__":
    clarifier = AgenticClarifier()
    
    test_queries = [
        "Show me EC2 cost",
        "What is the total cost?",
        "Show me top services",
        "What are the regional costs?",
        "Show me AWS costs for last month",
        "Show me top 10 Azure services by cost"
    ]
    
    print("=" * 70)
    print("  Agentic Clarification - Test Cases")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = clarifier.analyze_query(query)
        
        if result["needs_clarification"]:
            print(f"❓ {result['question']}")
            print("   Options:")
            for option in result["options"]:
                print(f"   - {option['label']} ({option['value']})")
            print(f"   Missing: {', '.join(result['missing_context'])}")
            
            # Simulate applying context
            if result["options"]:
                selected = result["options"][0]["value"]
                enhanced = clarifier.apply_context(
                    query, 
                    result["missing_context"][0], 
                    selected
                )
                print(f"✅ Enhanced: {enhanced}")
        else:
            print("✅ No clarification needed - query is complete")
        
        print("-" * 70)
