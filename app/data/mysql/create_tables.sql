-- Teams Table
CREATE TABLE IF NOT EXISTS equipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL UNIQUE,
    descricao TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    version INT NOT NULL DEFAULT 1,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Users Table
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipe_id INT,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    name_id VARCHAR(50),
    senha VARCHAR(255) NOT NULL,
    tipo_usuario ENUM('admin', 'comum') DEFAULT 'comum',
    data_entrada DATE,
    data_saida DATE,
    base_value DECIMAL(10,2),
    ociosidade TIME,
    is_logged_in BOOLEAN DEFAULT FALSE,
    status BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT NOT NULL DEFAULT 1,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (equipe_id) REFERENCES equipes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Funcionarios Table
CREATE TABLE IF NOT EXISTS funcionarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name_id VARCHAR(50) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    status BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT NOT NULL DEFAULT 1,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Activities Table
CREATE TABLE IF NOT EXISTS atividades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    description TEXT,
    atividade VARCHAR(255) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    time_regress TIME,
    time_exceeded TIME,
    reason TEXT,
    total_time TIME,
    ativo BOOLEAN DEFAULT TRUE,
    pausado BOOLEAN DEFAULT FALSE,
    concluido BOOLEAN DEFAULT FALSE,
    current_mode VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT NOT NULL DEFAULT 1,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Lock/Unlock Table
CREATE TABLE IF NOT EXISTS user_lock_unlock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    lock_status BOOLEAN DEFAULT FALSE,
    unlock_control BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT NOT NULL DEFAULT 1,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- System Logs Table
CREATE TABLE IF NOT EXISTS logs_sistema (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    acao VARCHAR(255) NOT NULL,
    descricao TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    version INT NOT NULL DEFAULT 1,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- System Configuration Table
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    version INT NOT NULL DEFAULT 1,
    last_modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sync Log Table
CREATE TABLE IF NOT EXISTS sync_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    operation ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    old_data TEXT,
    new_data TEXT,
    version INT NOT NULL,
    sync_status ENUM('PENDING', 'SYNCED', 'CONFLICT', 'ERROR') NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sync_status (sync_status),
    INDEX idx_table_record (table_name, record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sync Conflicts Table
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    local_data TEXT NOT NULL,
    remote_data TEXT NOT NULL,
    local_version INT NOT NULL,
    remote_version INT NOT NULL,
    local_modified TIMESTAMP NOT NULL,
    remote_modified TIMESTAMP NOT NULL,
    resolution_strategy VARCHAR(50) NOT NULL,
    resolved_at TIMESTAMP NULL,
    resolved_by VARCHAR(100),
    resolution_data TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sync Metadata Table
CREATE TABLE IF NOT EXISTS sync_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    key_name VARCHAR(100) NOT NULL UNIQUE,
    value TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create trigger for auto-inserting lock status when a new user is created
DELIMITER //
CREATE TRIGGER after_usuario_insert 
AFTER INSERT ON usuarios
FOR EACH ROW
BEGIN
    INSERT INTO user_lock_unlock (user_id, lock_status, unlock_control, created_at) 
    VALUES (NEW.id, FALSE, TRUE, NOW());
END//
DELIMITER ;

-- Insert default teams
INSERT IGNORE INTO equipes (nome, descricao) VALUES
('Administrativo', 'Equipe Administrativa'),
('Civil', 'Equipe Civil'),
('Diretoria', 'Equipe Diretoria'),
('Eletromecânico', 'Equipe Eletromecânica'),
('SPCS', 'Equipe SPCS');

-- Insert default admin user
INSERT IGNORE INTO usuarios (nome, email, name_id, senha, tipo_usuario, equipe_id, data_entrada, status) 
SELECT 'Administrator', 'admin@interest.com.br', 'admin', 'admin123', 'admin', e.id, CURDATE(), TRUE
FROM equipes e 
WHERE e.nome = 'Administrativo'
LIMIT 1;

-- Insert default system configurations
INSERT IGNORE INTO system_config (config_key, config_value) VALUES
('SYSTEM_VERSION', '1.0'),
('MAX_LOGIN_ATTEMPTS', '3');

-- Insert initial sync metadata
INSERT IGNORE INTO sync_metadata (key_name, value) VALUES
('last_sync', NULL); 