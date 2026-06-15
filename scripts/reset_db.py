#!/usr/bin/env python3
"""
Reset all database tables for a fresh start.
Run from the project root: python scripts/reset_db.py

Truncates: calls, call_metrics, asterisk_cdr, system_log, caller_preferences
"""

import os
import sys

import pymysql

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "asterisk"))
from agi_lib.config import DB_CONFIG

TABLES = [
    "call_metrics",
    "calls",
    "asterisk_cdr",
    "system_log",
    "caller_preferences",
]


def reset():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in TABLES:
                cur.execute(f"TRUNCATE TABLE `{table}`")
                print(f"  [ok] truncated {table}")
            cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        print("\nDatabase reset complete. All tables are empty.")
    finally:
        conn.close()


if __name__ == "__main__":
    confirm = input("This will delete ALL data. Type 'yes' to continue: ")
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        sys.exit(0)
    reset()
