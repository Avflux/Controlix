# Sistema de Sincronização MySQL

Este módulo implementa um sistema de sincronização bidirecional entre bancos de dados MySQL local e remoto, com prioridade para o banco remoto.

## Estrutura do Módulo

- `__init__.py`: Exporta as classes principais
- `connection_pool.py`: Implementa o pool de conexões MySQL
- `mysql_connection.py`: Gerencia conexões com bancos MySQL local e remoto
- `create_tables.sql`: Script SQL para criação das tabelas
- `sync_manager.py`: Implementa o gerenciador de sincronização
- `test_sync.py`: Script para testar a sincronização

## Configuração

### Requisitos

- MySQL Server instalado localmente
- Acesso a um servidor MySQL remoto
- Bibliotecas Python: `mysql-connector-python`

### Configuração de Ambiente

As configurações de conexão são obtidas das variáveis de ambiente:

**MySQL Local:**
- `MYSQL_LOCAL_HOST`: Host do MySQL local (padrão: localhost)
- `MYSQL_LOCAL_PORT`: Porta do MySQL local (padrão: 3306)
- `MYSQL_LOCAL_USER`: Usuário do MySQL local (padrão: root)
- `MYSQL_LOCAL_PASSWORD`: Senha do MySQL local
- `MYSQL_LOCAL_DATABASE`: Nome do banco de dados local (padrão: controlix_local)

**MySQL Remoto:**
- `MYSQL_REMOTE_HOST`: Host do MySQL remoto
- `MYSQL_REMOTE_PORT`: Porta do MySQL remoto (padrão: 3306)
- `MYSQL_REMOTE_USER`: Usuário do MySQL remoto
- `MYSQL_REMOTE_PASSWORD`: Senha do MySQL remoto
- `MYSQL_REMOTE_DATABASE`: Nome do banco de dados remoto (padrão: controlix_remote)

## Uso

### Inicialização

```python
from app.data.mysql.mysql_connection import MySQLConnection
from app.data.mysql.sync_manager import MySQLSyncManager, SyncDirection

# Inicializar conexão
db_connection = MySQLConnection()

# Inicializar gerenciador de sincronização
sync_manager = MySQLSyncManager()
```

### Executar Sincronização

```python
# Sincronização bidirecional
stats = sync_manager.synchronize(SyncDirection.BIDIRECTIONAL)

# Sincronização do local para o remoto
stats = sync_manager.synchronize(SyncDirection.LOCAL_TO_REMOTE)

# Sincronização do remoto para o local
stats = sync_manager.synchronize(SyncDirection.REMOTE_TO_LOCAL)

# Verificar estatísticas
print(f"Registros sincronizados: {stats['records_synced']}")
print(f"Conflitos: {stats['conflicts']}")
print(f"Erros: {stats['errors']}")
```

### Sincronização Automática

```python
# Inicializar com sincronização automática a cada 5 minutos
sync_manager = MySQLSyncManager(auto_sync=True, sync_interval=300)

# Parar sincronização automática
sync_manager.stop_auto_sync()
```

## Tabelas de Controle

O sistema utiliza as seguintes tabelas para controle de sincronização:

1. **sync_log**: Registra operações de sincronização
   - `table_name`: Nome da tabela
   - `record_id`: ID do registro
   - `operation`: Operação (INSERT, UPDATE, DELETE)
   - `old_data`: Dados antigos (JSON)
   - `new_data`: Novos dados (JSON)
   - `version`: Versão do registro
   - `sync_status`: Status da sincronização (PENDING, SYNCED, CONFLICT, ERROR)

2. **sync_conflicts**: Registra conflitos de sincronização
   - `table_name`: Nome da tabela
   - `record_id`: ID do registro
   - `local_data`: Dados do banco local (JSON)
   - `remote_data`: Dados do banco remoto (JSON)
   - `local_version`: Versão no banco local
   - `remote_version`: Versão no banco remoto
   - `resolution_strategy`: Estratégia de resolução

3. **sync_metadata**: Armazena metadados de sincronização
   - `key_name`: Nome da chave
   - `value`: Valor (JSON)

## Estratégias de Resolução de Conflitos

O sistema suporta as seguintes estratégias de resolução de conflitos:

- **REMOTE_WINS**: Prioridade para o banco remoto (padrão)
- **LOCAL_WINS**: Prioridade para o banco local
- **MANUAL**: Resolução manual pelo usuário
- **NEWEST_WINS**: Prioridade para a versão mais recente

## Requisitos para Tabelas

Para que a sincronização funcione corretamente, todas as tabelas devem ter:

1. Uma coluna de chave primária (padrão: `id`)
2. Uma coluna `version` (INT) para controle de versão
3. Uma coluna `last_modified` (TIMESTAMP) para controle de data/hora de modificação

## Testes

O script `test_sync.py` permite testar a sincronização:

```bash
# Configurar dados de teste
python app/data/mysql/test_sync.py --setup

# Testar sincronização local para remoto
python app/data/mysql/test_sync.py --local-to-remote

# Testar sincronização remoto para local
python app/data/mysql/test_sync.py --remote-to-local

# Testar resolução de conflitos
python app/data/mysql/test_sync.py --conflict

# Executar todos os testes
python app/data/mysql/test_sync.py --all
```

## Troubleshooting

### Problemas Comuns

1. **Erro de conexão com o banco remoto**
   - Verifique as credenciais e configurações de rede
   - Certifique-se de que o usuário tem permissões adequadas

2. **Conflitos frequentes**
   - Verifique se os relógios dos servidores estão sincronizados
   - Considere ajustar a estratégia de resolução de conflitos

3. **Desempenho lento**
   - Verifique a latência da rede para o servidor remoto
   - Considere aumentar o intervalo de sincronização automática
   - Verifique se há índices adequados nas tabelas
``` 