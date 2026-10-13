import pytest
from fastapi.testclient import TestClient
import database_handler as db
import llm_sentiment_enricher as enricher
from api import app

client = TestClient(app)

def test_heuristic_enrichment_positive():
    review = {
        "review_id": "TEST_POS",
        "review_text": "The interface is so clean and easy to use!",
        "rating": 5,
        "source": "Web",
        "customer_name": "Test User",
        "review_date": "2026-10-11"
    }
    result = enricher._heuristic_enrich(review)
    assert result["sentiment_class"] == "Positive"
    assert result["sentiment_score"] > 0
    assert result["feedback_category"] == "UI/UX"
    assert result["is_conflicted"] is False
    assert result["confidence_score"] >= 0.8

def test_heuristic_enrichment_negative_and_action():
    review = {
        "review_id": "TEST_NEG",
        "review_text": "It lags heavily when exporting data.",
        "rating": 1,
        "source": "Web",
        "customer_name": "Test User",
        "review_date": "2026-10-11"
    }
    result = enricher._heuristic_enrich(review)
    assert result["sentiment_class"] == "Negative"
    assert result["sentiment_score"] < 0
    assert result["feedback_category"] == "Performance"
    assert "Optimize" in result["suggested_action"]
    assert result["is_conflicted"] is False

def test_incongruence_anomaly_detection():
    # 1 star rating with forced positive wording
    is_conflicted = enricher._check_incongruence(rating=1, sentiment_class="Positive")
    assert is_conflicted is True

    # 5 star rating with negative sentiment
    is_conflicted = enricher._check_incongruence(rating=5, sentiment_class="Negative")
    assert is_conflicted is True

    # 5 star with positive sentiment
    is_conflicted = enricher._check_incongruence(rating=5, sentiment_class="Positive")
    assert is_conflicted is False

def test_database_operations_and_hitl():
    db.init_database()
    sample_records = [{
        "review_id": "REV_HITL_TEST",
        "customer_name": "Alex",
        "source": "Google",
        "rating": 1,
        "review_text": "Sarcastic compliment: Great job making it unusable!",
        "review_date": "2026-10-11",
        "sentiment_class": "Positive", # Incorrectly classified by AI
        "sentiment_score": 0.8,
        "feedback_category": "General",
        "suggested_action": "Investigate review.",
        "confidence_score": 0.40,
        "evidence_quote": "Great job",
        "is_conflicted": True,
        "human_verified": False
    }]
    db.insert_feedback_data(sample_records)
    
    # Query conflicted records
    conflicted = db.get_feedback_records(conflicted_only=True)
    assert any(r["review_id"] == "REV_HITL_TEST" for r in conflicted)

    # Apply Human-in-the-Loop Override
    db.update_feedback_label("REV_HITL_TEST", "Negative", -0.85)
    
    # Verify it has been updated and resolved
    records = db.get_feedback_records(conflicted_only=False)
    updated = next(r for r in records if r["review_id"] == "REV_HITL_TEST")
    assert updated["sentiment_class"] == "Negative"
    assert updated["human_verified"] == 1
    assert updated["is_conflicted"] == 0

def test_fastapi_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "llm_engine" in data

def test_fastapi_analyze_endpoint():
    payload = {
        "review_text": "The billing and pricing is way too expensive.",
        "rating": 2,
        "customer_name": "Sarah T.",
        "source": "Trustpilot"
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["sentiment_class"] == "Negative"
    assert data["data"]["feedback_category"] == "Pricing"
