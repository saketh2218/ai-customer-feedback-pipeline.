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
            suggested_action TEXT
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
                review_date, sentiment_class, sentiment_score, feedback_category, suggested_action
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["review_id"],
            item["customer_name"],
            item["source"],
            item["rating"],
            item["review_text"],
            item["review_date"],
            item["sentiment_class"],
            item["sentiment_score"],
            item["feedback_category"],
            item["suggested_action"]
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

if __name__ == "__main__":
    init_database()
