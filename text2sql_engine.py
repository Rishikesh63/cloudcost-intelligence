import os
import re
from typing import Dict, Optional
from dotenv import load_dotenv
from semantic_metadata import SemanticMetadataManager
from database_manager import DatabaseManager
from agentic_clarification import AgenticClarifier


class Text2SQLEngine:
    """Converts natural language queries to SQL using semantic metadata and Ollama LLM"""
    
    def __init__(self, db_path="cloud_cost.db", use_llm=True):
        load_dotenv()
        self.db = DatabaseManager(db_path)
        self.db.connect()
        self.metadata_manager = SemanticMetadataManager(db_path)
        # Pass database manager to clarifier for dynamic option generation
        self.clarifier = AgenticClarifier(db_manager=self.db, metadata_manager=self.metadata_manager)
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
    
    def analyze_intent_with_llm(self, natural_query: str) -> Dict:
        """Use LLM to analyze user intent - better than regex!"""
        if not self.use_llm or not self.client:
            return self.analyze_intent_fallback(natural_query)
        
        try:
            # Get semantic metadata context
            metadata_context = self._get_metadata_summary()
            
            prompt = f"""You are an expert at analyzing database queries. Analyze this natural language query and extract the intent.

Database Schema (SQLite):
{metadata_context}

User Query: "{natural_query}"

Analyze and respond in JSON format with:
{{
  "query_type": "aggregation" or "select" or "filter",
  "table": "aws_cost_usage" or "azure_cost_usage" or "both",
  "columns": ["column names needed"],
  "aggregations": {{"column": "SUM/AVG/COUNT/MAX/MIN"}},
  "group_by": ["columns to group by"],
  "order_by": {{"column": "column_name", "direction": "ASC/DESC"}},
  "limit": number or null,
  "filters": [{{"column": "name", "operator": "=/>/<", "value": "x"}}]
}}

Important: For date filters in SQLite:
- Last 7 days: date(columnname) >= date('now', '-7 days')
- Last 30 days: date(columnname) >= date('now', '-30 days')
- Date columns: billingperiodstart, billingperiodend

Think step by step:
1. What data is the user asking for? (columns)
2. Do they want aggregations? (total, average, count)
3. Do they want to group results? (by service, by region)
4. Do they want filtering? (specific service, time range)
5. Do they want sorting? (top N, highest, lowest)

Return ONLY the JSON, no explanation."""

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            import json
            intent_text = response.choices[0].message.content.strip()
            # Extract JSON from markdown code blocks if present
            if "```json" in intent_text:
                intent_text = intent_text.split("```json")[1].split("```")[0].strip()
            elif "```" in intent_text:
                intent_text = intent_text.split("```")[1].split("```")[0].strip()
            
            intent = json.loads(intent_text)
            return intent
            
        except Exception as e:
            print(f"⚠️ LLM intent analysis failed: {e}")
            return self.analyze_intent_fallback(natural_query)
    
    def analyze_intent_fallback(self, natural_query: str) -> Dict:
        """Fallback regex-based intent analysis (when LLM unavailable)"""
        intent = {
            "query_type": None,
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
            intent["table"] = "aws_cost_usage"
        
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
11. **CRITICAL: This is SQLite database - use SQLite date functions:**
    - For date filtering: date(columnname) >= date('now', '-7 days')
    - For date comparison: date(columnname) BETWEEN date('now', '-30 days') AND date('now')
    - For date extraction: strftime('%Y-%m-%d', columnname)
    - DO NOT use DATE_SUB, INTERVAL, CURRENT_DATE - use SQLite functions only!
12. Date columns: billingperiodstart, billingperiodend, chargeperiodstart, chargeperiodend
13. **CRITICAL: Region names are human-readable, NOT region codes:**
    - Database has: "US East (N. Virginia)", "Asia Pacific (Sydney)", "EU (Frankfurt)"
    - NOT AWS codes like: "us-east-1", "ap-southeast-2", "eu-central-1"
    - When user mentions a specific region, use LIKE '%region_keyword%' to match
    - Example: "us-east-1" should match "US East (N. Virginia)"
    - Example: "sydney" should match "Asia Pacific (Sydney)"
14. **Question Analysis for "top N regions in region X":**
    - This is likely asking for services/resources IN that region, not comparing regions
    - If asking "top 5 most expensive in us-east-1" → show top 5 services in that region
    - NOT: GROUP BY regionname (would only return 1 row)
    - YES: WHERE regionname LIKE '%East%' GROUP BY servicename
15. **CRITICAL - UNION Queries for BOTH AWS and Azure:**
    - IMPORTANT: ORDER BY and LIMIT must come AFTER the entire UNION, NOT before
    - Each SELECT in UNION should NOT have its own ORDER BY or LIMIT
    - CORRECT FORMAT:
      SELECT 'AWS' as provider, servicename, SUM(billedcost) as cost 
      FROM aws_cost_usage 
      WHERE condition
      GROUP BY servicename
      UNION ALL
      SELECT 'Azure' as provider, servicename, SUM(billedcost) as cost
      FROM azure_cost_usage 
      WHERE condition
      GROUP BY servicename
      ORDER BY cost DESC
      LIMIT 10
    - WRONG FORMAT (DO NOT DO THIS):
      SELECT ... ORDER BY cost DESC LIMIT 5
      UNION ALL  
      SELECT ... ORDER BY cost DESC LIMIT 5
    - NO parentheses around SELECT statements in UNION
    - NO subqueries like (SELECT * FROM table)
    - Each SELECT must have same number and type of columns
16. **CRITICAL - RESOURCETYPE Values (Case-sensitive!):**
    - User may say "EC2" or "VM" but database uses different values
    - AWS resourcetype values: 'instance' (NOT 'EC2'), 'bucket' (NOT 'S3'), 'volume' (NOT 'EBS'), 'distribution', or empty ''
    - Azure resourcetype values: 'Virtual machine' (NOT 'VM'), 'Storage account', 'Disk', 'Key vault', 'App Service web app'
    - When user asks about EC2, use: RESOURCETYPE = 'instance'
    - When user asks about VMs, use: RESOURCETYPE = 'Virtual machine'
    - When user asks about S3, use: RESOURCETYPE = 'bucket'
    - Most AWS records have EMPTY resourcetype, so if query returns 0 results, remove the resourcetype filter
17. **Filter with BILLEDCOST > 0:**
    - Always include "WHERE billedcost > 0" or "AND billedcost > 0" to exclude zero-cost entries
    - This ensures meaningful cost analysis results

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
            
            # Convert MySQL syntax to SQLite syntax
            sql_query = self._convert_to_sqlite_syntax(sql_query)
            
            # Fix UNION query syntax
            sql_query = self._fix_union_syntax(sql_query)
            
            # Normalize region filters (region codes to names)
            sql_query = self._normalize_region_filter(sql_query)
            
            # Normalize resource type filters (EC2 -> instance, VM -> Virtual machine, etc.)
            sql_query = self._normalize_resourcetype_filter(sql_query)
            
            return sql_query
            
        except Exception as e:
            print(f"Error using LLM: {str(e)}")
            return None
    
    def _convert_to_sqlite_syntax(self, sql: str) -> str:
        """Convert MySQL/PostgreSQL syntax to SQLite syntax"""
        
        # Replace CURRENT_DATE with date('now')
        sql = sql.replace("CURRENT_DATE", "date('now')")
        
        # Replace DATE_SUB(CURRENT_DATE, INTERVAL X DAY) with date('now', '-X days')
        sql = re.sub(
            r"DATE_SUB\(CURRENT_DATE,\s*INTERVAL\s+(\d+)\s+DAY\)",
            r"date('now', '-\1 days')",
            sql,
            flags=re.IGNORECASE
        )
        
        # Replace DATE_SUB(date('now'), INTERVAL X DAY) with date('now', '-X days')
        sql = re.sub(
            r"DATE_SUB\(date\('now'\),\s*INTERVAL\s+(\d+)\s+DAY\)",
            r"date('now', '-\1 days')",
            sql,
            flags=re.IGNORECASE
        )
        
        # Replace DATE_ADD patterns
        sql = re.sub(
            r"DATE_ADD\(CURRENT_DATE,\s*INTERVAL\s+(\d+)\s+DAY\)",
            r"date('now', '+\1 days')",
            sql,
            flags=re.IGNORECASE
        )
        
        # Replace NOW() with datetime('now')
        sql = re.sub(r"\bNOW\(\)", "datetime('now')", sql, flags=re.IGNORECASE)
        
        # Replace CURDATE() with date('now')
        sql = re.sub(r"\bCURDATE\(\)", "date('now')", sql, flags=re.IGNORECASE)
        
        # Fix column names with underscores to lowercase without underscores
        # billing_period_start -> billingperiodstart
        column_mappings = {
            'billing_period_start': 'billingperiodstart',
            'billing_period_end': 'billingperiodend',
            'charge_period_start': 'chargeperiodstart',
            'charge_period_end': 'chargeperiodend',
            'billed_cost': 'billedcost',
            'service_name': 'servicename',
            'region_name': 'regionname',
            'subaccount_name': 'subaccountname',
            'availability_zone': 'availabilityzone',
        }
        
        for old_col, new_col in column_mappings.items():
            # Use word boundaries to avoid partial matches
            sql = re.sub(r'\b' + old_col + r'\b', new_col, sql, flags=re.IGNORECASE)
        
        # Fix date comparison - ensure column names are wrapped in date()
        # columnname >= date('now', '-X days') becomes date(columnname) >= date('now', '-X days')
        date_columns = ['billingperiodstart', 'billingperiodend', 'chargeperiodstart', 'chargeperiodend']
        for col in date_columns:
            # If column is used in comparison without date() wrapper, add it
            sql = re.sub(
                r'\b(' + col + r')\s*(>=|<=|>|<|=)\s*date\(',
                r'date(\1) \2 date(',
                sql,
                flags=re.IGNORECASE
            )
        
        return sql
    
    def _fix_union_syntax(self, sql: str) -> str:
        """
        Fix UNION queries for SQLite compatibility:
        1. Remove parentheses around SELECT statements
        2. Move ORDER BY and LIMIT to the end of the entire UNION query
        """
        # First, check if it's a UNION query
        if 'UNION' not in sql.upper():
            return sql
        
        # Extract ORDER BY and LIMIT clauses from individual SELECT statements
        order_by_clauses = []
        limit_clauses = []
        
        # Pattern to find ORDER BY before UNION
        order_by_pattern = r'ORDER\s+BY\s+[^\n]+\s+(?:LIMIT\s+\d+\s+)?(?=UNION)'
        matches = list(re.finditer(order_by_pattern, sql, flags=re.IGNORECASE))
        
        for match in matches:
            clause = match.group(0).strip()
            # Extract just ORDER BY part (without LIMIT if present)
            if 'LIMIT' in clause.upper():
                order_part = re.search(r'ORDER\s+BY\s+[^L]+', clause, flags=re.IGNORECASE)
                limit_part = re.search(r'LIMIT\s+\d+', clause, flags=re.IGNORECASE)
                if order_part:
                    order_by_clauses.append(order_part.group(0).strip())
                if limit_part:
                    limit_clauses.append(limit_part.group(0).strip())
            else:
                order_by_clauses.append(clause.strip())
        
        # Remove ORDER BY and LIMIT from individual SELECT statements before UNION
        sql = re.sub(r'ORDER\s+BY\s+[^\n]+\s+LIMIT\s+\d+\s+(?=UNION)', '\n', sql, flags=re.IGNORECASE)
        sql = re.sub(r'ORDER\s+BY\s+[^\n]+\s+(?=UNION)', '\n', sql, flags=re.IGNORECASE)
        sql = re.sub(r'LIMIT\s+\d+\s+(?=UNION)', '\n', sql, flags=re.IGNORECASE)
        
        # Remove parentheses around SELECT statements - preserve newlines
        sql = re.sub(r'\(\s*\n?\s*SELECT', '\nSELECT', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\)\s*\n?\s*UNION', '\nUNION', sql, flags=re.IGNORECASE)
        
        # Check if there's already an ORDER BY at the end
        has_final_order = bool(re.search(r'UNION\s+ALL.*?ORDER\s+BY', sql, flags=re.IGNORECASE | re.DOTALL))
        
        # If we extracted ORDER BY clauses and there's none at the end, add the first one
        if order_by_clauses and not has_final_order:
            # Use the first ORDER BY found (they should be the same for symmetric queries)
            final_order = order_by_clauses[0]
            
            # Check if there's already a LIMIT at the end
            has_final_limit = bool(re.search(r'LIMIT\s+\d+\s*;?\s*$', sql, flags=re.IGNORECASE))
            
            # Add ORDER BY at the end
            sql = sql.rstrip().rstrip(';')
            sql = f"{sql}\n{final_order}"
            
            # Add LIMIT if found and not already at end
            if limit_clauses and not has_final_limit:
                sql = f"{sql}\n{limit_clauses[0]}"
        
        # Remove closing parenthesis before ORDER BY (at the end)
        sql = re.sub(r'\)\s*\n?\s*ORDER\s+BY', '\nORDER BY', sql, flags=re.IGNORECASE)
        
        # Remove any trailing closing parenthesis at the end
        sql = re.sub(r'\)\s*;?\s*$', '', sql)
        
        return sql
    
    def _normalize_region_filter(self, sql: str) -> str:
        """Convert AWS region codes to human-readable names in WHERE clauses"""
        # Map common AWS region codes to database region names
        region_mappings = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'EU (Ireland)',
            'eu-central-1': 'EU (Frankfurt)',
            'eu-west-2': 'EU (London)',
            'eu-west-3': 'EU (Paris)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-southeast-2': 'Asia Pacific (Sydney)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
            'ap-northeast-2': 'Asia Pacific (Seoul)',
            'ap-south-1': 'Asia Pacific (Mumbai)',
            'sa-east-1': 'South America (Sao Paulo)',
            'ca-central-1': 'Canada (Central)',
        }
        
        # Replace region code filters with LIKE patterns
        for code, name in region_mappings.items():
            # Match patterns like: regionname = 'us-east-1'
            sql = re.sub(
                rf"regionname\s*=\s*['\"]({code})['\"]",
                f"regionname LIKE '%{name.split('(')[0].strip()}%'",
                sql,
                flags=re.IGNORECASE
            )
        
        return sql
    
    def _normalize_resourcetype_filter(self, sql: str) -> str:
        """
        Convert common user resource type terms to actual database values.
        
        Database contains:
        - AWS: 'instance' (EC2), 'bucket' (S3), 'volume' (EBS), 'distribution' (CloudFront), '' (empty for many)
        - Azure: 'Virtual machine', 'Storage account', 'Disk', 'Key vault', 'App Service web app', etc.
        
        Users commonly say: 'EC2', 'VM', 'S3', 'blob storage', etc.
        """
        
        # Map user-friendly terms to actual database RESOURCETYPE values
        # Format: {pattern_to_match: (aws_value, azure_value)}
        resource_mappings = {
            # EC2 / Virtual Machines
            'EC2': ('instance', 'Virtual machine'),
            'ec2': ('instance', 'Virtual machine'),
            'virtual machine': ('instance', 'Virtual machine'),
            'VM': ('instance', 'Virtual machine'),
            'vm': ('instance', 'Virtual machine'),
            'compute instance': ('instance', 'Virtual machine'),
            'instance': ('instance', 'Virtual machine'),
            
            # Storage
            'S3': ('bucket', 'Storage account'),
            's3': ('bucket', 'Storage account'),
            'bucket': ('bucket', 'Storage account'),
            'storage': ('bucket', 'Storage account'),
            'blob': ('bucket', 'Storage account'),
            'blob storage': ('bucket', 'Storage account'),
            
            # Disks / Volumes
            'EBS': ('volume', 'Disk'),
            'ebs': ('volume', 'Disk'),
            'volume': ('volume', 'Disk'),
            'disk': ('volume', 'Disk'),
            
            # CDN
            'CloudFront': ('distribution', None),
            'cloudfront': ('distribution', None),
            'CDN': ('distribution', None),
            'cdn': ('distribution', None),
            
            # Azure specific
            'key vault': (None, 'Key vault'),
            'keyvault': (None, 'Key vault'),
            'app service': (None, 'App Service web app'),
            'web app': (None, 'App Service web app'),
        }
        
        # Check which table(s) the query references
        is_aws = 'aws_cost_usage' in sql.lower()
        is_azure = 'azure_cost_usage' in sql.lower()
        
        for user_term, (aws_value, azure_value) in resource_mappings.items():
            # Pattern 1: RESOURCETYPE = 'user_term'
            # Pattern 2: resourcetype = "user_term"
            # Case insensitive matching
            
            # For AWS table
            if is_aws and aws_value:
                # Find and replace in WHERE clauses for aws_cost_usage table
                # Match: resourcetype = 'EC2' or RESOURCETYPE = "VM" etc.
                pattern = rf"(FROM\s+aws_cost_usage[^F]*WHERE[^F]*?)RESOURCETYPE\s*=\s*['\"]({re.escape(user_term)})['\"]"
                replacement = rf"\1RESOURCETYPE = '{aws_value}'"
                sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
                
                # Also handle AND clauses
                pattern = rf"(FROM\s+aws_cost_usage[^F]*?)\s+AND\s+RESOURCETYPE\s*=\s*['\"]({re.escape(user_term)})['\"]"
                replacement = rf"\1 AND RESOURCETYPE = '{aws_value}'"
                sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
            
            # For Azure table
            if is_azure and azure_value:
                # Find and replace in WHERE clauses for azure_cost_usage table
                pattern = rf"(FROM\s+azure_cost_usage[^F]*WHERE[^F]*?)RESOURCETYPE\s*=\s*['\"]({re.escape(user_term)})['\"]"
                replacement = rf"\1RESOURCETYPE = '{azure_value}'"
                sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
                
                # Also handle AND clauses
                pattern = rf"(FROM\s+azure_cost_usage[^F]*?)\s+AND\s+RESOURCETYPE\s*=\s*['\"]({re.escape(user_term)})['\"]"
                replacement = rf"\1 AND RESOURCETYPE = '{azure_value}'"
                sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
        
        return sql
    
    def _get_schema_context(self) -> str:
        """Get formatted schema information for LLM context"""
        context = ""
        
        for table_name in ["aws_cost_usage", "azure_cost_usage"]:
            context += f"\nTable: {table_name}\n"
            context += f"Description: {self.metadata_manager.metadata[table_name]['description']}\n"
            context += "Columns:\n"
            
            for col_name, col_meta in self.metadata_manager.metadata[table_name]["columns"].items():
                context += f"  - {col_name} ({col_meta['data_type']}): {col_meta['description']}\n"
                if "aliases" in col_meta:
                    context += f"    Aliases: {', '.join(col_meta['aliases'][:3])}\n"
        
        return context
    
    def _get_metadata_summary(self) -> str:
        """Get concise metadata summary for intent analysis"""
        summary = "Available Tables and Columns:\n\n"
        
        for table_name in ["aws_cost_usage", "azure_cost_usage"]:
            summary += f"{table_name}:\n"
            columns = list(self.metadata_manager.metadata[table_name]["columns"].keys())
            summary += f"  Columns: {', '.join(columns[:15])}\n"
        
        return summary
    
    def get_semantic_metadata(self) -> Dict:
        """Get the semantic metadata layer for display"""
        return self.metadata_manager.metadata
    
    def check_clarification_needed(self, natural_query: str) -> Dict:
        """
        Check if query needs clarification before execution
        Returns: Dict with needs_clarification, question, options
        """
        return self.clarifier.analyze_query(natural_query)
    
    def apply_clarification(self, natural_query: str, context_key: str, context_value: str) -> str:
        """Apply clarification context to enhance the query"""
        return self.clarifier.apply_context(natural_query, context_key, context_value)
    
    def _validate_and_fix_sql(self, sql: str) -> str:
        """
        Comprehensive SQL validation and automatic fixing.
        Catches common issues before execution.
        """
        # 1. Fix UNION syntax issues
        if 'UNION' in sql.upper():
            sql = self._fix_union_syntax(sql)
            
            # Additional UNION validation
            if 'UNION' in sql.upper():
                # Check for ORDER BY before UNION (common error)
                if re.search(r'ORDER\s+BY[^U]*UNION', sql, flags=re.IGNORECASE | re.DOTALL):
                    # Still has ORDER BY before UNION, fix more aggressively
                    parts = re.split(r'\bUNION\s+ALL\b', sql, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        # Remove ORDER BY and LIMIT from all parts except the last
                        for i in range(len(parts) - 1):
                            parts[i] = re.sub(r'\s*ORDER\s+BY\s+[^\n]+', '', parts[i], flags=re.IGNORECASE)
                            parts[i] = re.sub(r'\s*LIMIT\s+\d+', '', parts[i], flags=re.IGNORECASE)
                        sql = '\nUNION ALL\n'.join(parts)
        
        # 2. Fix common SQLite syntax issues
        sql = self._convert_to_sqlite_syntax(sql)
        
        # 3. Normalize region filters
        sql = self._normalize_region_filter(sql)
        
        # 4. Normalize resource type filters
        sql = self._normalize_resourcetype_filter(sql)
        
        # 5. Remove extra semicolons and whitespace
        sql = sql.strip().rstrip(';').strip()
        
        # 5. Validate basic SQL structure
        sql_upper = sql.upper()
        if 'SELECT' not in sql_upper:
            raise ValueError("Invalid SQL: No SELECT statement found")
        
        # 6. Check for balanced parentheses
        if sql.count('(') != sql.count(')'):
            # Try to fix by removing trailing parentheses
            while sql.endswith(')') and sql.count('(') < sql.count(')'):
                sql = sql[:-1].strip()
        
        # 7. Fix GROUP BY issues - columns in GROUP BY must be in SELECT
        if 'GROUP BY' in sql_upper:
            # Extract GROUP BY columns
            group_by_match = re.search(r'GROUP\s+BY\s+([^\n]+?)(?:ORDER|LIMIT|UNION|$)', sql, flags=re.IGNORECASE)
            if group_by_match:
                group_by_cols = [col.strip() for col in group_by_match.group(1).split(',')]
                
                # Extract SELECT columns
                select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql, flags=re.IGNORECASE | re.DOTALL)
                if select_match:
                    select_clause = select_match.group(1)
                    
                    # Check if all GROUP BY columns are in SELECT
                    for col in group_by_cols:
                        col_name = col.split()[0]  # Get just the column name without alias
                        if col_name not in select_clause and col_name.lower() not in ['regionname', 'servicename', 'resourcetype']:
                            continue
                        
                        # If column is missing from SELECT, add it
                        if col_name not in select_clause:
                            # Add the column to SELECT
                            sql = sql.replace('SELECT ', f'SELECT {col_name}, ', 1)
        
        return sql
    
    def convert_to_sql(self, natural_query: str):
        """
        Convert natural language query to SQL
        Returns: (sql_query, method_used)
        """
        # Try Ollama-based conversion first if available
        if self.use_llm and self.client:
            sql_query = self.convert_with_llm(natural_query)
            if sql_query:
                # Validate and fix before returning
                sql_query = self._validate_and_fix_sql(sql_query)
                return sql_query, "Ollama"
        
        # Fallback to rule-based conversion using LLM-based intent
        intent = self.analyze_intent_with_llm(natural_query)
        sql_query = self.build_sql_from_intent(intent, natural_query)
        # Validate and fix before returning
        sql_query = self._validate_and_fix_sql(sql_query)
        return sql_query, "Rule-based (LLM intent)"
    
    def _detect_and_fix_date_issues(self, sql_query: str) -> tuple[str, str]:
        """
        Detect if date filters will fail due to malformed data and provide workaround
        Returns: (modified_sql, warning_message)
        """
        # Check if query has date filters - be more specific
        if not ('date(' in sql_query.lower() and 'billingperiodstart' in sql_query.lower()):
            return sql_query, None
        
        # Also check for BETWEEN with billingperiodstart
        if not (('between' in sql_query.lower() and 'billingperiodstart' in sql_query.lower()) or 
                ('date(' in sql_query.lower() and 'billingperiodstart' in sql_query.lower())):
            return sql_query, None
        
        # Test if dates are valid by checking a sample
        try:
            test_query = "SELECT billingperiodstart FROM aws_cost_usage WHERE billingperiodstart IS NOT NULL LIMIT 1"
            from database_manager import DatabaseManager
            db = DatabaseManager()
            db.connect()
            result = db.execute_query(test_query)
            
            if result is not None and len(result) > 0:
                date_value = str(result.iloc[0, 0])
                # Check if it's a malformed date (like "00:00.0")
                if date_value == '00:00.0' or not any(char.isdigit() and int(char) > 0 for char in date_value[:4]):
                    # Dates are malformed - remove date filter
                    warning = "⚠️ Note: Date filter removed because the database contains malformed dates. Showing all available data instead."
                    
                    import re
                    sql_modified = sql_query
                    
                    # Pattern 1: Remove BETWEEN date(...) AND date(...)
                    sql_modified = re.sub(
                        r"WHERE\s+billingperiodstart\s+BETWEEN\s+date\([^)]+\)\s+AND\s+date\([^)]+\)\s*",
                        "",
                        sql_modified,
                        flags=re.IGNORECASE
                    )
                    
                    # Pattern 2: Remove WHERE date(billingperiodstart) >= date(...)
                    sql_modified = re.sub(
                        r"WHERE\s+date\([^)]+\)\s*>=\s*date\([^)]+\)\s*",
                        "",
                        sql_modified,
                        flags=re.IGNORECASE
                    )
                    
                    # Pattern 3: Remove WHERE date(billingperiodstart) BETWEEN ...
                    sql_modified = re.sub(
                        r"WHERE\s+date\([^)]+\)\s+BETWEEN[^G]+GROUP",
                        "GROUP",
                        sql_modified,
                        flags=re.IGNORECASE
                    )
                    
                    # Pattern 4: Remove AND clauses with date filters
                    sql_modified = re.sub(
                        r"AND\s+billingperiodstart\s+BETWEEN\s+date\([^)]+\)\s+AND\s+date\([^)]+\)\s*",
                        "",
                        sql_modified,
                        flags=re.IGNORECASE
                    )
                    
                    sql_modified = re.sub(
                        r"AND\s+date\([^)]+\)\s*>=\s*date\([^)]+\)\s*",
                        "",
                        sql_modified,
                        flags=re.IGNORECASE
                    )
                    
                    # Clean up extra whitespace and format nicely
                    sql_modified = re.sub(r'\s+', ' ', sql_modified).strip()
                    sql_modified = re.sub(r'\s+GROUP', '\n  GROUP', sql_modified)
                    sql_modified = re.sub(r'\s+FROM', '\n  FROM', sql_modified)
                    sql_modified = re.sub(r'\s+UNION', '\n\nUNION', sql_modified)
                    sql_modified = re.sub(r'\s+ORDER', '\n  ORDER', sql_modified)
                    sql_modified = re.sub(r'\s+LIMIT', '\n  LIMIT', sql_modified)
                    sql_modified = re.sub(r'SELECT', '\nSELECT', sql_modified).strip()
                    
                    return sql_modified.strip(), warning
                    
            db.close()
        except Exception:
            pass
        
        return sql_query, None
    
    def execute_natural_query(self, natural_query: str):
        """
        Execute natural language query and return results
        Returns: Dict with sql, results, and metadata
        """
        # Convert to SQL
        sql_query, method = self.convert_to_sql(natural_query)
        
        # Detect which table(s) are used in the query
        used_tables = []
        if 'aws_cost_usage' in sql_query.lower():
            used_tables.append('aws_cost_usage')
        if 'azure_cost_usage' in sql_query.lower():
            used_tables.append('azure_cost_usage')
        
        # Get only the relevant metadata for tables used in this query
        query_metadata = {}
        for table in used_tables:
            if table in self.metadata_manager.metadata:
                query_metadata[table] = self.metadata_manager.metadata[table]
        
        # Check and fix date filter issues
        sql_query, date_warning = self._detect_and_fix_date_issues(sql_query)
        
        # Execute query
        results = self.db.execute_query(sql_query)
        
        return {
            "natural_query": natural_query,
            "sql_query": sql_query,
            "method": method,
            "results": results,
            "row_count": len(results) if results is not None else 0,
            "warning": date_warning,
            "used_tables": used_tables,
            "query_metadata": query_metadata
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
