"""数据库连接与初始化 (SQLite 离线版)"""

import sqlite3
import os
from config import Config

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clinicease.db")


def get_connection():
    """获取 SQLite 数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """创建数据库和所有表（如果不存在）"""
    conn = get_connection()
    cursor = conn.cursor()

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

    conn.commit()
    cursor.close()
    conn.close()
