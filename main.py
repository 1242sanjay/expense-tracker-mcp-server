from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expense.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("Expense Tracker")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                description TEXT DEFAULT ''
            )
        """)

init_db()

@mcp.tool()
def add_expense(date: str, amount: float, category: str, subcategory: str = "", description: str = ""):
    """Add a new expense to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO expenses (date, amount, category, subcategory, description)
            VALUES (?, ?, ?, ?, ?)
        """, (date, amount, category, subcategory, description))
    return {"Status":"Ok", "id": conn.lastrowid}

@mcp.tool()
def list_expenses():
    """List all expenses in the database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT id, date, amount, category, subcategory, description FROM expenses")
        cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

@mcp.tool()
def summerize(start_date: str, end_date: str, category: str = None):
    """Summarize expenses by categories within and inclusive date range."""
    with sqlite3.connect(DB_PATH) as conn:
        query = """
            SELECT id, date, amount, category, subcategory, description
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += "Group BY category ORDER BY category ASC"
        cursor = conn.execute(query, params)
        cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """Read fresh each time so you can edit the file without restarting the server."""
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run()
