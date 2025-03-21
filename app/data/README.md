# Módulo de Dados da Aplicação

Este módulo contém todos os componentes relacionados ao gerenciamento de dados da aplicação.

## Estrutura de Pastas

- **cache/** - Gerenciamento de cache e monitoramento de memória
  - `memory_monitor.py` - Monitor de uso de memória
  - `query_cache.py` - Cache de consultas SQL
  - `cache_invalidator.py` - Invalidação de cache
  - `cache_monitor.py` - Monitoramento de cache
  - `auth_cache.py` - Cache de autenticação

## Arquivos Principais

- `connection.py` - Gerenciamento de conexões para MySQL e MySQL local
- `secure_storage.py` - Armazenamento seguro de dados
- `backup_manager.py` - Gerenciamento de backups
- `cache_manager.py` - Gerenciamento de cache
- `user_settings.json` - Configurações do usuário

## Notas

- A pasta `mysql` foi consolidada nesta estrutura para evitar duplicação de código.
- Todos os componentes relacionados a dados estão centralizados neste módulo. 