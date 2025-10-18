"""
Test suite for CloudCost Intelligence Text2SQL Engine
"""

import unittest
from text2sql_engine import Text2SQLEngine
from semantic_metadata import SemanticMetadataManager
from database_manager import DatabaseManager


class TestSemanticMetadata(unittest.TestCase):
    """Test semantic metadata functionality"""
    
    def setUp(self):
        self.manager = SemanticMetadataManager()
    
    def test_table_detection_aws(self):
        """Test AWS table detection"""
        table = self.manager.get_table_from_intent("Show me AWS costs")
        self.assertEqual(table, "aws_cost_usage")
    
    def test_table_detection_azure(self):
        """Test Azure table detection"""
        table = self.manager.get_table_from_intent("Show me Azure costs")
        self.assertEqual(table, "azure_cost_usage")
    
    def test_column_match_cost(self):
        """Test column matching for cost"""
        column = self.manager.find_column_match("aws_cost_usage", "cost")
        self.assertEqual(column, "billed_cost")
    
    def test_column_match_service(self):
        """Test column matching for service"""
        column = self.manager.find_column_match("aws_cost_usage", "service")
        self.assertEqual(column, "servicename")
    
    def test_aggregation_total(self):
        """Test aggregation detection for total"""
        agg = self.manager.get_aggregation_function("total cost", "billed_cost", "aws_cost_usage")
        self.assertEqual(agg, "SUM")
    
    def test_aggregation_average(self):
        """Test aggregation detection for average"""
        agg = self.manager.get_aggregation_function("average cost", "billed_cost", "aws_cost_usage")
        self.assertEqual(agg, "AVG")


class TestText2SQLEngine(unittest.TestCase):
    """Test Text2SQL engine functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database"""
        cls.engine = Text2SQLEngine(use_llm=False)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        cls.engine.close()
    
    def test_intent_analysis_total_cost(self):
        """Test intent analysis for total cost query"""
        intent = self.engine.analyze_intent("What is the total AWS cost?")
        self.assertEqual(intent['query_type'], 'aggregation')
        self.assertIn('billed_cost', intent['columns'])
    
    def test_intent_analysis_group_by_service(self):
        """Test intent analysis for group by service"""
        intent = self.engine.analyze_intent("Show me costs by service")
        self.assertIn('servicename', intent['group_by'])
    
    def test_intent_analysis_top_n(self):
        """Test intent analysis for top N query"""
        intent = self.engine.analyze_intent("Show me top 5 services")
        self.assertEqual(intent['limit'], 5)
        self.assertIsNotNone(intent['order_by'])
    
    def test_sql_generation_simple(self):
        """Test SQL generation for simple query"""
        intent = {
            'query_type': 'aggregation',
            'table': 'aws_cost_usage',
            'columns': ['billed_cost'],
            'aggregations': {},
            'filters': [],
            'group_by': [],
            'order_by': None,
            'limit': None
        }
        sql = self.engine.build_sql_from_intent(intent, "total cost")
        self.assertIn("SUM(billed_cost)", sql)
        self.assertIn("FROM aws_cost_usage", sql)
    
    def test_sql_generation_with_groupby(self):
        """Test SQL generation with GROUP BY"""
        intent = {
            'query_type': 'aggregation',
            'table': 'aws_cost_usage',
            'columns': ['billed_cost'],
            'aggregations': {},
            'filters': [],
            'group_by': ['servicename'],
            'order_by': None,
            'limit': None
        }
        sql = self.engine.build_sql_from_intent(intent, "cost by service")
        self.assertIn("GROUP BY service_name", sql)
    
    def test_query_execution(self):
        """Test actual query execution"""
        result = self.engine.execute_natural_query("What is the total cost?")
        self.assertIsNotNone(result['sql_query'])
        self.assertIn(result['method'], ['LLM', 'Rule-based'])


class TestDatabaseManager(unittest.TestCase):
    """Test database operations"""
    
    def setUp(self):
        self.db = DatabaseManager()
        self.db.connect()
    
    def tearDown(self):
        self.db.close()
    
    def test_connection(self):
        """Test database connection"""
        self.assertIsNotNone(self.db.conn)
    
    def test_query_execution(self):
        """Test query execution"""
        df = self.db.execute_query("SELECT COUNT(*) as count FROM aws_cost_usage LIMIT 1")
        self.assertIsNotNone(df)
        self.assertIn('count', df.columns)
    
    def test_table_schema(self):
        """Test getting table schema"""
        schema = self.db.get_table_schema("aws_cost_usage")
        self.assertIsNotNone(schema)
        self.assertGreater(len(schema), 0)


def run_tests():
    """Run all tests"""
    print("Running CloudCost Intelligence Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticMetadata))
    suite.addTests(loader.loadTestsFromTestCase(TestText2SQLEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

