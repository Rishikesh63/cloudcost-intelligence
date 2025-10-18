# CloudCost Intelligence ☁️

A Text-to-SQL engine that converts natural language questions into SQL queries to analyze cloud cost data from AWS and Azure.

## ✨ Features

- 🗣️ **Natural Language Processing** - Ask questions in plain English
- 🤖 **FREE Local LLM** - Uses Ollama (no API keys, 100% private)
- 🤝 **Agentic Clarification** - Smart detection of ambiguous queries with follow-up questions
- 📊 **Interactive Dashboard** - Built with Streamlit
- 🌐 **RESTful API** - FastAPI endpoint for programmatic access
- 📈 **Auto Visualizations** - Charts and graphs generated automatically  
- ☁️ **Multi-Cloud Support** - Analyze AWS and Azure costs together
- 📜 **Query History** - Track and reuse previous queries
- 🔌 **Multiple Interfaces** - Web UI, REST API, and CLI

## 📋 Prerequisites

- **Python 3.11+**
- **Poetry** (dependency management)
- **Ollama** (optional - for AI-powered queries)

## 🚀 Quick Start

### 1. Install Poetry

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### 2. Clone & Setup

```powershell
# Clone the repository
git clone <your-repo-url>
cd CloudCost-Intelligence

# Install dependencies
poetry install

# Initialize database with sample data
poetry run python database_manager.py
```

### 3. (Optional) Install Ollama

```powershell
# Download from: https://ollama.ai/download
# Then pull the model:
ollama pull llama3.2
```

### 4. Run the Application

Choose one of the three interfaces:

#### Option A: Web UI (Streamlit) - **Recommended for Interactive Use**

**Method 1: Direct Poetry command**
```powershell
poetry run streamlit run app.py
```

**Method 2: Activate environment first** *(Recommended)*
```powershell
# Step 1: Activate
.\activate.ps1

# Step 2: Run normally
streamlit run app.py
```

The app will open at `http://localhost:8501`

#### Option B: REST API (FastAPI) - **For Programmatic Access**

```powershell
# Activate environment first
.\activate.ps1

# Run FastAPI server
python api.py
```

The API will be available at:
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)
- **API Endpoint**: `http://localhost:8000`

**Example API Usage:**
```powershell
# Test the API with curl
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{\"question\": \"What is the total AWS cost?\", \"explain\": true}'

# Get database statistics
curl http://localhost:8000/stats

# Get example queries
curl http://localhost:8000/examples
```

#### Option C: Command-Line Interface (CLI)

```powershell
# Activate environment first
.\activate.ps1

# Interactive mode
python cli.py

# Single query
What is the total cost?
```

## 💡 Example Queries

Try asking:
- "What is the total AWS cost?"
- "Show me top 10 services by cost"
- "What are the costs by region?"
- "Show me Azure costs by service"
- "What is the average cost per service?"
- "Show me the top 5 most expensive regions"

## 🤝 Agentic Clarification (Smart Query Assistant)

The **Agentic Clarification** feature intelligently detects ambiguous queries and asks follow-up questions to gather missing context before execution. This ensures you get exactly the data you need without having to reformulate your questions.

### 🎯 What It Detects

The system automatically identifies these types of ambiguities:

1. **Missing Time Range** 📅
   - Query: *"What is the total cost?"*
   - Clarifies: Which time period? (Last 7 days, last month, YTD, etc.)

2. **Missing Cloud Provider** ☁️
   - Query: *"Show me EC2 costs"*
   - Clarifies: AWS only, Azure only, or both?

3. **Ambiguous Cost Metric** 💰
   - Query: *"Show me the cost"*
   - Clarifies: Billed cost (invoice) or effective cost (with discounts)?

4. **Missing Limit in Top-N Queries** 🔢
   - Query: *"Show me top services"*
   - Clarifies: Top 5, 10, 20, or 50?

5. **Missing Region Specification** 🌍
   - Query: *"What are the regional costs?"*
   - Clarifies: All regions or a specific region?

### 🚀 How to Use

#### Standalone Testing

```powershell
# Activate environment
.\activate.ps1

# Run the clarification demo
python agentic_clarification.py
```

