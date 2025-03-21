"""
Testes para o módulo de conversão de tipos entre MySQL e SQLite.
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from app.data.sync.type_converters import DataTypeConverter

class TestDataTypeConverter(unittest.TestCase):
    def setUp(self):
        self.converter = DataTypeConverter()
        
    def test_time_conversion(self):
        """Testa conversão de TIME entre MySQL e SQLite"""
        # MySQL -> SQLite
        time_delta = timedelta(hours=2, minutes=30, seconds=15)
        sqlite_value = self.converter.convert_to_sqlite(time_delta, 'TIME')
        self.assertEqual(sqlite_value, 9015.0)  # 2h30m15s em segundos
        
        # SQLite -> MySQL
        mysql_value = self.converter.convert_to_mysql(sqlite_value, 'REAL', 'TIME')
        self.assertEqual(mysql_value, time_delta)
    
    def test_datetime_conversion(self):
        """Testa conversão de DATETIME entre MySQL e SQLite"""
        # MySQL -> SQLite
        dt = datetime(2024, 3, 5, 14, 30, 0)
        sqlite_value = self.converter.convert_to_sqlite(dt, 'DATETIME')
        self.assertEqual(sqlite_value, '2024-03-05T14:30:00')
        
        # SQLite -> MySQL
        mysql_value = self.converter.convert_to_mysql(sqlite_value, 'TEXT', 'DATETIME')
        self.assertEqual(mysql_value, dt)
    
    def test_boolean_conversion(self):
        """Testa conversão de BOOLEAN entre MySQL e SQLite"""
        # MySQL -> SQLite
        self.assertEqual(self.converter.convert_to_sqlite(True, 'BOOLEAN'), 1)
        self.assertEqual(self.converter.convert_to_sqlite(False, 'BOOLEAN'), 0)
        self.assertEqual(self.converter.convert_to_sqlite('yes', 'BOOLEAN'), 1)
        self.assertEqual(self.converter.convert_to_sqlite('no', 'BOOLEAN'), 0)
        
        # SQLite -> MySQL
        self.assertEqual(self.converter.convert_to_mysql(1, 'INTEGER', 'BOOLEAN'), True)
        self.assertEqual(self.converter.convert_to_mysql(0, 'INTEGER', 'BOOLEAN'), False)
    
    def test_decimal_conversion(self):
        """Testa conversão de DECIMAL entre MySQL e SQLite"""
        # MySQL -> SQLite
        decimal_value = Decimal('123.45')
        sqlite_value = self.converter.convert_to_sqlite(decimal_value, 'DECIMAL')
        self.assertEqual(sqlite_value, 123.45)
        
        # SQLite -> MySQL
        mysql_value = self.converter.convert_to_mysql(sqlite_value, 'REAL', 'DECIMAL(10,2)')
        self.assertEqual(mysql_value, decimal_value)
    
    def test_enum_conversion(self):
        """Testa conversão de ENUM entre MySQL e SQLite"""
        # MySQL -> SQLite
        enum_value = 'admin'
        sqlite_value = self.converter.convert_to_sqlite(enum_value, 'ENUM')
        self.assertEqual(sqlite_value, 'admin')
        
        # SQLite -> MySQL
        mysql_value = self.converter.convert_to_mysql(sqlite_value, 'TEXT', 'ENUM')
        self.assertEqual(mysql_value, enum_value)
    
    def test_null_values(self):
        """Testa conversão de valores NULL"""
        self.assertIsNone(self.converter.convert_to_sqlite(None, 'TIME'))
        self.assertIsNone(self.converter.convert_to_mysql(None, 'TEXT', 'DATETIME'))
    
    def test_invalid_conversions(self):
        """Testa tratamento de conversões inválidas"""
        with self.assertRaises(ValueError):
            self.converter.convert_to_sqlite('invalid', 'TIME')
        
        with self.assertRaises(ValueError):
            self.converter.convert_to_mysql('invalid', 'TEXT', 'DATETIME')
    
    def test_cache_functionality(self):
        """Testa se o cache está funcionando"""
        # Primeira chamada
        result1 = self.converter.convert_to_sqlite(True, 'BOOLEAN')
        # Segunda chamada (deve usar cache)
        result2 = self.converter.convert_to_sqlite(True, 'BOOLEAN')
        
        self.assertEqual(result1, result2)
        self.assertEqual(result1, 1)

if __name__ == '__main__':
    unittest.main() 