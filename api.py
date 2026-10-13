import os
import io
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import database_handler as db
import llm_sentiment_enricher as enricher
from excel_dashboard_generator import generate_excel_dashboard

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database is initialized on startup
    db.init_database()
    yield

app = FastAPI(
    title="Customer Feedback & Sentiment Analytics API",
    description="Production-grade API for automated sentiment enrichment, anomaly detection, SQL analytics, and Human-in-the-Loop audits.",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewInput(BaseModel):
    review_text: str = Field(..., json_schema_extra={"example": "The interface is clean, but export times are very slow."})
    rating: int = Field(3, ge=1, le=5, json_schema_extra={"example": 3})
    customer_name: Optional[str] = Field("Anonymous", json_schema_extra={"example": "Alex Rivera"})
    source: Optional[str] = Field("Web", json_schema_extra={"example": "App Store"})


class BatchReviewInput(BaseModel):
    reviews: List[ReviewInput]
    save_to_database: bool = True


class AuditOverrideInput(BaseModel):
    review_id: str
    corrected_class: str = Field(..., pattern="^(Positive|Neutral|Negative)$")
    notes: Optional[str] = ""


@app.get("/health", tags=["Monitoring"])
def health_check():
    """
    Production health check & readiness probe.
    """
    api_key_set = bool(os.environ.get("OPENAI_API_KEY"))
    return {
        "status": "healthy",
        "service": "customer-sentiment-review-pipeline",
        "version": "2.0.0",
        "llm_engine": "OpenAI " + enricher.LLM_MODEL if api_key_set and enricher._OPENAI_AVAILABLE else "deterministic-heuristic",
        "timestamp": time.time()
    }


@app.post("/api/analyze", tags=["Inference"])
def analyze_review(payload: ReviewInput):
    """
    Analyzes a single customer review in real-time.
    Returns sentiment, polarity score, confidence score, category, evidence quote, and anomaly conflict status.
    """
    result = enricher.analyze_single_review(
        review_text=payload.review_text,
        rating=payload.rating,
        customer_name=payload.customer_name or "Anonymous",
        source=payload.source or "Web"
    )
    return {
        "success": True,
        "data": result
    }


@app.post("/api/batch-analyze", tags=["Inference"])
def batch_analyze_reviews(payload: BatchReviewInput):
    """
    Enriches a batch of customer reviews. Optionally ingests directly into SQLite database.
    """
    raw_dicts = []
    for idx, item in enumerate(payload.reviews):
        raw_dicts.append({
            "review_id": f"REV_{int(time.time())}_{idx}",
            "customer_name": item.customer_name or "Anonymous",
            "source": item.source or "Batch Upload",
            "rating": item.rating,
            "review_text": item.review_text,
            "review_date": time.strftime("%Y-%m-%d"),
        })

    enriched = enricher.enrich_reviews_with_ai(raw_dicts)

    if payload.save_to_database:
        db.insert_feedback_data(enriched)

    return {
        "success": True,
        "count": len(enriched),
        "data": enriched
    }


@app.get("/api/metrics", tags=["Analytics"])
def get_metrics():
    """
    Queries SQL analytics: category breakdown and critical negative items.
    """
    try:
        df_summary, df_neg = db.run_analytical_summaries()
        return {
            "categories": df_summary.to_dict(orient="records"),
            "critical_actions": df_neg.head(10).to_dict(orient="records")
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/audit-queue", tags=["Human-in-the-Loop"])
def get_audit_queue(conflicted_only: bool = True, limit: int = 50):
    """
    Fetches reviews that have been flagged as conflicted (rating vs sentiment incongruence)
    or low confidence, ready for human auditor sign-off.
    """
    items = db.get_feedback_records(limit=limit, conflicted_only=conflicted_only)
    return {
        "count": len(items),
        "queue": items
    }


@app.post("/api/audit/override", tags=["Human-in-the-Loop"])
def override_label(payload: AuditOverrideInput):
    """
    Allows a human reviewer to override or approve an anomalous sentiment classification.
    """
    success = db.update_feedback_label(
        review_id=payload.review_id,
        corrected_class=payload.corrected_class,
        notes=payload.notes
    )
    if not success:
        raise HTTPException(status_code=404, detail="Review ID not found")
    return {
        "success": True,
        "message": f"Review {payload.review_id} updated to {payload.corrected_class} with human verification flag."
    }


@app.get("/api/export/excel", tags=["Reporting"])
def export_excel():
    """
    Triggers automated Excel generation with KPI blocks and embedded visualizations,
    then returns the spreadsheet file for download.
    """
    try:
        generate_excel_dashboard()
        excel_path = "customer_feedback_insights.xlsx"
        if not os.path.exists(excel_path):
            raise HTTPException(status_code=500, detail="Excel file could not be generated")
        return FileResponse(
            excel_path,
            filename="customer_feedback_insights.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