This will show test cases demonstrating how the clarifier works:

```
📝 Query: Show me EC2 cost
❓ Which time range would you like me to use?
   Options:
   - Last 7 days (last_7_days)
   - Last 30 days (last_30_days)
   - This month (this_month)
   - Year to date (year_to_date)
   Missing: time_range
✅ Enhanced: Show me EC2 cost in the last 7 days
```

#### Programmatic Usage

```python
from agentic_clarification import AgenticClarifier

# Initialize clarifier
clarifier = AgenticClarifier()

# Analyze a query
result = clarifier.analyze_query("What is the total cost?")

if result["needs_clarification"]:
    # Display question to user
    print(result["question"])
    
    # Show options
    for option in result["options"]:
        print(f"- {option['label']}")
    
    # User selects an option (e.g., "last_30_days")
    selected_value = "last_30_days"
    
    # Apply context to enhance query
    enhanced_query = clarifier.apply_context(
        original_query="What is the total cost?",
        context_key=result["missing_context"][0],
        context_value=selected_value
    )
    
    print(f"Enhanced query: {enhanced_query}")
    # Output: "What is the total cost? in the last 30 days"
```

#### Integration with Existing Interfaces

The clarification system can be integrated into:

**Web UI (Streamlit):**
```python
# Before executing query
clarifier = AgenticClarifier()
result = clarifier.analyze_query(user_query)

if result["needs_clarification"]:
    # Show selectbox with options
    selected = st.selectbox(result["question"], 
                           [opt["label"] for opt in result["options"]])
    
    # Find selected value
    selected_value = next(opt["value"] for opt in result["options"] 
                         if opt["label"] == selected)
    
    # Enhance query
    user_query = clarifier.apply_context(user_query, 
                                         result["missing_context"][0],
                                         selected_value)
```

**REST API (FastAPI):**
```python
@app.post("/query/clarify")
async def clarify_query(question: str):
    clarifier = AgenticClarifier()
    result = clarifier.analyze_query(question)
    return result

@app.post("/query/apply-context")
async def apply_context(query: str, context_key: str, context_value: str):
    clarifier = AgenticClarifier()
    enhanced = clarifier.apply_context(query, context_key, context_value)
    return {"enhanced_query": enhanced}
```

**CLI:**
```python
result = clarifier.analyze_query(user_input)
if result["needs_clarification"]:
    print(f"\n{result['question']}")
    for i, opt in enumerate(result["options"], 1):
        print(f"{i}. {opt['label']}")
    choice = int(input("Select option: ")) - 1
    user_input = clarifier.apply_context(user_input, 
                                         result["missing_context"][0],
                                         result["options"][choice]["value"])
```

### 📊 Example Scenarios

| Ambiguous Query | Clarification Question | Options |
|----------------|----------------------|---------|
| "Show me EC2 cost" | Which time range would you like me to use? | Last 7 days, Last 30 days, This month, YTD, etc. |
| "Show me the cost" | Which cost metric would you like to use? | Billed Cost, Effective Cost |
| "Show me top services" | How many results would you like to see? | Top 5, Top 10, Top 20, Top 50 |
| "What are regional costs?" | Which region would you like to analyze? | All regions, us-east-1, eu-west-1, etc. |
| "Show me S3 costs" | Which cloud provider would you like to analyze? | AWS, Azure, Both |

### 🧠 Smart Features

**Context Application:** The clarifier doesn't just ask questions—it intelligently applies your selections:
- Time ranges → Added as temporal constraints
- Providers → Added as table filters
- Limits → Inserted into TOP-N clauses
- Metrics → Replaces generic "cost" with specific column

**Query Enhancement:**
```
Original:  "Show me top services"
Enhanced:  "Show me top 10 services in the last 30 days for AWS"
```

### 🎓 Benefits

- ✅ **Reduces Errors** - Catches missing context before execution
- ✅ **Saves Time** - No need to reformulate queries manually
- ✅ **Better Results** - Ensures you get exactly what you're looking for
- ✅ **User-Friendly** - Guides users with helpful options
- ✅ **Flexible** - Works with any interface (Web, API, CLI)

