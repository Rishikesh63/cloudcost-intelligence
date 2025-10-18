"""
JSON Query Helpers
Utilities for extracting and querying JSON data from cost columns (tags, cost_categories)
"""

import json
import pandas as pd
from typing import Set, Optional


class JSONQueryHelper:
    """Helper class for querying JSON fields in cost data"""
    
    def __init__(self, db_manager):
        """
        Initialize with a database manager instance
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
    
    def extract_json_field(self, table_name: str, json_column: str, json_key: str) -> Optional[pd.DataFrame]:
        """
        Extract a specific field from a JSON column
        Useful for querying tags or cost_categories
        
        Args:
            table_name: Name of the table (aws_cost_usage or azure_cost_usage)
            json_column: Column containing JSON data (e.g., 'tags', 'cost_categories')
            json_key: Key to extract from JSON (e.g., 'Environment', 'Team')
        
        Returns:
            DataFrame with extracted values and aggregated costs
        
        Example:
            >>> helper = JSONQueryHelper(db_manager)
            >>> helper.extract_json_field('aws_cost_usage', 'tags', 'Environment')
            
            Result:
            | Environment | total_cost | record_count |
            |-------------|------------|--------------|
            | Production  | 15234.56   | 523          |
            | Development | 8765.43    | 234          |
        """
        query = f"""
            SELECT 
                json_extract({json_column}, '$.{json_key}') as {json_key},
                SUM(billed_cost) as total_cost,
                SUM(effective_cost) as effective_cost,
                COUNT(*) as record_count
            FROM {table_name}
            WHERE {json_column} IS NOT NULL 
                AND {json_column} != ''
                AND json_extract({json_column}, '$.{json_key}') IS NOT NULL
            GROUP BY json_extract({json_column}, '$.{json_key}')
            ORDER BY total_cost DESC
        """
        return self.db.execute_query(query)
    
    def get_available_json_keys(self, table_name: str, json_column: str, limit: int = 100) -> Set[str]:
        """
        Get all available keys from a JSON column
        Useful for discovering available tags or cost categories
        
        Args:
            table_name: Name of the table
            json_column: Column containing JSON data (e.g., 'tags')
            limit: Number of rows to sample (default: 100)
        
        Returns:
            Set of all unique keys found in the JSON column
        
        Example:
            >>> helper.get_available_json_keys('aws_cost_usage', 'tags')
            {'Environment', 'Team', 'Project', 'CostCenter', 'Owner'}
        """
        query = f"""
            SELECT DISTINCT {json_column}
            FROM {table_name}
            WHERE {json_column} IS NOT NULL 
                AND {json_column} != ''
            LIMIT {limit}
        """
        df = self.db.execute_query(query)
        
        if df is None or df.empty:
            return set()
        
        # Extract all unique keys from JSON strings
        keys = set()
        for json_str in df[json_column]:
            try:
                if json_str:
                    data = json.loads(json_str)
                    if isinstance(data, dict):
                        keys.update(data.keys())
            except (json.JSONDecodeError, TypeError):
                continue
        
        return keys
    
    def query_by_tag(self, table_name: str, tag_key: str, tag_value: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Query costs filtered by a specific tag
        
        Args:
            table_name: Name of the table (aws_cost_usage or azure_cost_usage)
            tag_key: Tag key to filter by (e.g., 'Environment', 'Team')
            tag_value: Optional specific value to filter (e.g., 'Production')
                      If None, returns all values grouped by tag_key
        
        Returns:
            DataFrame with cost breakdown by tag
        
        Examples:
            >>> # Get all costs by environment
            >>> helper.query_by_tag('aws_cost_usage', 'Environment')
            
            >>> # Get only production environment costs
            >>> helper.query_by_tag('aws_cost_usage', 'Environment', 'Production')
        """
        if tag_value:
            # Filter by specific tag value
            query = f"""
                SELECT 
                    service_name,
                    region_name,
                    json_extract(tags, '$.{tag_key}') as {tag_key},
                    SUM(billed_cost) as total_cost,
                    SUM(effective_cost) as effective_cost,
                    COUNT(*) as record_count
                FROM {table_name}
                WHERE json_extract(tags, '$.{tag_key}') = '{tag_value}'
                GROUP BY service_name, region_name, json_extract(tags, '$.{tag_key}')
                ORDER BY total_cost DESC
            """
        else:
            # Group by all values of the tag
            query = f"""
                SELECT 
                    json_extract(tags, '$.{tag_key}') as {tag_key},
                    SUM(billed_cost) as total_cost,
                    SUM(effective_cost) as effective_cost,
                    COUNT(*) as record_count
                FROM {table_name}
                WHERE json_extract(tags, '$.{tag_key}') IS NOT NULL
                GROUP BY json_extract(tags, '$.{tag_key}')
                ORDER BY total_cost DESC
            """
        
        return self.db.execute_query(query)
    
    def query_by_cost_category(self, table_name: str, category_key: str, category_value: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Query costs filtered by cost category
        
        Args:
            table_name: Name of the table
            category_key: Cost category key (e.g., 'CostCenter', 'Project')
            category_value: Optional specific value to filter
        
        Returns:
            DataFrame with cost breakdown by category
        """
        json_column = 'cost_categories'
        
        if category_value:
            query = f"""
                SELECT 
                    service_name,
                    json_extract({json_column}, '$.{category_key}') as {category_key},
                    SUM(billed_cost) as total_cost,
                    SUM(effective_cost) as effective_cost,
                    COUNT(*) as record_count
                FROM {table_name}
                WHERE json_extract({json_column}, '$.{category_key}') = '{category_value}'
                GROUP BY service_name, json_extract({json_column}, '$.{category_key}')
                ORDER BY total_cost DESC
            """
        else:
            query = f"""
                SELECT 
                    json_extract({json_column}, '$.{category_key}') as {category_key},
                    SUM(billed_cost) as total_cost,
                    SUM(effective_cost) as effective_cost,
                    COUNT(*) as record_count
                FROM {table_name}
                WHERE json_extract({json_column}, '$.{category_key}') IS NOT NULL
                GROUP BY json_extract({json_column}, '$.{category_key}')
                ORDER BY total_cost DESC
            """
        
        return self.db.execute_query(query)
    
    def generate_tag_query_sql(self, table_name: str, tag_key: str, tag_value: Optional[str] = None, 
                                group_by: Optional[list] = None, order_by: str = "total_cost DESC") -> str:
        """
        Generate SQL query for tag-based analysis
        Useful for the Text2SQL engine to incorporate JSON extraction
        
        Args:
            table_name: Table name
            tag_key: Tag key to extract
            tag_value: Optional value to filter
            group_by: Additional columns to group by (e.g., ['service_name', 'region_name'])
            order_by: Order clause (default: 'total_cost DESC')
        
        Returns:
            SQL query string
        
        Example:
            >>> sql = helper.generate_tag_query_sql(
            ...     'aws_cost_usage', 
            ...     'Environment', 
            ...     group_by=['service_name']
            ... )
            >>> print(sql)
            SELECT 
                service_name,
                json_extract(tags, '$.Environment') as Environment,
                SUM(billed_cost) as total_cost
            FROM aws_cost_usage
            WHERE json_extract(tags, '$.Environment') IS NOT NULL
            GROUP BY service_name, json_extract(tags, '$.Environment')
            ORDER BY total_cost DESC
        """
        # Build SELECT clause
        select_cols = []
        if group_by:
            select_cols.extend(group_by)
        select_cols.append(f"json_extract(tags, '$.{tag_key}') as {tag_key}")
        select_cols.append("SUM(billed_cost) as total_cost")
        select_cols.append("SUM(effective_cost) as effective_cost")
        
        # Build WHERE clause
        where_clause = f"json_extract(tags, '$.{tag_key}') IS NOT NULL"
        if tag_value:
            where_clause += f" AND json_extract(tags, '$.{tag_key}') = '{tag_value}'"
        
        # Build GROUP BY clause
        group_clause = []
        if group_by:
            group_clause.extend(group_by)
        group_clause.append(f"json_extract(tags, '$.{tag_key}')")
        
        # Construct query
        query = f"""
            SELECT 
                {', '.join(select_cols)}
            FROM {table_name}
            WHERE {where_clause}
            GROUP BY {', '.join(group_clause)}
            ORDER BY {order_by}
        """
        
        return query.strip()
    
    def detect_tag_query(self, natural_query: str) -> Optional[dict]:
        """
        Detect if a natural language query is asking for tag-based analysis
        
        Args:
            natural_query: Natural language query from user
        
        Returns:
            Dictionary with tag analysis details or None
        
        Example:
            >>> helper.detect_tag_query("Show me costs by environment tag")
            {
                'is_tag_query': True,
                'tag_key': 'Environment',
                'column': 'tags'
            }
        """
        query_lower = natural_query.lower()
        
        # Common tag-related keywords
        tag_indicators = ['tag', 'tagged', 'label', 'labeled']
        
        if not any(indicator in query_lower for indicator in tag_indicators):
            return None
        
        # Common tag keys
        common_tags = {
            'environment': 'Environment',
            'env': 'Environment',
            'team': 'Team',
            'project': 'Project',
            'owner': 'Owner',
            'cost center': 'CostCenter',
            'costcenter': 'CostCenter',
            'application': 'Application',
            'app': 'Application'
        }
        
        # Try to detect tag key
        detected_tag = None
        for keyword, tag_name in common_tags.items():
            if keyword in query_lower:
                detected_tag = tag_name
                break
        
        if detected_tag:
            return {
                'is_tag_query': True,
                'tag_key': detected_tag,
                'column': 'tags'
            }
        
        # Generic tag query detected but no specific tag identified
        return {
            'is_tag_query': True,
            'tag_key': None,  # Needs clarification
            'column': 'tags'
        }


# Standalone helper functions for direct use
def extract_tag_value(db_manager, table_name: str, tag_key: str) -> Optional[pd.DataFrame]:
    """
    Quick function to extract costs by tag
    
    Example:
        >>> from json_query_helpers import extract_tag_value
        >>> df = extract_tag_value(db, 'aws_cost_usage', 'Environment')
    """
    helper = JSONQueryHelper(db_manager)
    return helper.extract_json_field(table_name, 'tags', tag_key)


def get_all_tags(db_manager, table_name: str) -> Set[str]:
    """
    Quick function to get all available tags
    
    Example:
        >>> from json_query_helpers import get_all_tags
        >>> tags = get_all_tags(db, 'aws_cost_usage')
        >>> print(tags)
        {'Environment', 'Team', 'Project'}
    """
    helper = JSONQueryHelper(db_manager)
    return helper.get_available_json_keys(table_name, 'tags')


# Example usage and testing
if __name__ == "__main__":
    from database_manager import DatabaseManager
    
    # Initialize
    db = DatabaseManager()
    db.connect()
    helper = JSONQueryHelper(db)
    
    print("=" * 70)
    print("  JSON Query Helpers - Test Cases")
    print("=" * 70)
    
    # Test 1: Get available tags
    print("\n1️⃣ Discovering available tags...")
    tags = helper.get_available_json_keys('aws_cost_usage', 'tags')
    print(f"   Available tags: {tags}")
    
    # Test 2: Extract costs by Environment tag
    if 'Environment' in tags:
        print("\n2️⃣ Costs by Environment tag:")
        df = helper.extract_json_field('aws_cost_usage', 'tags', 'Environment')
        if df is not None and not df.empty:
            print(df.to_string(index=False))
    
    # Test 3: Query specific tag value
    print("\n3️⃣ Production environment costs:")
    df = helper.query_by_tag('aws_cost_usage', 'Environment', 'Production')
    if df is not None and not df.empty:
        print(df.head().to_string(index=False))
    
    # Test 4: Generate SQL
    print("\n4️⃣ Generated SQL for tag query:")
    sql = helper.generate_tag_query_sql(
        'aws_cost_usage', 
        'Environment', 
        group_by=['service_name']
    )
    print(sql)
    
    # Test 5: Detect tag queries
    print("\n5️⃣ Natural language tag detection:")
    test_queries = [
        "Show me costs by environment tag",
        "What is the team spending?",
        "Total cost by project tag",
        "Show me EC2 costs"  # Not a tag query
    ]
    
    for query in test_queries:
        result = helper.detect_tag_query(query)
        if result and result['is_tag_query']:
            print(f"   ✅ '{query}' → Tag: {result.get('tag_key', 'Unknown')}")
        else:
            print(f"   ❌ '{query}' → Not a tag query")
    
    db.close()
    print("\n" + "=" * 70)
