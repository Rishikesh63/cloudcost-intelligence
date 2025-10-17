"""
Setup script for CloudCost Intelligence Text2SQL Engine
Initializes the database and loads sample data
"""

import os
import sys


def check_requirements():
    """Check if required packages are installed"""
    required_packages = [
        'pandas',
        'sqlalchemy',
        'python-dotenv',
        'streamlit',
        'plotly',
        'openai'  # Used by Ollama client
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for pkg in missing_packages:
            print(f"   - {pkg}")
        print("\n📦 Install them with: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed!")
    return True


def setup_env_file():
    """Create .env file if it doesn't exist"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            print("📝 Creating .env file from template...")
            with open('.env.example', 'r') as f:
                content = f.read()
            with open('.env', 'w') as f:
                f.write(content)
            print("✅ .env file created!")
            print("ℹ️  Default Ollama settings are ready to use!")
        else:
            print("⚠️  .env.example not found")
    else:
        print("✅ .env file already exists")


def initialize_database():
    """Initialize the database with sample data"""
    print("\n🗄️  Initializing database...")
    
    try:
        from database_manager import initialize_database as init_db
        init_db()
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        return False
    
    return True


def generate_semantic_metadata():
    """Generate semantic metadata file"""
    print("\n📚 Generating semantic metadata...")
    
    try:
        from semantic_metadata import SemanticMetadataManager
        manager = SemanticMetadataManager()
        manager.save_metadata_to_file()
        print("✅ Semantic metadata generated!")
    except Exception as e:
        print(f"❌ Error generating metadata: {str(e)}")
        return False
    
    return True


def test_engine():
    """Test the Text2SQL engine with a simple query"""
    print("\n🧪 Testing Text2SQL engine...")
    
    try:
        from text2sql_engine import Text2SQLEngine
        engine = Text2SQLEngine(use_llm=False)  # Use rule-based for testing
        
        result = engine.execute_natural_query("What is the total cost?")
        
        if result['results'] is not None:
            print("✅ Engine test successful!")
            print(f"   Generated SQL: {result['sql_query']}")
            print(f"   Method: {result['method']}")
            print(f"   Rows returned: {result['row_count']}")
        else:
            print("⚠️  Engine test returned no results")
        
        engine.close()
    except Exception as e:
        print(f"❌ Error testing engine: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def main():
    """Main setup function"""
    print("=" * 60)
    print("   CloudCost Intelligence - Text2SQL Engine Setup")
    print("=" * 60)
    print()
    
    # Step 1: Check requirements
    print("Step 1: Checking requirements...")
    if not check_requirements():
        print("\n❌ Setup failed. Please install required packages first.")
        sys.exit(1)
    
    # Step 2: Setup environment file
    print("\nStep 2: Setting up environment file...")
    setup_env_file()
    
    # Step 3: Initialize database
    print("\nStep 3: Initializing database...")
    if not initialize_database():
        print("\n⚠️  Database initialization failed, but continuing...")
    
    # Step 4: Generate semantic metadata
    print("\nStep 4: Generating semantic metadata...")
    if not generate_semantic_metadata():
        print("\n⚠️  Metadata generation failed, but continuing...")
    
    # Step 5: Test the engine
    print("\nStep 5: Testing the engine...")
    if not test_engine():
        print("\n⚠️  Engine test failed, but setup is complete")
    
    # Final instructions
    print("\n" + "=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print("\n📖 Next Steps:")
    print("   1. Install Ollama from https://ollama.ai")
    print("   2. Pull model: ollama pull llama3.2")
    print("   3. Start Ollama: ollama serve")
    print("   4. Run the app: streamlit run app.py")
    print("   5. Open your browser to http://localhost:8501")
    print("\n💡 Tips:")
    print("   - The app works without Ollama (rule-based mode)")
    print("   - For best results, use Ollama for LLM-powered queries")
    print("   - Check README.md for example queries and documentation")
    print("   - See OLLAMA_SETUP.md for detailed Ollama setup")
    print("\n🚀 Enjoy using CloudCost Intelligence!")
    print()


if __name__ == "__main__":
    main()