## �️ JSON Query Helpers (Tag-Based Queries)

The system includes powerful **JSON extraction utilities** for querying tags and cost categories within your cloud billing data.

### 📦 What It Does

Cloud cost data often includes JSON columns like:
- **`tags`**: `{"Environment": "Production", "Team": "Engineering", "Project": "CloudMigration"}`
- **`cost_categories`**: `{"CostCenter": "IT", "Department": "R&D"}`

Standard SQL makes this hard to query. Our JSON helpers make it easy!

### 🚀 Usage

```python
from database_manager import DatabaseManager
from json_query_helpers import JSONQueryHelper

# Initialize
db = DatabaseManager()
db.connect()
helper = JSONQueryHelper(db)

# Example 1: Get costs by Environment tag
df = helper.extract_json_field('aws_cost_usage', 'tags', 'Environment')
# Returns: Production: $15,234 | Development: $8,765

# Example 2: Query specific tag value
df = helper.query_by_tag('aws_cost_usage', 'Environment', 'Production')
# Returns: Breakdown by service/region for Production only

# Example 3: Discover available tags
tags = helper.get_available_json_keys('aws_cost_usage', 'tags')
# Returns: {'Environment', 'Team', 'Project', 'Owner'}

# Example 4: Natural language detection
result = helper.detect_tag_query("Show me costs by environment tag")
# Returns: {'is_tag_query': True, 'tag_key': 'Environment'}
```

### 📊 Supported Queries

| Query Type | Example | Result |
|------------|---------|--------|
| **By Tag** | "Show cost by environment tag" | Costs grouped by Environment values |
| **Specific Value** | "Show production environment costs" | Only Production tagged resources |
| **By Cost Category** | "Show costs by cost center" | Grouped by CostCenter category |
| **Service Breakdown** | "EC2 costs by team tag" | EC2 costs split by Team |

### 🛠️ Available Methods

- `extract_json_field()` - Extract and aggregate by JSON key
- `query_by_tag()` - Filter and group by tag values
- `query_by_cost_category()` - Filter by cost category
- `get_available_json_keys()` - Discover available JSON keys
- `generate_tag_query_sql()` - Generate SQL for tag queries
- `detect_tag_query()` - Detect tag queries from natural language

### ✨ Integration with Text2SQL

The JSON helpers automatically integrate with the Text2SQL engine:

```
User: "Show me costs by environment tag"
      ↓
Text2SQL detects tag query
      ↓
Uses JSONQueryHelper.generate_tag_query_sql()
      ↓
Executes: SELECT json_extract(tags, '$.Environment'), SUM(billed_cost)...
      ↓
Returns: Nice formatted results by Environment
```

## �🎯 How It Works

1. **You ask a question** in natural language
2. **Engine analyzes** your intent and requirements
3. **SQL is generated** automatically (with Ollama or rule-based)
4. **Results displayed** in tables and charts

## 🌐 API Endpoints (FastAPI)

### POST `/query`
Execute a natural language query

**Request:**
```json
{
  "question": "What is the total AWS cost?",
  "explain": true
}
```

**Response:**
```json
{
  "natural_query": "What is the total AWS cost?",
  "sql_query": "SELECT SUM(billedcost) as total_cost FROM aws_cost",
  "method": "Ollama",
  "row_count": 1,
  "results": [{"total_cost": 45678.92}],
  "explanation": "Based on your question 'What is the total AWS cost?', the total comes to $45,678.92."
}
```

### GET `/stats`
Get database statistics for AWS and Azure

**Response:**
```json
{
  "aws": {"records": 1000, "total_cost": 45678.92},
  "azure": {"records": 5000, "total_cost": 125432.18},
  "combined": {"records": 6000, "total_cost": 171111.10}
}
```

### GET `/examples`
Get example queries organized by category

### GET `/`
API health check and endpoint documentation

## 🛠️ Common Poetry Commands

```powershell
poetry install              # Install all dependencies
poetry add package-name     # Add new package
poetry remove package-name  # Remove package
poetry update              # Update all packages
poetry show                # List installed packages
```

## 📁 Project Structure

