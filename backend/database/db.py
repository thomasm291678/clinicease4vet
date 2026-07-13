"""数据库连接与初始化"""

import mysql.connector
from config import Config


def get_connection():
    """获取 MySQL 数据库连接"""
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        passwd=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
    )


def init_database():
    """创建数据库和所有表（如果不存在）"""
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        passwd=Config.MYSQL_PASSWORD,
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DATABASE}")
    cursor.close()
    conn.close()

    conn = get_connection()
    cursor = conn.cursor()

    # ---------- 宠物信息表 ----------
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

    # ---------- 兽医信息表 ----------
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

    # ---------- 助理/护士表 ----------
    cursor.execute("""CREATE TABLE IF NOT EXISTS assistant_details (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(30) NOT NULL,
        role VARCHAR(30),
        age INT,
        address VARCHAR(50),
        contact VARCHAR(15),
        monthly_salary INT
    )""")

    # ---------- 其他员工表 ----------
    cursor.execute("""CREATE TABLE IF NOT EXISTS other_workers_details (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(30) NOT NULL,
        role VARCHAR(30),
        age INT,
        address VARCHAR(50),
        contact VARCHAR(15),
        monthly_salary INT
    )""")

    # ---------- 用户认证表（增加角色字段）----------
    cursor.execute("""CREATE TABLE IF NOT EXISTS user_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(30) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) DEFAULT 'staff'
    )""")

    # ---------- 诊疗记录表 ----------
    cursor.execute("""CREATE TABLE IF NOT EXISTS medical_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pet_id INT NOT NULL,
        vet_name VARCHAR(30),
        visit_date DATE NOT NULL,
        diagnosis TEXT,
        treatment TEXT,
        notes TEXT,
        follow_up_date DATE,
        fee_charged INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pet_id) REFERENCES pet_details(id) ON DELETE CASCADE
    )""")

    # ---------- 疫苗接种记录表 ----------
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

    # ---------- 药品库存表 ----------
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

    conn.commit()
    cursor.close()
    conn.close()
