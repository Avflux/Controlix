import logging
from typing import Set, Dict, List
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class CacheInvalidator:
    def __init__(self):
        # Padrões de invalidação por tabela
        self.invalidation_patterns: Dict[str, Set[str]] = {
            'funcionarios': {'SELECT.*FROM.*funcionarios', 'SELECT.*funcionarios.*JOIN'},
            'configuracoes': {'SELECT.*FROM.*configuracoes'},
            'operation_logs': {'SELECT.*FROM.*operation_logs'}
        }
        
        # Cache de padrões compilados
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compila padrões de regex para melhor performance"""
        for table, patterns in self.invalidation_patterns.items():
            self._compiled_patterns[table] = {
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            }
    
    def should_invalidate(self, query: str) -> List[str]:
        """
        Verifica se uma query deve invalidar cache
        Retorna lista de padrões que devem ser invalidados
        """
        affected_tables = self._extract_affected_tables(query)
        patterns_to_invalidate = set()
        
        for table in affected_tables:
            if table in self._compiled_patterns:
                patterns_to_invalidate.update(self._compiled_patterns[table])
                
        return list(patterns_to_invalidate)
    
    def _extract_affected_tables(self, query: str) -> Set[str]:
        """Extrai tabelas afetadas por uma query"""
        tables = set()
        query = query.lower()
        
        # Detecta operações de modificação
        if any(op in query for op in ['insert', 'update', 'delete']):
            # Extrai nome da tabela após INSERT INTO, UPDATE ou DELETE FROM
            match = re.search(r'(?:into|update|from)\s+(\w+)', query)
            if match:
                tables.add(match.group(1))
                
        return tables

# Instância global
cache_invalidator = CacheInvalidator() 