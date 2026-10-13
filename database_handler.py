import sqlite3
import pandas as pd

DB_NAME = "feedback_analytics.db"

def init_database():
    """
    Initializes the SQLite database and creates the necessary tables.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Drop existing table if we want a fresh run
    cursor.execute("DROP TABLE IF EXISTS customer_feedback")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_feedback (
            review_id TEXT PRIMARY KEY,
            customer_name TEXT,
            source TEXT,
            rating INTEGER,
            review_text TEXT,
            review_date DATE,
            sentiment_class TEXT,
            sentiment_score REAL,
            feedback_category TEXT,
            suggested_action TEXT,
            confidence_score REAL DEFAULT 0.85,
            evidence_quote TEXT DEFAULT '',
            is_conflicted INTEGER DEFAULT 0,
            human_verified INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"[Database] SQLite Database and 'customer_feedback' table initialized successfully.")

def insert_feedback_data(data):
    """
    Inserts enriched reviews into the SQLite database.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for item in data:
        cursor.execute("""
            INSERT OR REPLACE INTO customer_feedback (
                review_id, customer_name, source, rating, review_text, 
                review_date, sentiment_class, sentiment_score, feedback_category, suggested_action,
                confidence_score, evidence_quote, is_conflicted, human_verified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["review_id"],
            item.get("customer_name", "Anonymous"),
            item.get("source", "Web"),
            item["rating"],
            item["review_text"],
            item.get("review_date", "2026-10-11"),
            item["sentiment_class"],
            item["sentiment_score"],
            item["feedback_category"],
            item["suggested_action"],
            item.get("confidence_score", 0.85),
            item.get("evidence_quote", ""),
            1 if item.get("is_conflicted", False) else 0,
            1 if item.get("human_verified", False) else 0
        ))
        
    conn.commit()
    conn.close()
    print(f"[Database] Loaded {len(data)} records into the database.")

def query_database(sql_query):
    """
    Runs an SQL query and returns a Pandas DataFrame.
    Demonstrates integration of SQL query extraction into Python workflows.
    """
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(sql_query, conn)
    conn.close()
    return df

def run_analytical_summaries():
    """
    Runs advanced analytical queries on the feedback data to demonstrate SQL aggregates.
    """
    print("[Database] Running analytical SQL queries for business insights...")
    
    # Summary 1: Average rating and average sentiment score by product category
    q1 = """
        SELECT 
            feedback_category,
            COUNT(*) as total_feedback,
            ROUND(AVG(rating), 2) as avg_rating,
            ROUND(AVG(sentiment_score), 2) as avg_sentiment_score
        FROM customer_feedback
        GROUP BY feedback_category
        ORDER BY avg_rating DESC
    """
    
    # Summary 2: Action list for Negative items (critical items)
    q2 = """
        SELECT 
            review_id,
            feedback_category,
            rating,
            review_text,
            suggested_action
        FROM customer_feedback
        WHERE sentiment_class = 'Negative'
        ORDER BY rating ASC
    """
    
    df_cat_summary = query_database(q1)
    df_neg_actions = query_database(q2)
    
    return df_cat_summary, df_neg_actions

def update_feedback_label(review_id, corrected_class, corrected_score=None, notes=""):
    """
    Updates an anomalous or conflicted review with a human-verified ground-truth label.
    Part of the Human-in-the-Loop (HITL) quality control workflow.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if corrected_score is None:
        score_map = {"Positive": 0.8, "Neutral": 0.0, "Negative": -0.8}
        corrected_score = score_map.get(corrected_class, 0.0)
    
    cursor.execute("""
        UPDATE customer_feedback
        SET sentiment_class = ?,
            sentiment_score = ?,
            human_verified = 1,
            is_conflicted = 0
        WHERE review_id = ?
    """, (corrected_class, corrected_score, review_id))
    conn.commit()
    conn.close()
    return True

def get_feedback_records(limit=100, conflicted_only=False):
    """
    Fetches customer feedback records as a list of dicts.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM customer_feedback"
    if conflicted_only:
        query += " WHERE is_conflicted = 1"
    query += " ORDER BY review_date DESC LIMIT ?"
    cursor.execute(query, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_database()
