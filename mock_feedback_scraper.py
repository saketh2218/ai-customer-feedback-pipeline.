import random
import time
from datetime import datetime, timedelta

def scrape_reviews(num_reviews=50):
    """
    Simulates scraping customer reviews from various sources (Google Reviews, Trustpilot, App Store).
    Returns a list of raw review dictionaries.
    """
    print(f"[Scraper] Initializing scraper for {num_reviews} reviews...")
    time.sleep(0.5) # Simulate connection delay

    sources = ["Google Reviews", "Trustpilot", "App Store"]
    
    # Realistic product features that clients might comment on
    positive_comments = [
        "The interface is so clean and easy to navigate! Saved me hours.",
        "Excellent customer support. They resolved my login issue in 5 minutes.",
        "Very fast loading times compared to the competitors.",
        "Love the new updates, the dashboards are incredibly intuitive.",
        "A game-changer for our weekly workflow management.",
        "Great value for money. Highly recommended.",
        "Clean design and very responsive on mobile.",
        "The search feature is blazing fast now."
    ]
    
    negative_comments = [
        "It lags heavily when trying to export large datasets. Fix this!",
        "Customer service took 3 days to respond to my query. Frustrating.",
        "The pricing model is way too expensive for small businesses.",
        "The app crashed twice today while saving my settings.",
        "Confusing UI design. Hard to find where the settings are.",
        "Missing a dark mode option, it hurts my eyes at night.",
        "The latest update broke my integration. Disappointed.",
        "Too many notification popups. Let us turn them off."
    ]
    
    neutral_comments = [
        "It does the job, but it is nothing special.",
        "Decent app, but needs more documentation on advanced features.",
        "Average experience, could use some UI improvements.",
        "It is okay, but I prefer the old layout.",
        "Standard features. Works as expected."
    ]

    reviews = []
    
    for i in range(num_reviews):
        source = random.choice(sources)
        # Weight towards positive reviews for a realistic product distribution
        sentiment_type = random.choices(["pos", "neu", "neg"], weights=[0.6, 0.15, 0.25])[0]
        
        if sentiment_type == "pos":
            text = random.choice(positive_comments)
            rating = random.randint(4, 5)
        elif sentiment_type == "neg":
            text = random.choice(negative_comments)
            rating = random.randint(1, 2)
        else:
            text = random.choice(neutral_comments)
            rating = 3
            
        # Add random customer names
        first_names = ["John", "Sarah", "Emily", "Michael", "David", "Jessica", "Robert", "Ashley", "Daniel", "Amanda"]
        last_names = ["Smith", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor"]
        customer_name = f"{random.choice(first_names)} {random.choice(last_names)[0]}."
        
        # Add a date within the last 30 days
        days_ago = random.randint(0, 30)
        review_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        reviews.append({
            "review_id": f"REV_{1000 + i}",
            "customer_name": customer_name,
            "source": source,
            "rating": rating,
            "review_text": text,
            "review_date": review_date
        })
        
    print(f"[Scraper] Successfully scraped {len(reviews)} reviews from {len(sources)} sources.")
    return reviews

if __name__ == "__main__":
    # Test execution
    sample_data = scrape_reviews(5)
    for review in sample_data:
        print(review)
