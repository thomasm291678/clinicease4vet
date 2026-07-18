"""数据库连接与初始化 — 支持 MySQL + SQLite 双模式

优先使用 MySQL，连接失败自动降级 SQLite
"""

import os
import sqlite3
from config import Config

_use_sqlite = False
_sqlite_path = os.path.join(Config.BASE_DIR, "data", "clinicease.db")


class _SqliteConnectionWrapper:
    """包装 SQLite 连接，使其 cursor() 返回自动 %s→? 转换的游标"""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _SqliteCursorWrapper(self._conn.cursor(), self._conn)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


class _SqliteCursorWrapper:
    """包装 SQLite cursor，自动将 MySQL 风格 %s 转为 SQLite 风格 ?"""

    def __init__(self, cursor, conn):
        self._cursor = cursor
        self._conn = conn

    def execute(self, sql, params=None):
        if _use_sqlite:
            sql = sql.replace("%s", "?")
        if params is not None:
            return self._cursor.execute(sql, params)
        return self._cursor.execute(sql)

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def close(self):
        return self._cursor.close()


def get_connection():
    """获取数据库连接（自动选择 MySQL 或 SQLite）"""
    global _use_sqlite

    if _use_sqlite:
        _ensure_sqlite_dir()
        raw = sqlite3.connect(_sqlite_path)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA journal_mode=WAL")
        raw.execute("PRAGMA foreign_keys=ON")
        return _SqliteConnectionWrapper(raw)

    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            passwd=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
        )
        return conn
    except Exception as e:
        print(f"[DB] MySQL 连接失败 ({e})，降级使用 SQLite")
        _use_sqlite = True
        _ensure_sqlite_dir()
        raw = sqlite3.connect(_sqlite_path)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA journal_mode=WAL")
        raw.execute("PRAGMA foreign_keys=ON")
        return _SqliteConnectionWrapper(raw)


def get_cursor(conn):
    """获取游标（SQLite 模式下自动转换 %s → ?）"""
    return _SqliteCursorWrapper(conn.cursor(), conn) if _use_sqlite else conn.cursor()


def _ensure_sqlite_dir():
    os.makedirs(os.path.dirname(_sqlite_path), exist_ok=True)


def init_database():
    """创建数据库和所有表"""
    global _use_sqlite

    # 先尝试 MySQL
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            passwd=Config.MYSQL_PASSWORD,
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DATABASE}")
        cursor.close()
        conn.close()
        _use_sqlite = False
        print("[DB] 使用 MySQL")
    except Exception as e:
        print(f"[DB] MySQL 不可用 ({e})，使用 SQLite")
        _use_sqlite = True
        _ensure_sqlite_dir()

    conn = get_connection()
    cursor = conn.cursor()

    if _use_sqlite:
        _init_sqlite_tables(cursor)
    else:
        _init_mysql_tables(cursor)

    conn.commit()
    cursor.close()
    conn.close()
    print("[DB] 数据库初始化完成")


def _init_sqlite_tables(cursor):
    """SQLite 建表语句"""
    cursor.execute("""CREATE TABLE IF NOT EXISTS pet_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(30) NOT NULL,
        species VARCHAR(30) NOT NULL,
        breed VARCHAR(30),
        gender VARCHAR(10),
        age_months INTEGER,
        weight_kg REAL,
        color VARCHAR(20),
        owner_name VARCHAR(30) NOT NULL,
        owner_contact VARCHAR(15),
        owner_address VARCHAR(100),
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS vet_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(30) NOT NULL,
        specialisation VARCHAR(40),
        license_no VARCHAR(30),
        age INTEGER,
        address VARCHAR(50),
        contact VARCHAR(15),
        consultation_fee INTEGER,
        monthly_salary INTEGER
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS assistant_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(30) NOT NULL,
        role VARCHAR(30),
        age INTEGER,
        address VARCHAR(50),
        contact VARCHAR(15),
        monthly_salary INTEGER
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS other_workers_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(30) NOT NULL,
        role VARCHAR(30),
        age INTEGER,
        address VARCHAR(50),
        contact VARCHAR(15),
        monthly_salary INTEGER
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS user_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(30) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) DEFAULT 'staff'
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS medical_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER NOT NULL,
        vet_name VARCHAR(30),
        visit_date DATE NOT NULL,
        diagnosis TEXT,
        treatment TEXT,
        symptoms TEXT,
        subjective TEXT,
        objective TEXT,
        assessment TEXT,
        plan TEXT,
        clinical_reasoning_data TEXT,
        notes TEXT,
        follow_up_date DATE,
        fee_charged INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE CASCADE
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS clinical_reasoning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        problem_list TEXT,
        reasoning_path TEXT,
        differential_list TEXT,
        must_not_miss TEXT,
        missing_info TEXT,
        recommended_tests TEXT,
        dynamic_questions TEXT,
        client_communication TEXT,
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (record_id) REFERENCES medical_records(id) ON DELETE CASCADE
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS vaccination_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER NOT NULL,
        vaccine_name VARCHAR(50) NOT NULL,
        dose_number INTEGER DEFAULT 1,
        administered_date DATE NOT NULL,
        next_due_date DATE,
        vet_name VARCHAR(30),
        batch_number VARCHAR(30),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE CASCADE
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS drug_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drug_name VARCHAR(50) NOT NULL,
        category VARCHAR(30),
        manufacturer VARCHAR(50),
        batch_number VARCHAR(30),
        quantity INTEGER DEFAULT 0,
        unit VARCHAR(10) DEFAULT '瓶',
        unit_price REAL,
        expiry_date DATE,
        storage_condition VARCHAR(50),
        min_stock_level INTEGER DEFAULT 5,
        notes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(100) NOT NULL,
        event_date DATE NOT NULL,
        start_time VARCHAR(5) DEFAULT '09:00',
        end_time VARCHAR(5) DEFAULT '09:30',
        event_type VARCHAR(20) DEFAULT 'appointment',
        pet_id INTEGER,
        pet_name VARCHAR(30),
        owner_name VARCHAR(30),
        medical_record_id INTEGER,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'scheduled',
        color VARCHAR(7) DEFAULT '#2563eb',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE SET NULL
    )""")


