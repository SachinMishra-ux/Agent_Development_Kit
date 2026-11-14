"""Sample vulnerable service for static code analysis & security testing."""

import os
import sqlite3

# VULNERABILITY 1: Hardcoded credentials
API_SECRET_KEY = "sk-live-938472918237491823749812739"
ADMIN_PASSWORD = "SuperSecretPassword123!"


def authenticate_user(username: str, query_filter: str):
    """VULNERABILITY 2: SQL Injection via string formatting."""
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # Flawed: concatenated / formatted query
    sql = f"SELECT * FROM users WHERE username = '{username}' AND role = '{query_filter}'"
    cursor.execute(sql)
    return cursor.fetchall()


def execute_dynamic_rule(rule_expression: str, context: dict):
    """VULNERABILITY 3: Dangerous arbitrary code execution via eval()."""
    # Flawed: evaluating untrusted string
    try:
        return eval(rule_expression, {}, context)
    except:  # VULNERABILITY 4: Bare except clause
        pass
    return False
