"""
Agentic Clarification Module
Detects ambiguous queries and asks follow-up questions before execution
Now with dynamic option generation based on actual database content
"""

from typing import Dict, Optional
import re
from database_manager import DatabaseManager
from semantic_metadata import SemanticMetadataManager


class AgenticClarifier:
    """
    Intelligent query clarification agent that detects ambiguous queries
    and asks follow-up questions to gather missing context.
    Generates clarification options dynamically based on database content.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None, metadata_manager: Optional[SemanticMetadataManager] = None):
        self.clarification_needed = False
        self.clarification_question = None
        self.clarification_options = []
        self.missing_context = []
        
        # Initialize database and metadata managers
        self.db_manager = db_manager or self._init_db_manager()
        self.metadata_manager = metadata_manager or SemanticMetadataManager()
    
    def _init_db_manager(self) -> DatabaseManager:
        """Initialize database manager if not provided"""
        db = DatabaseManager()
        db.connect()
        return db
    
    def analyze_query(self, query: str, provider_context: Optional[str] = None) -> Dict:
        """
        Analyze query for ambiguities and determine needed clarifications.
        Now generates options dynamically from database.
        
        Args:
            query: User's natural language query
            provider_context: Optional provider context (aws/azure/both)
        
        Returns:
            Dict with clarification details
        """
        query_lower = query.lower()
        
        # Reset state
        self.clarification_needed = False
        self.clarification_question = None
        self.clarification_options = []
        self.missing_context = []
        
        # Determine which tables to query based on provider context
        tables = self._get_tables_for_query(query_lower, provider_context)
        
        # Check 1: Provider not specified
        if not self._has_provider(query_lower) and not provider_context:
            self.clarification_needed = True
            self.missing_context.append("provider")
            self.clarification_question = "Which cloud provider would you like to analyze?"
            self.clarification_options = [
                {"value": "both", "label": "Both AWS and Azure"},
                {"value": "aws", "label": "AWS only"},
                {"value": "azure", "label": "Azure only"}
            ]
            return self._build_response()
        
        # Check 2: Regional queries without specifying region (check before time range)
        if self._is_regional_query(query_lower) and not self._has_specific_region(query_lower):
            self.clarification_needed = True
            self.missing_context.append("region")
            self.clarification_question = "Which region would you like to analyze?"
            # Generate dynamic region options based on available data
            self.clarification_options = self._get_dynamic_regions(tables)
            return self._build_response()
        
        # Check 3: Time range not specified for cost queries
        if self._is_cost_query(query_lower) and not self._has_time_range(query_lower):
            self.clarification_needed = True
            self.missing_context.append("time_range")
            self.clarification_question = "What time period would you like to analyze?"
            # Generate dynamic time range options based on available data
            self.clarification_options = self._get_dynamic_time_ranges(tables)
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
        
        # No clarification needed
        return {
            "needs_clarification": False,
            "question": None,
            "options": [],
            "missing_context": []
        }
    
    def _get_tables_for_query(self, query: str, provider_context: Optional[str] = None) -> list:
        """Determine which tables to query based on provider context"""
        if provider_context == "aws":
            return ["aws_cost_usage"]
        elif provider_context == "azure":
            return ["azure_cost_usage"]
        elif provider_context == "both":
            return ["aws_cost_usage", "azure_cost_usage"]
        
        # Infer from query
        if "aws" in query or "amazon" in query:
            return ["aws_cost_usage"]
        elif "azure" in query or "microsoft" in query:
            return ["azure_cost_usage"]
        else:
            return ["aws_cost_usage", "azure_cost_usage"]
    
    def _get_dynamic_time_ranges(self, tables: list) -> list:
        """Generate time range options based on actual data in the database"""
        try:
            all_dates = []
            for table in tables:
                query = f"""
                    SELECT 
                        MIN(billingperiodstart) as min_date,
                        MAX(billingperiodend) as max_date
                    FROM {table}
                    WHERE billingperiodstart IS NOT NULL
                """
                result = self.db_manager.execute_query(query)
                if result is not None and not result.empty:
                    all_dates.append(result.iloc[0])
            
            if not all_dates:
                # Fallback to default options if no data
                return self._get_default_time_ranges()
            
            # Build dynamic options based on available date range
            # For now, use sensible defaults but this could be further enhanced
            return [
                {"value": "last_7_days", "label": "Last 7 days"},
                {"value": "last_30_days", "label": "Last 30 days"},
                {"value": "last_90_days", "label": "Last 90 days"},
                {"value": "this_month", "label": "This month"},
                {"value": "last_month", "label": "Last month"},
                {"value": "year_to_date", "label": "Year to date"},
                {"value": "all_time", "label": "All available data"}
            ]
        except Exception as e:
            print(f"Error getting dynamic time ranges: {e}")
            return self._get_default_time_ranges()
    
    def _get_default_time_ranges(self) -> list:
        """Get default time range options"""
        return [
            {"value": "last_7_days", "label": "Last 7 days"},
            {"value": "last_30_days", "label": "Last 30 days"},
            {"value": "last_90_days", "label": "Last 90 days"},
            {"value": "this_month", "label": "This month"},
            {"value": "last_month", "label": "Last month"},
            {"value": "year_to_date", "label": "Year to date"},
            {"value": "all_time", "label": "All available data"}
        ]
    
    def _get_dynamic_regions(self, tables: list) -> list:
        """Generate region options based on actual data in the database"""
        try:
            all_regions = set()
            for table in tables:
                query = f"""
                    SELECT DISTINCT regionname
                    FROM {table}
                    WHERE regionname IS NOT NULL AND regionname != ''
                    ORDER BY regionname
                    LIMIT 20
                """
                result = self.db_manager.execute_query(query)
                if result is not None and not result.empty:
                    all_regions.update(result['regionname'].tolist())
            
            if not all_regions:
                # Fallback to default options if no data
                return self._get_default_regions()
            
            # Build options from actual regions
            options = [{"value": "all", "label": "All regions"}]
            for region in sorted(all_regions)[:10]:  # Limit to top 10 for UI
                options.append({"value": region, "label": region})
            
            return options
        except Exception as e:
            print(f"Error getting dynamic regions: {e}")
            return self._get_default_regions()
    
    def _get_default_regions(self) -> list:
        """Get default region options"""
        return [
            {"value": "all", "label": "All regions"},
            {"value": "us-east-1", "label": "US East (N. Virginia)"},
            {"value": "us-west-2", "label": "US West (Oregon)"},
            {"value": "eu-west-1", "label": "EU (Ireland)"},
            {"value": "ap-southeast-2", "label": "Asia Pacific (Sydney)"}
        ]
    
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
        """Check if query mentions a SPECIFIC service (not the generic word 'service')"""
        # Only trigger if user mentions a specific service name
        # NOT if they just say "services" or "service" generically
        specific_service_keywords = [
            "ec2", "s3", "rds", "lambda", "dynamodb", "cloudfront", "route53",
            "vm", "virtual machine", "blob storage", "cosmos", "sql database",
            "compute", "storage account", "app service"
        ]
        
        # Check if any specific service is mentioned
        for keyword in specific_service_keywords:
            if keyword in query:
                return True
        
        # Don't trigger for generic "service" or "services" 
        # (which is just asking to see all services)
        return False
    
    def _has_provider(self, query: str) -> bool:
        """Check if query specifies cloud provider"""
        providers = ["aws", "amazon", "azure", "microsoft"]
        return any(provider in query for provider in providers)
    
    def _is_generic_service_query(self, query: str) -> bool:
        """Check if query is asking generically about services (not a specific service)"""
        # Queries like "show me services", "list services", "top services"
        generic_patterns = [
            r'\bservices?\b.*\bby\s+cost\b',  # "services by cost"
            r'\btop\s+\d*\s*services?\b',      # "top 10 services"
            r'\blist\s+services?\b',           # "list services"
            r'\bshow\s+.*\bservices?\b',       # "show me services"
            r'\ball\s+services?\b',            # "all services"
        ]
        return any(re.search(pattern, query) for pattern in generic_patterns)
    
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
    print("  Agentic Clarification - Test Cases (Dynamic Options)")
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
