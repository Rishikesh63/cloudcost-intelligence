# Metadata Extraction Technical Documentation

## Overview

This document explains the technical methodology used for **automated metadata extraction** in the CloudCost Intelligence Text2SQL Engine, including semantic enrichment and FOCUS standard alignment.

---

## 1. Metadata Extraction Architecture

### 1.1 Dual-Mode Approach

The system supports **two metadata extraction modes**:

1. **Predefined Mode** (Default)
   - Manually curated metadata with rich semantic annotations
   - Based on FinOps FOCUS v1.0 standard
   - Includes expert guidance and LLM usage hints
   - File: `semantic_metadata_predefined.json`

2. **Auto-Extraction Mode** (Dynamic)
   - Automatically extracts schema from existing database
   - Uses SQLite PRAGMA introspection
   - Enriched with semantic aliases and aggregation hints
   - File: `semantic_metadata_extracted.json`

---

## 2. Auto-Extraction Methodology

### 2.1 Schema Introspection Process

The auto-extraction uses SQLite's `PRAGMA` commands to extract structural metadata:

```python
def _extract_metadata_from_db(self) -> Dict:
    """Extract metadata directly from database using PRAGMA"""
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Extract: column name, data type, nullable, primary key
```

**PRAGMA Commands Used:**
- `PRAGMA table_info(table_name)` - Column names, types, constraints
- `SELECT name FROM sqlite_master` - Table discovery

**Extracted Attributes:**
| Attribute | Source | Description |
|-----------|--------|-------------|
| `name` | PRAGMA column name | Column identifier |
| `data_type` | PRAGMA type | SQLite type (TEXT, REAL, INTEGER) |
| `nullable` | PRAGMA notnull | Whether NULL values allowed |
| `primary_key` | PRAGMA pk | Primary key indicator |

### 2.2 Data Type Mapping

SQLite types are mapped to semantic categories:

```python
TYPE_MAPPING = {
    "TEXT": "string",
    "REAL": "numeric",
    "INTEGER": "numeric",
    "BLOB": "binary"
}
```

### 2.3 Sample Value Extraction

For each column, we extract sample distinct values to aid LLM understanding:

```sql
SELECT DISTINCT column_name 
FROM table_name 
WHERE column_name IS NOT NULL 
LIMIT 5
```

**Purpose**: Help LLM understand data patterns and domains.

---

## 3. Semantic Enrichment Process

### 3.1 Alias Generation

Auto-extracted metadata is enriched with semantic aliases using pattern matching:

```python
SEMANTIC_MAPPINGS = {
    "billedcost": ["cost", "bill", "charge", "amount", "price", "spend", "expense"],
    "servicename": ["service", "product", "service name"],
    "regionname": ["region", "location", "geography", "area"],
    "subaccountname": ["account", "subaccount", "subscription"]
}
```

**Algorithm:**
1. Check if column name matches known billing fields
2. Apply predefined alias mappings
3. Add lowercase version and variations
4. Fall back to column name itself

**Example:**
```json
{
  "billedcost": {
    "aliases": ["cost", "bill", "charge", "amount", "price", "spend", "expense"]
  }
}
```

### 3.2 Aggregation Hint Injection

For numeric columns, aggregation functions are auto-suggested:

```python
if column_type in ["REAL", "INTEGER"]:
    metadata["aggregations"] = ["SUM", "AVG", "MIN", "MAX", "COUNT"]
```

**Purpose**: Guide LLM on appropriate SQL aggregation functions.

---

## 4. FOCUS Standard Integration

### 4.1 FinOps FOCUS v1.0 Alignment

The predefined metadata aligns with the **FinOps Open Cost and Usage Specification (FOCUS) v1.0**:

**Key FOCUS Fields Implemented:**
| FOCUS Field | Our Mapping | Category |
|-------------|-------------|----------|
| `BilledCost` | `billedcost` | Metric (Mandatory) |
| `EffectiveCost` | `effectivecost` | Metric (Recommended) |
| `ServiceName` | `servicename` | Dimension |
| `RegionName` | `regionname` | Dimension |
| `BillingPeriodStart` | `billingperiodstart` | Temporal |
| `BillingPeriodEnd` | `billingperiodend` | Temporal |
| `ConsumedQuantity` | `consumedquantity` | Metric |
| `SubAccountName` | `subaccountname` | Dimension |

### 4.2 AWS FOCUS Dictionary Reference

