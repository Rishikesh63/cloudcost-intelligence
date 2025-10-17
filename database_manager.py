import sqlite3
import pandas as pd
import os


class DatabaseManager:
    """Manages database operations for cloud cost data"""
    
    def __init__(self, db_path="cloud_cost.db"):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Establish database connection with thread safety for Streamlit"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """Create tables for AWS and Azure cost data"""
        cursor = self.conn.cursor()
        
        # AWS Cost Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aws_cost (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                availability_zone TEXT,
                billed_cost REAL,
                billing_account_id TEXT,
                billing_account_name TEXT,
                billing_currency TEXT,
                billing_period_end TEXT,
                billing_period_start TEXT,
                charge_category TEXT,
                charge_class TEXT,
                charge_description TEXT,
                charge_frequency TEXT,
                charge_period_end TEXT,
                charge_period_start TEXT,
                commitment_discount_category TEXT,
                commitment_discount_id TEXT,
                commitment_discount_name TEXT,
                commitment_discount_status TEXT,
                commitment_discount_type TEXT,
                consumed_quantity REAL,
                consumed_unit TEXT,
                contracted_cost REAL,
                contracted_unit_price REAL,
                effective_cost REAL,
                invoice_issuer_name TEXT,
                list_cost REAL,
                list_unit_price REAL,
                pricing_category TEXT,
                pricing_quantity REAL,
                pricing_unit TEXT,
                provider_name TEXT,
                publisher_name TEXT,
                region_id TEXT,
                region_name TEXT,
                resource_id TEXT,
                resource_name TEXT,
                resource_type TEXT,
                service_category TEXT,
                service_name TEXT,
                sku_id TEXT,
                sku_price_id TEXT,
                subaccount_id TEXT,
                subaccount_name TEXT,
                tags TEXT,
                cost_categories TEXT,
                discounts TEXT,
                operation TEXT,
                service_code TEXT,
                usage_type TEXT
            )
        """)
        
        # Azure Cost Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS azure_cost (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                billed_cost REAL,
                billing_account_id TEXT,
                billing_account_name TEXT,
                billing_account_type TEXT,
                billing_currency TEXT,
                billing_period_end TEXT,
                billing_period_start TEXT,
                charge_category TEXT,
                charge_class TEXT,
                charge_description TEXT,
                charge_frequency TEXT,
                charge_period_end TEXT,
                charge_period_start TEXT,
                commitment_discount_category TEXT,
                commitment_discount_id TEXT,
                commitment_discount_name TEXT,
                commitment_discount_status TEXT,
                commitment_discount_type TEXT,
                consumed_quantity REAL,
                consumed_unit TEXT,
                contracted_cost REAL,
                contracted_unit_price REAL,
                effective_cost REAL,
                invoice_issuer_name TEXT,
                list_cost REAL,
                list_unit_price REAL,
                pricing_category TEXT,
                pricing_quantity REAL,
                pricing_unit TEXT,
                provider_name TEXT,
                publisher_name TEXT,
                region_id TEXT,
                region_name TEXT,
                resource_id TEXT,
                resource_name TEXT,
                resource_type TEXT,
                service_category TEXT,
                service_name TEXT,
                sku_id TEXT,
                sku_price_id TEXT,
                subaccount_id TEXT,
                subaccount_name TEXT,
                subaccount_type TEXT,
                tags TEXT
            )
        """)
        
        self.conn.commit()
    
    def load_csv_data(self, csv_path, table_name):
        """Load CSV data into specified table"""
        df = pd.read_csv(csv_path)
        
        # Normalize column names - just lowercase, no conversion
        # The CSV columns are already in format like BILLEDCOST
        # We'll just make them billedcost to match app expectations
        df.columns = df.columns.str.lower()
        
        # Load data to table
        df.to_sql(table_name, self.conn, if_exists='replace', index=False)
        print(f"Loaded {len(df)} records into {table_name}")
    
    def execute_query(self, query):
        """Execute SQL query and return results as DataFrame"""
        try:
            df = pd.read_sql_query(query, self.conn)
            return df
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            return None
    
    def get_table_schema(self, table_name):
        """Get schema information for a table"""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        schema = cursor.fetchall()
        return schema
    
    def get_sample_data(self, table_name, limit=5):
        """Get sample data from a table"""
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.execute_query(query)


def initialize_database():
    """Initialize database with cost data from CSV files"""
    db = DatabaseManager()
    db.connect()
    
    # Create tables
    db.create_tables()
    
    # Load AWS data
    aws_csv = "mock_data_sets/aws_cost_usage.csv"
    if os.path.exists(aws_csv):
        db.load_csv_data(aws_csv, "aws_cost")
    
    # Load Azure data
    azure_csv = "mock_data_sets/azure_cost_usage.csv"
    if os.path.exists(azure_csv):
        db.load_csv_data(azure_csv, "azure_cost")
    
    db.close()
    print("Database initialized successfully!")


if __name__ == "__main__":
    initialize_database()
