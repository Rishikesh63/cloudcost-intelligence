import streamlit as st
import pandas as pd
from text2sql_engine import Text2SQLEngine
from database_manager import DatabaseManager
import plotly.express as px


# Page configuration
st.set_page_config(
    page_title="CloudCost Intelligence - Text2SQL",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .query-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_engine():
    """Initialize and cache the Text2SQL engine"""
    return Text2SQLEngine()


def format_currency(value):
    """Format number as currency"""
    if pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"


def display_results(result_data):
    """Display query results with visualizations"""
    df = result_data['results']
    
    if df is None or len(df) == 0:
        st.warning("No results found for this query.")
        return
    
    # Display metrics if aggregated data
    if len(df) <= 20 and 'total_cost' in df.columns:
        cols = st.columns(3)
        
        with cols[0]:
            total = df['total_cost'].sum()
            st.metric("Total Cost", format_currency(total))
        
        with cols[1]:
            avg = df['total_cost'].mean()
            st.metric("Average Cost", format_currency(avg))
        
        with cols[2]:
            count = len(df)
            st.metric("Number of Items", count)
    
    # Display table
    st.subheader("📊 Query Results")
    
    # Format cost columns
    display_df = df.copy()
    for col in display_df.columns:
        if 'cost' in col.lower() or 'price' in col.lower():
            if display_df[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                display_df[col] = display_df[col].apply(format_currency)
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # Visualizations for aggregated data
    if len(df) <= 50 and 'total_cost' in df.columns:
        st.subheader("📈 Visualizations")
        
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            # Bar chart
            if 'servicename' in df.columns:
                fig = px.bar(
                    df.head(15), 
                    x='servicename', 
                    y='total_cost',
                    title='Cost by Service',
                    labels={'total_cost': 'Total Cost ($)', 'servicename': 'Service'},
                    color='total_cost',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            elif 'regionname' in df.columns:
                fig = px.bar(
                    df.head(15), 
                    x='regionname', 
                    y='total_cost',
                    title='Cost by Region',
                    labels={'total_cost': 'Total Cost ($)', 'regionname': 'Region'},
                    color='total_cost',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
        
        with viz_col2:
            # Pie chart
            if 'servicename' in df.columns:
                fig = px.pie(
                    df.head(10), 
                    values='total_cost', 
                    names='servicename',
                    title='Cost Distribution by Service'
                )
                st.plotly_chart(fig, use_container_width=True)
            elif 'regionname' in df.columns:
                fig = px.pie(
                    df.head(10), 
                    values='total_cost', 
                    names='regionname',
                    title='Cost Distribution by Region'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv,
        file_name="query_results.csv",
        mime="text/csv"
    )


def main():
    """Main application"""
    
    # Header
    st.markdown('<div class="main-header">☁️ CloudCost Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Text-to-SQL Engine with Semantic Metadata</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This application converts natural language questions into SQL queries 
        to analyze cloud cost data from AWS and Azure.
        
        **Features:**
        - Natural language to SQL conversion
        - Semantic metadata layer
        - Interactive visualizations
        - Support for AWS and Azure cost data
        """)
        
        st.header("📝 Example Queries")
        example_queries = [
            "What is the total AWS cost?",
            "Show me top 10 services by cost",
            "What are the costs by region?",
            "Show me Azure costs by service",
            "What is the average cost per service?",
            "Show me the top 5 most expensive regions",
            "What is the total cost for compute services?",
            "Show me costs for storage services"
        ]
        
        selected_example = st.selectbox(
            "Select an example query:",
            [""] + example_queries
        )
        
        if st.button("🔄 Use Example Query") and selected_example:
            st.session_state.query_text = selected_example
            st.rerun()
    
    # Initialize engine
    engine = get_engine()
    
    # Main query input
    st.header("🔍 Ask a Question")
    
    natural_query = st.text_input(
        "Enter your question in natural language:",
        placeholder="e.g., What is the total cost for AWS services?",
        key="query_text"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        execute_button = st.button("▶️ Execute Query", type="primary", use_container_width=True)
    
    # Execute query
    if execute_button and natural_query:
        with st.spinner("🔄 Converting to SQL and executing query..."):
            try:
                result = engine.execute_natural_query(natural_query)
                
                # Display SQL query
                st.subheader("🔧 Generated SQL Query")
                st.code(result['sql_query'], language='sql')
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Conversion Method:** {result['method']}")
                with col2:
                    st.info(f"**Rows Returned:** {result['row_count']}")
                
                # Display results
                if result['results'] is not None:
                    display_results(result)
                else:
                    st.error("Query execution failed. Please try a different question.")
                
                # Store in session state for history
                if 'query_history' not in st.session_state:
                    st.session_state.query_history = []
                
                st.session_state.query_history.append({
                    'natural': natural_query,
                    'sql': result['sql_query'],
                    'method': result['method'],
                    'rows': result['row_count']
                })
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.exception(e)
    
    # Query history
    if 'query_history' in st.session_state and st.session_state.query_history:
        st.header("📜 Query History")
        
        with st.expander("View previous queries"):
            for i, query in enumerate(reversed(st.session_state.query_history[-10:])):
                st.markdown(f"**Query {len(st.session_state.query_history) - i}:** {query['natural']}")
                st.code(query['sql'], language='sql')
                st.caption(f"Method: {query['method']} | Rows: {query['rows']}")
                st.divider()
    
    # Database statistics
    with st.expander("📊 Database Statistics"):
        db = DatabaseManager()
        db.connect()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("AWS Data")
            aws_count = db.execute_query("SELECT COUNT(*) as count FROM aws_cost")
            if aws_count is not None:
                st.metric("Total Records", f"{aws_count['count'][0]:,}")
            
            aws_cost = db.execute_query("SELECT SUM(billedcost) as total FROM aws_cost")
            if aws_cost is not None:
                st.metric("Total Cost", format_currency(aws_cost['total'][0]))
        
        with col2:
            st.subheader("Azure Data")
            azure_count = db.execute_query("SELECT COUNT(*) as count FROM azure_cost")
            if azure_count is not None:
                st.metric("Total Records", f"{azure_count['count'][0]:,}")
            
            azure_cost = db.execute_query("SELECT SUM(billedcost) as total FROM azure_cost")
            if azure_cost is not None:
                st.metric("Total Cost", format_currency(azure_cost['total'][0]))
        
        db.close()


if __name__ == "__main__":
    main()