AWS-specific fields follow the [AWS FOCUS Column Dictionary](https://docs.aws.amazon.com/cur/latest/userguide/table-dictionary-focus-1-0-aws-columns.html):

**AWS Extensions (x_ prefix):**
- `x_servicecode` - AWS service identifier
- `x_usagetype` - Detailed usage categorization  
- `x_operation` - API operation name
- `x_discounts` - Applied discount information

### 4.3 Azure Cost Management Schema

Azure fields follow [Azure FOCUS Schema v1.0](https://learn.microsoft.com/en-us/azure/cost-management-billing/dataset-schema/cost-usage-details-focus):

**Azure-Specific Mappings:**
- `SubscriptionName` → `subaccountname`
- `MeterCategory` → `servicecategory`
- `ResourceGroup` → Mapped to tags
- `BillingAccountType` → `billingaccounttype`

---

## 5. Profiling Techniques

### 5.1 Distinct Value Analysis

```python
# Count distinct values for cardinality estimation
SELECT COUNT(DISTINCT column_name) as cardinality FROM table_name

# If cardinality < 20: Low cardinality dimension (good for GROUP BY)
# If cardinality > 1000: High cardinality identifier (use for filtering)
```

**Purpose**: Determine if column is suitable for grouping vs filtering.

### 5.2 Null Percentage Detection

```python
# Calculate null percentage
SELECT 
    COUNT(*) as total_rows,
    COUNT(column_name) as non_null_rows,
    100.0 * (COUNT(*) - COUNT(column_name)) / COUNT(*) as null_percentage
FROM table_name
```

**Classification:**
- < 5% nulls: Mandatory field (high data quality)
- 5-30% nulls: Optional field
- \> 30% nulls: Sparse field (use with caution)

### 5.3 Data Type Inference

Beyond SQLite type, infer semantic type:

```python
# Detect temporal columns
if "date" in column_name or "period" in column_name:
    metadata["temporal"] = True

# Detect monetary columns  
if "cost" in column_name or "price" in column_name:
    metadata["category"] = "Metric"
    metadata["unit"] = "currency"

# Detect identifiers
if "id" in column_name or column_name.endswith("name"):
    metadata["category"] = "Dimension"
```

---

## 6. LLM Usage Guidance Structure

### 6.1 Filterable vs Groupable Classification

**Filterable Fields** (use in WHERE clause):
- High cardinality dimensions (e.g., `resourceid`)
- Identifier fields
- Temporal fields with specific ranges

**Groupable Fields** (use in GROUP BY):
- Low-medium cardinality dimensions (e.g., `servicename`, `regionname`)
- Categorical fields
- Non-identifier strings

**Example Metadata:**
```json
{
  "servicename": {
    "llm_usage_guidance": {
      "filterable": true,
      "groupable": true,
      "aggregate_function": null
    }
  },
  "billedcost": {
    "llm_usage_guidance": {
      "filterable": true,
      "groupable": false,
      "aggregate_function": "SUM"
    }
  }
}
```

### 6.2 Expert Guidance Annotations

Following the assignment's requirement, key fields include expert guidance:

```json
{
  "billedcost": {
    "expert_guidance": {
      "when_to_use": "For all cost reporting and trend analysis. This is the standard cost metric.",
      "how_to_use": "Use SUM(billedcost) for total costs. GROUP BY servicename for service breakdown.",
      "do_not_use_for": "Do not use for effective cost analysis (use effectivecost instead)."
    }
  }
}
```

**Coverage:**
- ✅ `billedcost` - Standard cost metric
- ✅ `effectivecost` - Amortized cost with discounts
- ✅ `servicename` - Service grouping
- ✅ `regionname` - Geographic analysis
- ✅ `consumedquantity` - Usage metrics

---

## 7. Query Probing for Validation

### 7.1 Self-Driven Exploration (SDE-SQL Approach)

Inspired by [SDE-SQL research](https://arxiv.org/abs/2401.02117), we use SQL probes to validate metadata:

```python
# Probe 1: Validate aggregatable columns
SELECT SUM(billedcost), AVG(billedcost) FROM aws_cost

# Probe 2: Validate groupable columns  
SELECT servicename, COUNT(*) FROM aws_cost GROUP BY servicename

# Probe 3: Check temporal validity
SELECT MIN(billingperiodstart), MAX(billingperiodend) FROM aws_cost
```

**Purpose**: 
- Verify aggregation functions work
- Confirm GROUP BY doesn't fail
- Detect data quality issues

### 7.2 Metadata Validation Checks

```python
# Check 1: Ensure no NULL-only columns
if null_percentage == 100:
    warnings.append(f"Column {col_name} is entirely NULL")

# Check 2: Validate data types
if expected_type == "REAL" and actual_type == "TEXT":
    warnings.append(f"Type mismatch for {col_name}")

# Check 3: Cardinality sanity
if cardinality > total_rows * 0.9:
    warnings.append(f"Column {col_name} has very high cardinality")
```

---

## 8. Performance Optimizations

### 8.1 Lazy Loading

Metadata extraction is performed once and cached:

```python
def __init__(self, db_path, auto_extract=False):
    if auto_extract:
        self.metadata = self._extract_metadata_from_db()
        self._save_metadata("semantic_metadata_extracted.json")
    else:
        self.metadata = self._load_predefined_metadata()
```

### 8.2 Incremental Updates

For database schema changes:

```python
# Detect new columns
new_columns = set(extracted_columns) - set(existing_metadata_columns)

# Merge with existing metadata
merged_metadata = {**existing, **extracted}
```

---

## 9. Output Format

### 9.1 JSON Structure

```json
{
  "table_name": {
    "description": "Table description",
    "aliases": ["alias1", "alias2"],
    "columns": {
      "column_name": {
        "description": "Column description",
        "data_type": "REAL",
        "nullable": true,
        "primary_key": false,
        "aliases": ["alias1", "alias2"],
        "aggregations": ["SUM", "AVG"],
        "llm_usage_guidance": {
          "filterable": true,
          "groupable": false,
          "aggregate_function": "SUM"
        },
        "expert_guidance": {
          "when_to_use": "...",
          "how_to_use": "...",
          "do_not_use_for": "..."
        }
      }
    }
  }
}
```

### 9.2 File Outputs

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `semantic_metadata_predefined.json` | Curated, FOCUS-aligned | Manual |
| `semantic_metadata_extracted.json` | Auto-generated | On schema change |

---

## 10. Integration with Text2SQL Engine

### 10.1 Metadata Usage in SQL Generation

The Text2SQL engine uses metadata for:

1. **Intent Analysis**: Map natural language terms to columns using aliases
2. **SQL Construction**: Select appropriate aggregation functions
3. **Validation**: Ensure generated SQL uses valid columns/tables

**Example Flow:**
```
User: "Show me total cost by service"
      ↓
Alias Lookup: "cost" → "billedcost", "service" → "servicename"
      ↓
Aggregation Hint: billedcost → SUM()
      ↓
Generated SQL: SELECT servicename, SUM(billedcost) FROM aws_cost GROUP BY servicename
```

### 10.2 LLM Prompt Enhancement

Metadata is injected into LLM prompts:

```python
prompt = f"""
Database Schema:
{self._get_schema_context()}

Important: billedcost should be used with SUM() for cost totals.
servicename is groupable for service breakdowns.
"""
```

---

## 11. Limitations & Future Enhancements

### Current Limitations

1. **No Foreign Key Detection**: SQLite PRAGMA doesn't expose relationships
2. **Limited Type Inference**: Can't detect enums or constrained values
3. **Static Aliases**: Alias mapping is predefined, not learned

### Planned Enhancements

1. **ML-based Alias Learning**: Learn aliases from query logs
2. **Statistical Profiling**: Min/max/median/percentile analysis
3. **Index Recommendations**: Suggest indexes based on query patterns
4. **Version Control**: Track metadata changes over time

---

## 12. References

### Academic Research

1. **SDE-SQL**: Enhancing Text-to-SQL Generation via Self-Driven Exploration  
   *Arxiv 2024* - https://arxiv.org/abs/2401.02117

2. **Automated Metadata Extraction for Text2SQL**  
   *NLP for Data Science Workshop 2023*

### Industry Standards

3. **FinOps FOCUS Specification v1.0**  
   https://focus.finops.org/focus-specification/v1-0/

4. **AWS FOCUS Column Dictionary**  
   https://docs.aws.amazon.com/cur/latest/userguide/table-dictionary-focus-1-0-aws-columns.html

5. **Azure Cost Management FOCUS Schema**  
   https://learn.microsoft.com/en-us/azure/cost-management-billing/dataset-schema/cost-usage-details-focus

---

## Conclusion

The CloudCost Intelligence metadata extraction system combines:
- ✅ Automated schema introspection using PRAGMA
- ✅ Semantic enrichment with FOCUS-aligned aliases
- ✅ LLM usage guidance for accurate SQL generation
- ✅ Expert annotations for production-grade queries
- ✅ Dual-mode flexibility (auto + curated)

This approach ensures **high-quality Text2SQL conversion** with minimal manual configuration while maintaining extensibility for custom metadata enhancement.

---

**Document Version**: 1.0  
**Last Updated**: October 17, 2025  
**Author**: CloudCost Intelligence Team
