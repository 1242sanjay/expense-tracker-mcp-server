from fastmcp import FastMCP
import os
import aiosqlite
"""
    Changed: sqlite3 --> aiosqlite
    Reason: aiosqlite is an async and non-blocking, works with asyncio.
    sqlite3 is synchronous and blocks execution until the database operation is complete.
"""

HOME_DIR = os.path.expanduser("~")
APP_DIR = os.path.join(HOME_DIR, ".expense_tracker")
os.makedirs(APP_DIR, exist_ok=True)

DB_PATH = os.path.join(APP_DIR, "expense.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("Expense Tracker")

def init_db():
    """
        Initialize the database once at startup.
        Using sqlite3 synchronously here is fine since it's a quick one-time setup. 
        Runtime operations use aiosqlite for async interaction.
    """
    try:
        import sqlite3
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # Enable Write-Ahead Logging for better concurrency
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
            # Test write access by inserting a dummy record
            conn.execute("INSERT INTO expenses (date, amount, category) VALUES ('1970-01-01', 0, 'test')")
            conn.execute("DELETE FROM expenses WHERE category = 'test'")
            print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# Initialize the database synchronously at module load.
init_db()

@mcp.tool()
async def add_expense(date: str, amount: float, category: str, subcategory: str = "", description: str = ""):
    """Add a new expense to the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.execute("""
                INSERT INTO expenses (date, amount, category, subcategory, description)
                VALUES (?, ?, ?, ?, ?)
            """, (date, amount, category, subcategory, description))
            await conn.commit()
            return {"Status":"Ok", "id": cursor.lastrowid}
    except Exception as e:
        if "readonly" in str(e).lower():
            return {"Status":"Error", "message": "Database is read-only. Please check file permissions."}
        return {"Status":"Error", "message": f"Database error: {str(e)}"}

@mcp.tool()
async def list_expenses():
    """List all expenses in the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            cursor = await conn.execute("SELECT id, date, amount, category, subcategory, description FROM expenses")
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        return {"Status":"Error", "message": f"Error while listing expenses: {str(e)}"}

@mcp.tool()
async def summerize(start_date: str, end_date: str, category: str = None):
    """Summarize expenses by categories within and inclusive date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            query = """
                SELECT category, sum(amount) as total_amount
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]
            if category:
                query += " AND category = ?"
                params.append(category)
            query += "Group BY category ORDER BY category ASC"
            cursor = await conn.execute(query, params)
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in await cursor.fetchall()]
    except Exception as e:
        return {"Status":"Error", "message": f"Error while summarizing expenses: {str(e)}"}
    
@mcp.tool()
async def update_expense(id: int, date: str = None, amount: float = None, category: str = None, subcategory: str = None, description: str = None):
    """Update an existing expense by ID."""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            fields = []
            params = []
            if date is not None:
                fields.append("date = ?")
                params.append(date)
            if amount is not None:
                fields.append("amount = ?")
                params.append(amount)
            if category is not None:
                fields.append("category = ?")
                params.append(category)
            if subcategory is not None:
                fields.append("subcategory = ?")
                params.append(subcategory)
            if description is not None:
                fields.append("description = ?")
                params.append(description)
            if not fields:
                return {"Status":"Error", "message": "No fields to update."}
            params.append(id)
            query = f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?"
            await conn.execute(query, params)
            await conn.commit()
            return {"Status":"Ok", "message": f"Expense with ID {id} updated successfully."}
    except Exception as e:
        return {"Status":"Error", "message": f"Error while updating expense: {str(e)}"}

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """Read fresh each time so you can edit the file without restarting the server."""
    try:
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return {"Status":"Error", "message": f"Error while loading categories: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
