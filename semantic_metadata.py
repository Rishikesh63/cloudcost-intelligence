import json
from typing import Dict, Optional
import sqlite3


class SemanticMetadataManager:
    """Manages semantic metadata for database tables and columns"""
    
    def __init__(self, db_path="cloud_cost.db", auto_extract=False):
        self.db_path = db_path
        if auto_extract:
            # Extract metadata from database schema
            self.metadata = self._extract_metadata_from_db()
            # Enhance with semantic information
            self._enhance_metadata()
        else:
            # Use predefined semantic metadata
            self.metadata = self._initialize_metadata()
    
    def _initialize_metadata(self) -> Dict:
        """Initialize semantic metadata for cloud cost tables"""
        return {
            "aws_cost_usage": {
                "description": "AWS cloud cost and usage data",
                "aliases": ["aws", "amazon web services", "amazon costs", "ec2 costs"],
                "columns": {
                    "billedcost": {
                        "description": "The actual amount billed to the customer",
                        "aliases": ["cost", "bill", "charge", "amount", "price", "spend", "expense"],
                        "data_type": "REAL",
                        "aggregations": ["SUM", "AVG", "MIN", "MAX", "COUNT"],
                        "examples": ["total cost", "average cost", "cost breakdown"]
                    },
                    "effective_cost": {
                        "description": "Cost after applying discounts and credits",
                        "aliases": ["net cost", "actual cost", "final cost"],
                        "data_type": "REAL",
                        "aggregations": ["SUM", "AVG", "MIN", "MAX"]
                    },
                    "servicename": {
                        "description": "Name of the AWS service used",
                        "aliases": ["service", "product", "aws service"],
                        "data_type": "TEXT",
                        "examples": ["EC2", "S3", "RDS", "Lambda", "Elastic Compute Cloud"]
                    },
                    "service_category": {
                        "description": "Category of the service",
                        "aliases": ["category", "service type"],
                        "data_type": "TEXT",
                        "examples": ["Compute", "Storage", "Database", "Networking"]
                    },
                    "regionname": {
                        "description": "AWS region where resources are deployed",
                        "aliases": ["region", "location", "geography", "area"],
                        "data_type": "TEXT",
                        "examples": ["us-east-1", "Asia Pacific (Sydney)", "EU (Ireland)"]
                    },
                    "resourcetype": {
                        "description": "Type of cloud resource",
                        "aliases": ["resource", "instance type"],
                        "data_type": "TEXT"
                    },
                    "billing_period_start": {
                        "description": "Start date of the billing period",
                        "aliases": ["start date", "period start", "from date", "beginning"],
                        "data_type": "TEXT",
                        "temporal": True
                    },
                    "billing_period_end": {
                        "description": "End date of the billing period",
                        "aliases": ["end date", "period end", "to date", "until"],
                        "data_type": "TEXT",
                        "temporal": True
                    },
                    "tags": {
                        "description": "JSON tags associated with the resource",
                        "aliases": ["labels", "metadata", "tag"],
                        "data_type": "TEXT"
                    },
                    "consumed_quantity": {
                        "description": "Amount of service consumed",
                        "aliases": ["quantity", "usage", "volume", "amount used"],
                        "data_type": "REAL",
                        "aggregations": ["SUM", "AVG", "MIN", "MAX"]
                    },
                    "subaccountname": {
                        "description": "Name of the AWS sub-account",
                        "aliases": ["account", "subaccount", "account name"],
                        "data_type": "TEXT"
                    }
                }
            },
            "azure_cost_usage": {
                "description": "Azure cloud cost and usage data",
                "aliases": ["azure", "microsoft azure", "azure costs"],
                "columns": {
                    "billedcost": {
                        "description": "The actual amount billed to the customer",
                        "aliases": ["cost", "bill", "charge", "amount", "price", "spend", "expense"],
                        "data_type": "REAL",
                        "aggregations": ["SUM", "AVG", "MIN", "MAX", "COUNT"]
                    },
                    "effective_cost": {
                        "description": "Cost after applying discounts and credits",
                        "aliases": ["net cost", "actual cost", "final cost"],
                        "data_type": "REAL",
                        "aggregations": ["SUM", "AVG", "MIN", "MAX"]
                    },
                    "servicename": {
                        "description": "Name of the Azure service used",
                        "aliases": ["service", "product", "azure service"],
                        "data_type": "TEXT",
                        "examples": ["Virtual Machines", "Storage Accounts", "Azure SQL"]
                    },
                    "service_category": {
                        "description": "Category of the service",
                        "aliases": ["category", "service type"],
                        "data_type": "TEXT",
                        "examples": ["Compute", "Storage", "Database", "Networking"]
                    },
                    "regionname": {
                        "description": "Azure region where resources are deployed",
                        "aliases": ["region", "location", "geography", "area"],
                        "data_type": "TEXT",
                        "examples": ["Australia East", "Australia Southeast", "US East"]
                    },
                    "resourcetype": {
                        "description": "Type of Azure resource",
                        "aliases": ["resource", "instance type"],
                        "data_type": "TEXT"
                    },
                    "billing_period_start": {
                        "description": "Start date of the billing period",
                        "aliases": ["start date", "period start", "from date"],
                        "data_type": "TEXT",
                        "temporal": True
                    },
                    "billing_period_end": {
                        "description": "End date of the billing period",
                        "aliases": ["end date", "period end", "to date"],
                        "data_type": "TEXT",
                        "temporal": True
                    },
                    "tags": {
                        "description": "JSON tags associated with the resource",
                        "aliases": ["labels", "metadata", "tag"],
                        "data_type": "TEXT"
                    },
                    "consumed_quantity": {
                        "description": "Amount of service consumed",
                        "aliases": ["quantity", "usage", "volume"],
                        "data_type": "REAL",
                        "aggregations": ["SUM", "AVG", "MIN", "MAX"]
                    },
                    "subaccountname": {
                        "description": "Name of the Azure subscription",
                        "aliases": ["subscription", "account", "account name"],
                        "data_type": "TEXT"
                    }
                }
            }
        }
    
    def get_table_from_intent(self, text: str) -> Optional[str]:
        """Determine which table to query based on user intent"""
        text_lower = text.lower()
        
        # Check for specific provider mentions
        if any(alias in text_lower for alias in self.metadata["aws_cost_usage"]["aliases"]):
            return "aws_cost_usage"
        elif any(alias in text_lower for alias in self.metadata["azure_cost_usage"]["aliases"]):
            return "azure_cost_usage"
        
        # Default to both tables if no specific provider mentioned
        return None
    
    def find_column_match(self, table_name: str, column_reference: str) -> Optional[str]:
        """Find the actual column name from a natural language reference"""
        column_reference_lower = column_reference.lower()
        
        if table_name not in self.metadata:
            return None
        
        columns = self.metadata[table_name]["columns"]
        
        # Direct match
        if column_reference_lower in columns:
            return column_reference_lower
        
        # Check aliases
        for col_name, col_meta in columns.items():
            if "aliases" in col_meta:
                if any(alias in column_reference_lower or column_reference_lower in alias 
                       for alias in col_meta["aliases"]):
                    return col_name
        
        return None
    
    def get_aggregation_function(self, text: str, column_name: str, table_name: str) -> str:
        """Determine the appropriate aggregation function based on intent"""
        text_lower = text.lower()
        
        # Check for explicit aggregation keywords
        if "total" in text_lower or "sum" in text_lower:
            return "SUM"
        elif "average" in text_lower or "avg" in text_lower or "mean" in text_lower:
            return "AVG"
        elif "maximum" in text_lower or "max" in text_lower or "highest" in text_lower:
            return "MAX"
        elif "minimum" in text_lower or "min" in text_lower or "lowest" in text_lower:
            return "MIN"
        elif "count" in text_lower or "number of" in text_lower or "how many" in text_lower:
            return "COUNT"
        
        # Default to SUM for cost columns
        if "cost" in column_name:
            return "SUM"
        
        return "SUM"
    
    def get_column_metadata(self, table_name: str, column_name: str) -> Optional[Dict]:
        """Get metadata for a specific column"""
        if table_name in self.metadata and column_name in self.metadata[table_name]["columns"]:
            return self.metadata[table_name]["columns"][column_name]
        return None
    
    def get_all_tables_info(self) -> Dict:
        """Get information about all tables"""
        return {
            table_name: {
                "description": table_meta["description"],
                "columns": list(table_meta["columns"].keys())
            }
            for table_name, table_meta in self.metadata.items()
        }
    
    def _extract_metadata_from_db(self) -> Dict:
        """
        Automatically extract metadata from database schema
        This demonstrates dynamic metadata extraction capability
        """
        metadata = {}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                if table_name.startswith('sqlite_'):
                    continue
                
                metadata[table_name] = {
                    "description": f"Auto-extracted: {table_name} table",
                    "aliases": [table_name.replace('_', ' ')],
                    "columns": {}
                }
                
                # Get column information
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                for col_id, col_name, col_type, not_null, default_val, is_pk in columns:
                    metadata[table_name]["columns"][col_name] = {
                        "description": f"Auto-extracted: {col_name} field",
                        "data_type": col_type,
                        "nullable": not not_null,
                        "primary_key": bool(is_pk),
                        "aliases": [col_name.replace('_', ' ')]
                    }
                    
                    # Add aggregations for numeric columns
                    if col_type.upper() in ['REAL', 'INTEGER', 'NUMERIC']:
                        metadata[table_name]["columns"][col_name]["aggregations"] = [
                            "SUM", "AVG", "MIN", "MAX", "COUNT"
                        ]
            
            conn.close()
            print(f"✅ Extracted metadata from database: {len(metadata)} tables found")
            return metadata
            
        except Exception as e:
            print(f"⚠️ Error extracting metadata from database: {e}")
            print("Falling back to predefined metadata...")
            return self._initialize_metadata()
    
    def _enhance_metadata(self):
        """
        Enhance auto-extracted metadata with semantic information
        This adds business-friendly aliases and descriptions
        """
        # Semantic enhancements for common cloud cost columns
        enhancements = {
            "billedcost": {
                "aliases": ["cost", "bill", "charge", "amount", "price", "spend", "expense"],
                "description": "The actual amount billed to the customer"
            },
            "billed_cost": {
                "aliases": ["cost", "bill", "charge", "amount", "price", "spend", "expense"],
                "description": "The actual amount billed to the customer"
            },
            "effective_cost": {
                "aliases": ["net cost", "actual cost", "final cost"],
                "description": "Cost after applying discounts and credits"
            },
            "servicename": {
                "aliases": ["service", "product", "service name"],
                "description": "Name of the cloud service used"
            },
            "service_name": {
                "aliases": ["service", "product", "service name"],
                "description": "Name of the cloud service used"
            },
            "regionname": {
                "aliases": ["region", "location", "geography", "area"],
                "description": "Cloud region where resources are deployed"
            },
            "region_name": {
                "aliases": ["region", "location", "geography", "area"],
                "description": "Cloud region where resources are deployed"
            },
            "subaccountname": {
                "aliases": ["account", "subaccount", "subscription"],
                "description": "Name of the account or subscription"
            },
            "consumed_quantity": {
                "aliases": ["quantity", "usage", "volume", "amount used"],
                "description": "Amount of service consumed"
            }
        }
        
        # Apply enhancements to all tables
        for table_name in self.metadata:
            for col_name in self.metadata[table_name]["columns"]:
                col_lower = col_name.lower()
                if col_lower in enhancements:
                    self.metadata[table_name]["columns"][col_name].update(enhancements[col_lower])
        
        print(f"✅ Enhanced metadata with semantic information")
    
    def save_metadata_to_file(self, filepath: str = "semantic_metadata.json"):
        """Save metadata to a JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def load_metadata_from_file(self, filepath: str = "semantic_metadata.json"):
        """Load metadata from a JSON file"""
        with open(filepath, 'r') as f:
            self.metadata = json.load(f)


if __name__ == "__main__":
    print("=" * 70)
    print("Semantic Metadata Manager - Demo")
    print("=" * 70)
    
    # Demo 1: Using predefined metadata (default)
    print("\n1️⃣ Using Predefined Metadata (Hardcoded):")
    print("-" * 70)
    manager = SemanticMetadataManager(auto_extract=False)
    manager.save_metadata_to_file("semantic_metadata_predefined.json")
    print("✅ Saved predefined metadata to semantic_metadata_predefined.json")
    
    # Demo 2: Auto-extract from database
    print("\n2️⃣ Auto-Extracting Metadata from Database:")
    print("-" * 70)
    manager_auto = SemanticMetadataManager(auto_extract=True)
    manager_auto.save_metadata_to_file("semantic_metadata_extracted.json")
    print("✅ Saved extracted metadata to semantic_metadata_extracted.json")
    
    # Test lookups
    print("\n3️⃣ Testing Metadata Lookups:")
    print("-" * 70)
    print("Table from 'AWS costs': ", manager.get_table_from_intent("Show me AWS costs"))
    print("Column match for 'cost': ", manager.find_column_match("aws_cost", "cost"))
    print("Aggregation for 'total cost': ", manager.get_aggregation_function("total cost", "billedcost", "aws_cost"))
    
    print("\n" + "=" * 70)
    print("✅ Demo complete! Check the generated JSON files.")
    print("=" * 70)
