"""
Módulo de conexão e gerenciamento de banco de dados MySQL.
Fornece classes e funções para interagir com bancos de dados MySQL locais e remotos.
"""

from app.data.mysql.connection_pool import MySQLPool
from app.data.mysql.mysql_connection import MySQLConnection

__all__ = ['MySQLPool', 'MySQLConnection'] 