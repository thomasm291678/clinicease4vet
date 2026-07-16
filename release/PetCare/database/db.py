"""数据库连接与初始化（SQLite 本地版）"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "max_hospitals.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS pet_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, species TEXT NOT NULL,
        breed TEXT, gender TEXT, age_months INTEGER, weight_kg REAL, color TEXT,
        owner_name TEXT NOT NULL, owner_contact TEXT, owner_address TEXT,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS vet_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, specialisation TEXT,
        license_no TEXT, age INTEGER, address TEXT, contact TEXT,
        consultation_fee INTEGER, monthly_salary INTEGER
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS assistant_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT,
        age INTEGER, address TEXT, contact TEXT, monthly_salary INTEGER
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS other_workers_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, role TEXT,
        age INTEGER, address TEXT, contact TEXT, monthly_salary INTEGER
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS user_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, role TEXT DEFAULT 'staff'
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS medical_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pet_id INTEGER NOT NULL,
        vet_name TEXT, visit_date TEXT NOT NULL, diagnosis TEXT, treatment TEXT,
        symptoms TEXT, subjective TEXT, objective TEXT, assessment TEXT,
        plan TEXT, clinical_reasoning_data TEXT, notes TEXT, follow_up_date TEXT,
        fee_charged INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE CASCADE
    )""")
    for col in ("symptoms", "subjective", "objective", "assessment", "plan", "clinical_reasoning_data"):
        try: cursor.execute(f"ALTER TABLE medical_records ADD COLUMN {col} TEXT")
        except: pass
    cursor.execute("""CREATE TABLE IF NOT EXISTS clinical_reasoning (
        id INTEGER PRIMARY KEY AUTOINCREMENT, record_id INTEGER NOT NULL,
        problem_list TEXT, reasoning_path TEXT, differential_list TEXT,
        must_not_miss TEXT, missing_info TEXT, recommended_tests TEXT,
        dynamic_questions TEXT, client_communication TEXT, summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (record_id) REFERENCES medical_records(id) ON DELETE CASCADE
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS vaccination_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pet_id INTEGER NOT NULL,
        vaccine_name TEXT NOT NULL, dose_number INTEGER DEFAULT 1,
        administered_date TEXT NOT NULL, next_due_date TEXT, vet_name TEXT,
        batch_number TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE CASCADE
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS drug_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT, drug_name TEXT NOT NULL, category TEXT,
        manufacturer TEXT, batch_number TEXT, quantity INTEGER DEFAULT 0,
        unit TEXT DEFAULT '瓶', unit_price REAL, expiry_date TEXT,
        storage_condition TEXT, min_stock_level INTEGER DEFAULT 5, notes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    cursor.close()
    conn.close()
    print("数据库初始化完成。")
