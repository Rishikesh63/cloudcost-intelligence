import os
import re
from typing import Dict
from dotenv import load_dotenv
from semantic_metadata import SemanticMetadataManager
from database_manager import DatabaseManager


class Text2SQLEngine:
    """Converts natural language queries to SQL using semantic metadata and Ollama LLM"""
    
    def __init__(self, db_path="cloud_cost.db", use_llm=True):
        load_dotenv()
        self.db = DatabaseManager(db_path)
        self.db.connect()
        self.metadata_manager = SemanticMetadataManager(db_path)
        self.use_llm = use_llm
        self.client = None
        self.model_name = None
        
        if use_llm:
            self._init_ollama()
    
    def _init_ollama(self):
        """Initialize Ollama (local, FREE, and PRIVATE)"""
        try:
            from openai import OpenAI
            base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1')
            
            # Initialize client
            try:
                self.client = OpenAI(
                    base_url=base_url,
                    api_key='ollama'  # Ollama doesn't require real API key
                )
            except TypeError:
                # Fallback for older openai versions
                self.client = OpenAI(
                    base_url=base_url,
                    api_key='ollama'
                )
            
            self.model_name = os.getenv('OLLAMA_MODEL', 'llama3.2')
            
            # Test connection
            try:
                self.client.models.list()
                print(f"✅ Connected to Ollama - Model: {self.model_name}")
            except Exception:
                print("⚠️ Ollama not responding. Make sure it's running:")
                print("   1. Install from: https://ollama.ai")
                print(f"   2. Pull model: ollama pull {self.model_name}")
                print("   3. Start server: ollama serve")
                print("   Falling back to rule-based conversion...")
                self.use_llm = False
                self.client = None
                
        except ImportError:
            print("⚠️ OpenAI library not installed. Run: pip install openai")
            print("   Falling back to rule-based conversion...")
            self.use_llm = False
        except Exception as e:
            print(f"⚠️ Ollama initialization error: {e}")
            print("   Falling back to rule-based conversion...")
            self.use_llm = False
    
    def analyze_intent(self, natural_query: str) -> Dict:
        """Analyze user intent from natural language query"""
        intent = {
            "query_type": None,  # SELECT, aggregation, comparison, etc.
            "table": None,
            "columns": [],
            "aggregations": {},
            "filters": [],
            "group_by": [],
            "order_by": None,
            "limit": None
        }
        
        query_lower = natural_query.lower()
        
        # Determine table
        intent["table"] = self.metadata_manager.get_table_from_intent(natural_query)
        if not intent["table"]:
            # If no specific provider mentioned, check both tables
            intent["table"] = "aws_cost"  # Default to AWS for now
        
        # Detect aggregation patterns
        if any(word in query_lower for word in ["total", "sum", "average", "avg", "count", "max", "min"]):
            intent["query_type"] = "aggregation"
        else:
            intent["query_type"] = "select"
        
        # Detect GROUP BY patterns
        if any(phrase in query_lower for phrase in ["by service", "by region", "by account", "per service", "per region", "breakdown"]):
            if "service" in query_lower:
                intent["group_by"].append("servicename")
            if "region" in query_lower:
                intent["group_by"].append("regionname")
            if "account" in query_lower or "subscription" in query_lower:
                intent["group_by"].append("subaccountname")
        
        # Detect ORDER BY patterns
        if "top" in query_lower or "highest" in query_lower:
            intent["order_by"] = {"column": "billedcost", "direction": "DESC"}
            # Extract limit number
            top_match = re.search(r'top\s+(\d+)', query_lower)
            if top_match:
                intent["limit"] = int(top_match.group(1))
        elif "lowest" in query_lower or "bottom" in query_lower:
            intent["order_by"] = {"column": "billedcost", "direction": "ASC"}
        
        # Detect columns
        if "cost" in query_lower or "spend" in query_lower or "bill" in query_lower:
            intent["columns"].append("billedcost")
        
        return intent
    
    def build_sql_from_intent(self, intent: Dict, natural_query: str) -> str:
        """Build SQL query from analyzed intent"""
        table = intent["table"]
        
        # Determine columns to select
        if intent["query_type"] == "aggregation":
            select_parts = []
            
            # Get aggregation function
            agg_func = self.metadata_manager.get_aggregation_function(
                natural_query, "billedcost", table
            )
            select_parts.append(f"{agg_func}(billedcost) as total_cost")
            
            # Add group by columns
            for col in intent["group_by"]:
                select_parts.append(col)
            
            select_clause = ", ".join(select_parts)
        else:
            select_clause = "*"
        
        # Build base query
        sql = f"SELECT {select_clause} FROM {table}"
        
        # Add WHERE clause if filters exist
        if intent["filters"]:
            where_conditions = " AND ".join(intent["filters"])
            sql += f" WHERE {where_conditions}"
        
        # Add GROUP BY
        if intent["group_by"]:
            group_by_clause = ", ".join(intent["group_by"])
            sql += f" GROUP BY {group_by_clause}"
        
        # Add ORDER BY
        if intent["order_by"]:
            sql += f" ORDER BY {intent['order_by']['column']} {intent['order_by']['direction']}"
        
        # Add LIMIT
        if intent["limit"]:
            sql += f" LIMIT {intent['limit']}"
        elif not intent["limit"] and intent["query_type"] == "select":
            sql += " LIMIT 10"  # Default limit for select queries
        
        return sql
    
    def convert_with_llm(self, natural_query: str) -> str:
        """Convert natural language to SQL using LLM"""
        
        # Get schema information
        schema_info = self._get_schema_context()
        
        # Create prompt with semantic metadata
        prompt = f"""You are a SQL expert. Convert the following natural language question into a SQL query.

Database Schema:
{schema_info}

Important Guidelines:
1. ALL column names are lowercase without underscores (e.g., billedcost, servicename, regionname)
2. For cost queries, use billedcost column
3. For service queries, use servicename column
4. For region queries, use regionname column
5. For account queries, use subaccountname column
6. Always use appropriate aggregations (SUM for costs, COUNT for counts)
7. Add appropriate GROUP BY clauses when aggregating
8. Add ORDER BY DESC when asking for "top" or "highest"
9. Add LIMIT when asking for specific number of results
10. Use LIKE '%value%' for text searches

Natural Language Question: {natural_query}

Generate ONLY the SQL query without any explanation or markdown formatting:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a SQL expert that converts natural language to SQL queries. Return only the SQL query without explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Clean up the response
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            
            return sql_query
            
        except Exception as e:
            print(f"Error using LLM: {str(e)}")
            return None
    
    def _get_schema_context(self) -> str:
        """Get formatted schema information for LLM context"""
        context = ""
        
        for table_name in ["aws_cost", "azure_cost"]:
            context += f"\nTable: {table_name}\n"
            context += f"Description: {self.metadata_manager.metadata[table_name]['description']}\n"
            context += "Columns:\n"
            
            for col_name, col_meta in self.metadata_manager.metadata[table_name]["columns"].items():
                context += f"  - {col_name} ({col_meta['data_type']}): {col_meta['description']}\n"
                if "aliases" in col_meta:
                    context += f"    Aliases: {', '.join(col_meta['aliases'][:3])}\n"
        
        return context
    
    def convert_to_sql(self, natural_query: str):
        """
        Convert natural language query to SQL
        Returns: (sql_query, method_used)
        """
        # Try Ollama-based conversion first if available
        if self.use_llm and self.client:
            sql_query = self.convert_with_llm(natural_query)
            if sql_query:
                return sql_query, "Ollama"
        
        # Fallback to rule-based conversion
        intent = self.analyze_intent(natural_query)
        sql_query = self.build_sql_from_intent(intent, natural_query)
        return sql_query, "Rule-based"
    
    def execute_natural_query(self, natural_query: str):
        """
        Execute natural language query and return results
        Returns: Dict with sql, results, and metadata
        """
        # Convert to SQL
        sql_query, method = self.convert_to_sql(natural_query)
        
        # Execute query
        results = self.db.execute_query(sql_query)
        
        return {
            "natural_query": natural_query,
            "sql_query": sql_query,
            "method": method,
            "results": results,
            "row_count": len(results) if results is not None else 0
        }
    
    def close(self):
        """Close database connection"""
        self.db.close()


# Example usage and test queries
if __name__ == "__main__":
    engine = Text2SQLEngine()
    
    test_queries = [
        "What is the total cost for AWS?",
        "Show me top 5 services by cost",
        "What are the costs by region?",
        "Show me Azure costs by service",
        "What is the average cost per service?",
    ]
    
    print("Testing Text2SQL Engine\n" + "="*50)
    
    for query in test_queries:
        print(f"\nNatural Query: {query}")
        result = engine.execute_natural_query(query)
        print(f"SQL Query: {result['sql_query']}")
        print(f"Method: {result['method']}")
        print(f"Results: {result['row_count']} rows")
        if result['results'] is not None and len(result['results']) > 0:
            print(result['results'].head())
        print("-"*50)
    
    engine.close()