def _init_mysql_tables(cursor):
    """MySQL 建表语句"""
    cursor.execute("""CREATE TABLE IF NOT EXISTS pet_details (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(30) NOT NULL,
        species VARCHAR(30) NOT NULL,
        breed VARCHAR(30),
        gender VARCHAR(10),
        age_months INT,
        weight_kg DECIMAL(5,2),
        color VARCHAR(20),
        owner_name VARCHAR(30) NOT NULL,
        owner_contact VARCHAR(15),
        owner_address VARCHAR(100),
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS vet_details (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(30) NOT NULL,
        specialisation VARCHAR(40),
        license_no VARCHAR(30),
        age INT,
        address VARCHAR(50),
        contact VARCHAR(15),
        consultation_fee INT,
        monthly_salary INT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS assistant_details (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(30) NOT NULL,
        role VARCHAR(30),
        age INT,
        address VARCHAR(50),
        contact VARCHAR(15),
        monthly_salary INT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS other_workers_details (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(30) NOT NULL,
        role VARCHAR(30),
        age INT,
        address VARCHAR(50),
        contact VARCHAR(15),
        monthly_salary INT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS user_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(30) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) DEFAULT 'staff'
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS medical_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        vet_name VARCHAR(30),
        visit_date DATE NOT NULL,
        diagnosis TEXT,
        treatment TEXT,
        symptoms TEXT,
        subjective TEXT,
        objective TEXT,
        assessment TEXT,
        plan TEXT,
        clinical_reasoning_data JSON,
        notes TEXT,
        follow_up_date DATE,
        fee_charged INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE CASCADE
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS clinical_reasoning (
        id INT AUTO_INCREMENT PRIMARY KEY,
        record_id INT NOT NULL,
        problem_list JSON,
        reasoning_path TEXT,
        differential_list JSON,
        must_not_miss JSON,
        missing_info TEXT,
        recommended_tests JSON,
        dynamic_questions TEXT,
        client_communication JSON,
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (record_id) REFERENCES medical_records(id) ON DELETE CASCADE
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS vaccination_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        vaccine_name VARCHAR(50) NOT NULL,
        dose_number INT DEFAULT 1,
        administered_date DATE NOT NULL,
        next_due_date DATE,
        vet_name VARCHAR(30),
        batch_number VARCHAR(30),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE CASCADE
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS drug_inventory (
        id INT AUTO_INCREMENT PRIMARY KEY,
        drug_name VARCHAR(50) NOT NULL,
        category VARCHAR(30),
        manufacturer VARCHAR(50),
        batch_number VARCHAR(30),
        quantity INT DEFAULT 0,
        unit VARCHAR(10) DEFAULT '瓶',
        unit_price DECIMAL(10,2),
        expiry_date DATE,
        storage_condition VARCHAR(50),
        min_stock_level INT DEFAULT 5,
        notes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS calendar_events (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(100) NOT NULL,
        event_date DATE NOT NULL,
        start_time VARCHAR(5) DEFAULT '09:00',
        end_time VARCHAR(5) DEFAULT '09:30',
        event_type VARCHAR(20) DEFAULT 'appointment',
        pet_id INT,
        pet_name VARCHAR(30),
        owner_name VARCHAR(30),
        medical_record_id INT,
        notes TEXT,
        status VARCHAR(20) DEFAULT 'scheduled',
        color VARCHAR(7) DEFAULT '#2563eb',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE SET NULL
    )""")
