"""
Command-Line Interface for CloudCost Intelligence Text2SQL Engine
Simple CLI for running queries without the web interface
"""

import sys
from text2sql_engine import Text2SQLEngine
from tabulate import tabulate


def print_banner():
    """Print application banner"""
    print("=" * 70)
    print("  ☁️  CloudCost Intelligence - Text2SQL Engine (CLI)")
    print("=" * 70)
    print()


def print_help():
    """Print help information"""
    print("Commands:")
    print("  query <your question>  - Ask a natural language question")
    print("  examples               - Show example queries")
    print("  stats                  - Show database statistics")
    print("  help                   - Show this help message")
    print("  exit                   - Exit the application")
    print()


def print_examples():
    """Print example queries"""
    examples = [
        "What is the total AWS cost?",
        "Show me top 10 services by cost",
        "What are the costs by region?",
        "Show me Azure costs by service",
        "What is the average cost per service?",
        "Show me the top 5 most expensive regions",
        "What is the total cost for compute services?"
    ]
    
    print("\n📝 Example Queries:")
    print("-" * 70)
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example}")
    print("-" * 70)
    print()


def show_stats(engine):
    """Show database statistics"""
    print("\n📊 Database Statistics:")
    print("-" * 70)
    
    # AWS stats
    result = engine.execute_natural_query("SELECT COUNT(*) as count, SUM(billed_cost) as total FROM aws_cost")
    if result['results'] is not None and len(result['results']) > 0:
        row = result['results'].iloc[0]
        print(f"AWS Records: {int(row['count']):,}")
        print(f"AWS Total Cost: ${row['total']:,.2f}")
    
    # Azure stats
    result = engine.execute_natural_query("SELECT COUNT(*) as count, SUM(billed_cost) as total FROM azure_cost")
    if result['results'] is not None and len(result['results']) > 0:
        row = result['results'].iloc[0]
        print(f"Azure Records: {int(row['count']):,}")
        print(f"Azure Total Cost: ${row['total']:,.2f}")
    
    print("-" * 70)
    print()


def format_table(df, max_rows=20):
    """Format DataFrame as table"""
    if df is None or len(df) == 0:
        return "No results found."
    
    # Limit rows
    display_df = df.head(max_rows)
    
    # Format cost columns
    for col in display_df.columns:
        if 'cost' in col.lower() or 'price' in col.lower():
            if display_df[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if not pd.isna(x) else "N/A")
    
    return tabulate(display_df, headers='keys', tablefmt='grid', showindex=False)


def run_query(engine, query_text):
    """Run a natural language query"""
    print(f"\n🔍 Query: {query_text}")
    print("-" * 70)
    
    try:
        result = engine.execute_natural_query(query_text)
        
        print(f"\n🔧 Generated SQL:")
        print(result['sql_query'])
        print(f"\n📊 Method: {result['method']}")
        print(f"📈 Rows: {result['row_count']}")
        
        if result['results'] is not None and len(result['results']) > 0:
            print(f"\n📋 Results:")
            print(format_table(result['results']))
            
            if result['row_count'] > 20:
                print(f"\n(Showing first 20 of {result['row_count']} rows)")
        else:
            print("\n⚠️  No results found.")
        
        print("-" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("-" * 70)


def interactive_mode():
    """Run in interactive mode"""
    print_banner()
    print("Welcome to the CloudCost Intelligence CLI!")
    print("Type 'help' for commands or 'exit' to quit.")
    print()
    
    # Initialize engine
    print("Initializing Text2SQL engine...")
    engine = Text2SQLEngine()
    print("✅ Engine initialized!\n")
    
    try:
        while True:
            try:
                user_input = input(">>> ").strip()
                
                if not user_input:
                    continue
                
                # Parse command
                if user_input.lower() == 'exit':
                    print("\n👋 Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    print_help()
                
                elif user_input.lower() == 'examples':
                    print_examples()
                
                elif user_input.lower() == 'stats':
                    show_stats(engine)
                
                elif user_input.lower().startswith('query '):
                    query_text = user_input[6:].strip()
                    if query_text:
                        run_query(engine, query_text)
                    else:
                        print("Please provide a query after 'query' command")
                
                else:
                    # Treat as direct query
                    run_query(engine, user_input)
            
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break
    
    finally:
        engine.close()


def single_query_mode(query):
    """Run a single query and exit"""
    engine = Text2SQLEngine()
    
    try:
        run_query(engine, query)
    finally:
        engine.close()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Single query mode
        query = ' '.join(sys.argv[1:])
        single_query_mode(query)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    # Check if pandas is available (for tabulate to work)
    try:
        import pandas as pd
    except ImportError:
        print("Error: pandas is required. Install with: pip install pandas")
        sys.exit(1)
    
    main()