```
CloudCost-Intelligence/
├── app.py                       # Streamlit web application
├── api.py                       # FastAPI REST API endpoint
├── cli.py                       # Command-line interface
├── agentic_clarification.py     # Smart query clarification agent
├── json_query_helpers.py        # JSON field extraction utilities (tags, cost categories)
├── database_manager.py          # Database operations
├── semantic_metadata.py         # Schema metadata
├── text2sql_engine.py           # Text-to-SQL converter
├── evaluation.md                # Test cases and results
├── METADATA_EXTRACTION.md       # Technical documentation
├── activate.ps1                 # Environment activation script
├── pyproject.toml              # Poetry configuration
├── README.md                   # This file
└── mock_data_sets/
    ├── aws_cost_usage.csv      # Sample AWS data
    └── azure_cost_usage.csv    # Sample Azure data
```

## 🏗️ Architecture

**Core Components:**
- `database_manager.py` - SQLite operations and data loading
- `semantic_metadata.py` - Schema understanding and aliases
- `text2sql_engine.py` - Natural language to SQL conversion
- `agentic_clarification.py` - Smart query ambiguity detection and clarification
- `json_query_helpers.py` - JSON extraction for tags and cost categories

**User Interfaces:**
- `app.py` - Streamlit web interface with visualizations
- `api.py` - FastAPI REST API for programmatic access
- `cli.py` - Command-line interface for terminal use

**Database Schema:**
- `aws_cost` - AWS billing data (billedcost, servicename, regionname, etc.)
- `azure_cost` - Azure billing data (same structure)

**Access Methods:**
- **Web UI (Streamlit)** - Interactive dashboard at `http://localhost:8501`
- **REST API (FastAPI)** - RESTful endpoints at `http://localhost:8000`
- **CLI** - Terminal-based queries

## ⚙️ Configuration

Environment variables (optional):
- `OLLAMA_BASE_URL` - Ollama server (default: `http://localhost:11434/v1`)
- `OLLAMA_MODEL` - Model name (default: `llama3.2`)
- `DATABASE_PATH` - Database location (default: `./cloud_cost.db`)
- `DEBUG` - Debug mode (default: `False`)

## � Troubleshooting

**App doesn't start?**
- Make sure Poetry is installed: `poetry --version`
- Reinstall dependencies: `poetry install`
- Try running: `poetry run streamlit run app.py`

**Database not found?**
- Initialize it: `poetry run python database_manager.py`

**Ollama not working?**
- The app works without Ollama (uses rule-based mode)
- To use Ollama: Install from https://ollama.ai and run `ollama pull llama3.2`

**Virtual environment issues?**
- Don't use `poetry shell`, use `.\activate.ps1` instead
- This ensures the correct Python/packages are used

## 🎯 Tips

**For Web UI (Streamlit):**
- Click "Use Example Query" button to quickly try sample questions
- Results are automatically visualized with charts when appropriate
- Download results as CSV using the download button
- Query history keeps track of your last 10 queries

**For REST API (FastAPI):**
- Visit `/docs` for interactive Swagger documentation
- Set `"explain": true` in requests to get natural language explanations
- Use `/stats` to check database health
- Use `/examples` to discover query patterns

**For CLI:**
- Type `help` to see available commands
- Type `examples` to see sample queries
- Type `stats` to view database statistics
- Press Ctrl+C to exit

## � Documentation

- **README.md** (this file) - Setup and usage guide
- **evaluation.md** - Test cases with real query examples
- **METADATA_EXTRACTION.md** - Technical documentation on metadata extraction methodology
- **ASSIGNMENT_REQUIREMENTS_CHECKLIST.md** - Assignment completion status

## 🎓 Use Cases

**Web UI (Streamlit)** - Best for:
- Interactive data exploration
- Visual analysis with charts
- Non-technical users
- Ad-hoc queries

**REST API (FastAPI)** - Best for:
- Integration with other applications
- Automation and scripting
- Building custom dashboards
- Microservices architecture

**CLI** - Best for:
- Server environments without GUI
- Shell scripting and automation
- Quick one-off queries
- SSH remote access


**Built with:** Python 3.11 | Poetry | Streamlit | FastAPI | Ollama | SQLite | Plotly
