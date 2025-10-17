"""
FastAPI Endpoint for CloudCost Intelligence Text2SQL Engine
RESTful API for natural language querying of cloud cost data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any
import uvicorn
from text2sql_engine import Text2SQLEngine


app = FastAPI(
    title="CloudCost Intelligence API",
    description="Natural language to SQL API for cloud cost analytics",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engine
engine = None


class QueryRequest(BaseModel):
    """Natural language query request"""
    question: str
    explain: Optional[bool] = True


class QueryResponse(BaseModel):
    """Query response with SQL and results"""
    natural_query: str
    sql_query: str
    method: str
    row_count: int
    results: Optional[Any] = None
    explanation: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize Text2SQL engine on startup"""
    global engine
    engine = Text2SQLEngine()
    print("✅ Text2SQL Engine initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    global engine
    if engine:
        engine.close()
    print("👋 Text2SQL Engine closed")


@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "CloudCost Intelligence API",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "POST /query": "Execute natural language query",
            "GET /stats": "Get database statistics",
            "GET /examples": "Get example queries"
        }
    }


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute a natural language query against cloud cost data
    
    Example:
    ```
    POST /query
    {
        "question": "What is the total AWS cost?",
        "explain": true
    }
    ```
    """
    try:
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Execute query
        result = engine.execute_natural_query(request.question)
        
        # Generate natural language explanation if requested
        explanation = None
        if request.explain and result['results'] is not None:
            explanation = generate_explanation(
                request.question,
                result['sql_query'],
                result['results'],
                result['row_count']
            )
        
        # Convert DataFrame to dict for JSON serialization
        results_data = None
        if result['results'] is not None:
            results_data = result['results'].to_dict('records')
        
        return QueryResponse(
            natural_query=result['natural_query'],
            sql_query=result['sql_query'],
            method=result['method'],
            row_count=result['row_count'],
            results=results_data,
            explanation=explanation
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_database_stats():
    """Get database statistics for AWS and Azure costs"""
    try:
        # AWS stats
        aws_result = engine.execute_natural_query("SELECT COUNT(*) as count, SUM(billedcost) as total FROM aws_cost")
        aws_stats = {
            "records": int(aws_result['results'].iloc[0]['count']) if aws_result['results'] is not None else 0,
            "total_cost": float(aws_result['results'].iloc[0]['total']) if aws_result['results'] is not None else 0.0
        }
        
        # Azure stats
        azure_result = engine.execute_natural_query("SELECT COUNT(*) as count, SUM(billedcost) as total FROM azure_cost")
        azure_stats = {
            "records": int(azure_result['results'].iloc[0]['count']) if azure_result['results'] is not None else 0,
            "total_cost": float(azure_result['results'].iloc[0]['total']) if azure_result['results'] is not None else 0.0
        }
        
        return {
            "aws": aws_stats,
            "azure": azure_stats,
            "combined": {
                "records": aws_stats["records"] + azure_stats["records"],
                "total_cost": aws_stats["total_cost"] + azure_stats["total_cost"]
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/examples")
async def get_example_queries():
    """Get example queries to try"""
    return {
        "examples": [
            {
                "category": "Basic Aggregation",
                "queries": [
                    "What is the total AWS cost?",
                    "What is the total Azure cost?",
                    "What is the average cost per service?"
                ]
            },
            {
                "category": "Grouping & Analysis",
                "queries": [
                    "Show me costs by service",
                    "What are the costs by region?",
                    "Show me Azure costs by service category"
                ]
            },
            {
                "category": "Top N Queries",
                "queries": [
                    "Show me top 5 services by cost",
                    "What are the top 10 most expensive regions?",
                    "Show me the top 3 accounts by spend"
                ]
            },
            {
                "category": "Comparative Analysis",
                "queries": [
                    "Compare AWS and Azure costs",
                    "Which provider has higher compute costs?",
                    "Show cost breakdown by provider"
                ]
            }
        ]
    }


def generate_explanation(question: str, sql: str, results, row_count: int) -> str:
    """
    Generate a natural language explanation of query results
    
    This function creates a conversational response explaining what the data shows.
    In a production system, this could use an LLM to generate more sophisticated explanations.
    """
    
    # Simple rule-based explanation generation
    explanation_parts = []
    
    # Start with acknowledgment
    explanation_parts.append(f"Based on your question '{question}',")
    
    # Analyze the query type
    sql_lower = sql.lower()
    
    if "count(*)" in sql_lower or "count(distinct" in sql_lower:
        # Count query
        if row_count > 0:
            count_value = results.iloc[0].iloc[0]
            explanation_parts.append(f"I found {count_value:,} matching records.")
        else:
            explanation_parts.append("I found no matching records.")
    
    elif "sum(" in sql_lower:
        # Aggregation query
        if row_count > 0:
            if "group by" in sql_lower:
                explanation_parts.append(f"I found {row_count} groups with the following breakdown:")
            else:
                total_cost = results.iloc[0].iloc[0]
                explanation_parts.append(f"the total comes to ${total_cost:,.2f}.")
        else:
            explanation_parts.append("no data was found matching your criteria.")
    
    elif "avg(" in sql_lower:
        # Average query
        if row_count > 0:
            avg_value = results.iloc[0].iloc[0]
            explanation_parts.append(f"the average is ${avg_value:,.2f}.")
        else:
            explanation_parts.append("no data was found to calculate an average.")
    
    elif "top" in question.lower() or "limit" in sql_lower:
        # Top N query
        if row_count > 0:
            explanation_parts.append(f"here are the top {row_count} results sorted by cost.")
        else:
            explanation_parts.append("no results were found.")
    
    else:
        # General query
        if row_count > 0:
            explanation_parts.append(f"I found {row_count} matching records.")
        else:
            explanation_parts.append("no records matched your query.")
    
    # Add data quality note if relevant
    if row_count > 100:
        explanation_parts.append(f"Note: Only showing first 100 rows out of {row_count} total.")
    
    return " ".join(explanation_parts)


if __name__ == "__main__":
    print("🚀 Starting CloudCost Intelligence API...")
    print("📝 API Documentation: http://localhost:8000/docs")
    print("🔍 Interactive API: http://localhost:8000/redoc")
    print("\nExample usage:")
    print("  curl -X POST http://localhost:8000/query \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"question": "What is the total AWS cost?"}\'')
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
