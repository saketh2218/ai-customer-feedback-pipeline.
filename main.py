import sys
from mock_feedback_scraper import scrape_reviews
from llm_sentiment_enricher import enrich_reviews_with_ai
from database_handler import init_database, insert_feedback_data, run_analytical_summaries
from excel_dashboard_generator import generate_excel_dashboard

def run_pipeline():
    """
    Executes the complete End-to-End ETL pipeline:
    1. Scrapes raw reviews.
    2. Enriches with AI (Sentiment, Classification, Actions).
    3. Stores in SQL Database.
    4. Executes Analytical Queries.
    5. Generates Excel Dashboard & Visualizations.
    """
    print("="*60)
    print("STARTING AI-POWERED CUSTOMER FEEDBACK ANALYTICS PIPELINE")
    print("="*60)
    
    # Step 1: Initialize Database Tables
    init_database()
    print("-" * 40)
    
    # Step 2: Extract (Scrape raw reviews)
    raw_reviews = scrape_reviews(num_reviews=60)
    print("-" * 40)
    
    # Step 3: Transform (Enrich reviews with Sentiment & Category via LLM logic)
    enriched_data = enrich_reviews_with_ai(raw_reviews)
    print("-" * 40)
    
    # Step 4: Load (Insert enriched data into SQLite)
    insert_feedback_data(enriched_data)
    print("-" * 40)
    
    # Step 5: Query (Execute Analytical Aggregations)
    df_cat_summary, df_neg_actions = run_analytical_summaries()
    
    print("\n--- [Analytics Output: Category Summaries] ---")
    print(df_cat_summary.to_string(index=False))
    
    print(f"\n--- [Analytics Output: Top 5 Critical Action Items] ---")
    print(df_neg_actions.head(5)[["review_id", "feedback_category", "rating", "suggested_action"]].to_string(index=False))
    print("-" * 40)
    
    # Step 6: Visualize & Export (Excel Sheet Generation)
    generate_excel_dashboard()
    
    print("="*60)
    print("PIPELINE EXECUTION COMPLETE! EXCEL DASHBOARD GENERATED.")
    print("="*60)

if __name__ == "__main__":
    run_pipeline()
