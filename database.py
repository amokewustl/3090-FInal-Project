import sqlite3
import json
import numpy as np
from datetime import datetime
import pytz 
from Plans import neutral_plans, hearts_representative_plans

DB_PATH = 'instance/redistricting.db'
ST_LOUIS_TZ = pytz.timezone('America/Chicago')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    import os
    os.makedirs('instance', exist_ok=True)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            districts TEXT NOT NULL,
            type TEXT NOT NULL,
            user_name TEXT,
            is_base INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if base plans already exist
    cursor.execute('SELECT COUNT(*) FROM plans WHERE is_base = 1')
    base_count = cursor.fetchone()[0]
    
    if base_count == 0:
        # Insert base neutral plans (plans 1-10)
        for i, plan in enumerate(neutral_plans):
            districts_json = json.dumps(plan.tolist())
            cursor.execute(
                'INSERT INTO plans (districts, type, user_name, is_base) VALUES (?, ?, ?, ?)',
                (districts_json, 'neutral', f'Base Plan {i+1}', 1)
            )
        
        # Insert base hearts representative plans (plans 11-20)
        for i, plan in enumerate(hearts_representative_plans):
            districts_json = json.dumps(plan.tolist())
            cursor.execute(
                'INSERT INTO plans (districts, type, user_name, is_base) VALUES (?, ?, ?, ?)',
                (districts_json, 'hearts_representative', f'Base Plan {i+11}', 1)
            )
        
        print(f"Initialized database with {len(neutral_plans) + len(hearts_representative_plans)} base plans")
    
    conn.commit()
    conn.close()

def add_user_plan(districts, plan_type, user_name='Anonymous'):
    """Add a user-submitted plan with St. Louis CST timezone"""
    conn = get_db()
    cursor = conn.cursor()
    st_louis_time = datetime.now(ST_LOUIS_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    districts_json = json.dumps(districts)
    cursor.execute(
        'INSERT INTO plans (districts, type, user_name, is_base, created_at) VALUES (?, ?, ?, ?, ?)',
        (districts_json, plan_type, user_name, 0, st_louis_time)
    )
    
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return plan_id

def get_all_plans():
    """Get all plans (base + user)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM plans ORDER BY is_base DESC, id ASC')
    rows = cursor.fetchall()
    conn.close()
    
    plans = []
    for row in rows:
        plans.append({
            'id': row['id'],
            'districts': json.loads(row['districts']),
            'type': row['type'],
            'user_name': row['user_name'],
            'is_base': bool(row['is_base']),
            'created_at': row['created_at']
        })
    
    return plans

def get_user_plans():
    """Get only user-submitted plans (not base plans) with CST display"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM plans WHERE is_base = 0 ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    plans = []
    for row in rows:
        created_at = row['created_at']
        
        plans.append({
            'id': row['id'],
            'districts': json.loads(row['districts']),
            'type': row['type'],
            'user_name': row['user_name'],
            'created_at': created_at
        })
    
    return plans

def delete_user_plan(plan_id):
    """Delete a user plan (cannot delete base plans)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if it's a user plan
    cursor.execute('SELECT is_base FROM plans WHERE id = ?', (plan_id,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        return False
    
    if row['is_base'] == 1:
        conn.close()
        return False  # Cannot delete base plans
    
    cursor.execute('DELETE FROM plans WHERE id = ?', (plan_id,))
    conn.commit()
    conn.close()
    
    return True

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")