import os
import sqlite3
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

import database_handler as db
import llm_sentiment_enricher as enricher
from mock_feedback_scraper import scrape_reviews
from excel_dashboard_generator import generate_excel_dashboard

st.set_page_config(
    page_title="AI Feedback & Sentiment Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #1F4E78;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .badge-pos {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .badge-neg {
        background-color: #f8d7da;
        color: #721c24;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .badge-neu {
        background-color: #fff3cd;
        color: #856404;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .badge-conflict {
        background-color: #fce8e6;
        color: #c5221f;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        border: 1px solid #fad2cf;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🛠️ Control Panel")
api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
st.sidebar.markdown(f"**LLM Mode:** {'🟢 OpenAI Live (GPT-4o-mini)' if api_key_present else '🟡 Deterministic Heuristic Fallback'}")
st.sidebar.caption("When no OPENAI_API_KEY is detected, pipeline runs with zero crash risk via deterministic rule validation.")

st.sidebar.divider()
st.sidebar.subheader("Quick Actions")
if st.sidebar.button("🔄 Reset / Initialize SQLite DB"):
    db.init_database()
    st.sidebar.success("Database initialized!")

if st.sidebar.button("📥 Generate Excel Dashboard"):
    generate_excel_dashboard()
    st.sidebar.success("Excel generated!")
    if os.path.exists("customer_feedback_insights.xlsx"):
        with open("customer_feedback_insights.xlsx", "rb") as f:
            st.sidebar.download_button(
                "⬇️ Download customer_feedback_insights.xlsx",
                data=f,
                file_name="customer_feedback_insights.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# Main Title
st.title("🎯 AI-Powered Customer Sentiment Review & Analytics Pipeline")
st.markdown("Production-grade ETL pipeline with **Multi-Engine Sentiment Analysis**, **Anomaly Detection**, **Explainability Evidence Extraction**, and **Human-in-the-Loop (HITL) Quality Control**.")

tabs = st.tabs([
    "🔍 Live Review Inspector",
    "📁 Batch Ingestion & ETL",
    "📈 SQL Analytics & KPIs",
    "🛡️ HITL Audit & Verification",
    "💡 Technical Interview Guide"
])

# ----------------- TAB 1: LIVE REVIEW INSPECTOR -----------------
with tabs[0]:
    st.subheader("Real-Time Sentiment Inference & Anomaly Detection")
    st.write("Test individual customer feedback reviews in real-time to observe the model's confidence, evidence extraction, and contradiction checks.")
    
    col1, col2 = st.columns([1.2, 0.8])
    with col1:
        sample_reviews = [
            "The interface is so clean and easy to navigate! Saved me hours.",
            "It lags heavily when trying to export large datasets. Fix this!",
            "Terrible app, crashes every time I open it, worst purchase ever.",
            "Customer service took 3 days to respond to my query. Frustrating.",
            "The search feature is blazing fast now, great job team!",
            "Decent app, but needs more documentation on advanced features."
        ]
        selected_sample = st.selectbox("Load sample review (optional):", ["-- Select a sample --"] + sample_reviews)
        
        default_text = selected_sample if selected_sample != "-- Select a sample --" else "The software is remarkably fast and intuitive, but the billing page is confusing."
        review_text = st.text_area("Customer Review Text", value=default_text, height=110)
        
        c_sub1, c_sub2, c_sub3 = st.columns(3)
        with c_sub1:
            rating = st.slider("Star Rating (1-5)", min_value=1, max_value=5, value=4)
        with c_sub2:
            customer_name = st.text_input("Customer Name", value="Jordan Lee")
        with c_sub3:
            source = st.selectbox("Platform Source", ["Trustpilot", "Google Reviews", "App Store", "Direct Support"])
            
        analyze_btn = st.button("🚀 Analyze Sentiment & Validate", type="primary")

    with col2:
        if analyze_btn:
            with st.spinner("Analyzing review semantics and cross-checking anomalies..."):
                res = enricher.analyze_single_review(
                    review_text=review_text,
                    rating=rating,
                    customer_name=customer_name,
                    source=source
                )
                
                st.markdown("#### Analysis Results")
                sentiment = res["sentiment_class"]
                score = res["sentiment_score"]
                conf = res["confidence_score"]
                cat = res["feedback_category"]
                action = res["suggested_action"]
                evidence = res["evidence_quote"]
                conflicted = res["is_conflicted"]
                
                # Badge styling
                badge_class = "badge-pos" if sentiment == "Positive" else ("badge-neg" if sentiment == "Negative" else "badge-neu")
                st.markdown(f"**Predicted Sentiment:** <span class='{badge_class}'>{sentiment}</span> (Score: `{score}`)", unsafe_allow_html=True)
                
                st.progress(conf, text=f"Model Confidence: {int(conf * 100)}%")
                
                st.markdown(f"**Product Category:** `{cat}`")
                st.markdown(f"**Evidence Excerpt:** *\"{evidence}\"*")
                st.info(f"💡 **Suggested Action Item:** {action}")
                
                if conflicted:
                    st.error("⚠️ **Contradiction Alert:** Star rating conflicts with sentiment polarity (e.g., 1-2 stars marked Positive or 4-5 stars marked Negative). This review is automatically flagged for Human-in-the-Loop review.")
                else:
                    st.success("✅ **Congruence Check Passed:** Star rating and linguistic polarity are aligned.")
                    
                # Option to save to database
                if st.button("💾 Save this review to Database"):
                    db.insert_feedback_data([res])
                    st.success("Review stored in SQLite database!")

# ----------------- TAB 2: BATCH INGESTION & ETL -----------------
with tabs[1]:
    st.subheader("Batch Review Extraction & Ingestion Pipeline")
    st.write("Run simulated multi-source scrapers or upload your own CSV dataset.")
    
    col_b1, col_b2 = st.columns([1, 1])
    with col_b1:
        st.markdown("##### Option A: Simulated Scraping")
        num_to_scrape = st.slider("Number of synthetic reviews to scrape:", min_value=10, max_value=120, value=50, step=10)
        if st.button("🕷️ Scrape & Run Complete Pipeline"):
            with st.spinner("Extracting, enriching, loading into SQLite, and compiling Excel..."):
                scraped = scrape_reviews(num_reviews=num_to_scrape)
                enriched = enricher.enrich_reviews_with_ai(scraped)
                db.insert_feedback_data(enriched)
                generate_excel_dashboard()
                st.success(f"Successfully processed and stored {len(enriched)} reviews into SQLite!")
                st.rerun()

    with col_b2:
        st.markdown("##### Option B: Upload Custom CSV")
        uploaded_file = st.file_uploader("Upload CSV (Requires 'review_text' & 'rating' columns)", type=["csv"])
        if uploaded_file is not None:
            df_up = pd.read_csv(uploaded_file)
            st.dataframe(df_up.head(4), use_container_width=True)
            if st.button("⚡ Enrich Uploaded CSV"):
                items = []
                for idx, row in df_up.iterrows():
                    items.append({
                        "review_id": f"CSV_{idx+1}",
                        "customer_name": str(row.get("customer_name", "Anonymous")),
                        "source": str(row.get("source", "CSV Import")),
                        "rating": int(row.get("rating", 3)),
                        "review_text": str(row.get("review_text", "")),
                        "review_date": str(row.get("review_date", "2026-10-11")),
                    })
                enriched = enricher.enrich_reviews_with_ai(items)
                db.insert_feedback_data(enriched)
                st.success(f"Enriched and stored {len(enriched)} reviews from uploaded CSV!")
                st.rerun()

# ----------------- TAB 3: SQL ANALYTICS & KPIS -----------------
with tabs[2]:
    st.subheader("SQL Business Intelligence & KPI Summary")
    try:
        conn = sqlite3.connect(db.DB_NAME)
        df_all = pd.read_sql_query("SELECT * FROM customer_feedback", conn)
        conn.close()
    except Exception:
        df_all = pd.DataFrame()
        
    if df_all.empty:
        st.warning("No records found in database. Run the pipeline in Tab 2 or click 'Reset / Initialize SQLite DB'.")
    else:
        # Top KPI Cards
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("Total Reviews", len(df_all))
        with kpi2:
            st.metric("Avg Rating", f"{df_all['rating'].mean():.2f} / 5.0")
        with kpi3:
            st.metric("Net Sentiment Score", f"{df_all['sentiment_score'].mean():.2f}")
        with kpi4:
            conflicted_cnt = len(df_all[df_all['is_conflicted'] == 1])
            st.metric("Contradiction Flags", conflicted_cnt, delta="Requires Audit" if conflicted_cnt > 0 else "Clean", delta_color="inverse")
            
        st.divider()
        
        # Charts Row
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("##### Feedback by Product Category")
            cat_counts = df_all["feedback_category"].value_counts()
            fig1, ax1 = plt.subplots(figsize=(6, 3.5))
            sns.barplot(x=cat_counts.values, y=cat_counts.index, palette="Blues_r", ax=ax1)
            ax1.set_xlabel("Count")
            st.pyplot(fig1)
            plt.close()
            
        with col_c2:
            st.markdown("##### Sentiment Distribution")
            sent_counts = df_all["sentiment_class"].value_counts()
            fig2, ax2 = plt.subplots(figsize=(6, 3.5))
            colors = ["#4CAF50", "#F44336", "#FFC107"]
            ax2.pie(sent_counts, labels=sent_counts.index, autopct='%1.1f%%',
                    colors=[colors[i % 3] for i in range(len(sent_counts))], startangle=140)
            st.pyplot(fig2)
            plt.close()
            
        # Critical Action Items
        st.markdown("##### 🚨 Critical Negative Action Items for Product & Support Teams")
        neg_df = df_all[df_all["sentiment_class"] == "Negative"][["review_id", "rating", "feedback_category", "review_text", "suggested_action"]]
        st.dataframe(neg_df.head(10), use_container_width=True)
        
        # Download Data
        csv_data = df_all.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Full Enriched Dataset (CSV)", csv_data, "enriched_customer_feedback.csv", "text/csv")

# ----------------- TAB 4: HITL AUDIT & VERIFICATION -----------------
with tabs[3]:
    st.subheader("🛡️ Human-in-the-Loop (HITL) Quality Control Queue")
    st.write("Never blindly trust an AI model. Reviews with detected rating-sentiment discrepancies or low confidence are routed here for human audit.")
    
    try:
        conflicted_items = db.get_feedback_records(limit=25, conflicted_only=True)
    except Exception:
        conflicted_items = []
        
    if not conflicted_items:
        st.success("🎉 No conflicted or contradictory reviews currently in the audit queue! All predictions pass consistency checks.")
    else:
        st.warning(f"Found {len(conflicted_items)} reviews flagged with contradictory signals.")
        for item in conflicted_items:
            with st.expander(f"Review ID: {item['review_id']} | Rating: {item['rating']} Stars | Current AI Class: {item['sentiment_class']}"):
                st.write(f"**Review Text:** \"{item['review_text']}\"")
                st.write(f"**Current Action:** {item['suggested_action']}")
                st.write(f"**Evidence:** {item.get('evidence_quote', 'N/A')}")
                
                st.markdown("**Override Ground Truth Label:**")
                col_o1, col_o2, col_o3 = st.columns(3)
                if col_o1.button("Mark as Positive", key=f"pos_{item['review_id']}"):
                    db.update_feedback_label(item['review_id'], "Positive", 0.8)
                    st.success(f"Updated {item['review_id']} to Positive!")
                    st.rerun()
                if col_o2.button("Mark as Neutral", key=f"neu_{item['review_id']}"):
                    db.update_feedback_label(item['review_id'], "Neutral", 0.0)
                    st.success(f"Updated {item['review_id']} to Neutral!")
                    st.rerun()
                if col_o3.button("Mark as Negative", key=f"neg_{item['review_id']}"):
                    db.update_feedback_label(item['review_id'], "Negative", -0.8)
                    st.success(f"Updated {item['review_id']} to Negative!")
                    st.rerun()

# ----------------- TAB 5: TECHNICAL INTERVIEW GUIDE -----------------
with tabs[4]:
    st.subheader("💡 Interview Preparation: Core Questions & Authoritative Answers")
    st.markdown("""
### 1. How do you know the sentiment label of a given review?
- **Ground Truth Definition:** In supervised learning and benchmark evaluations, the "ground truth" sentiment label comes from **human annotators** following formal annotation guidelines (e.g., SST-2, IMDB, or internal customer support datasets). Inter-annotator reliability is measured using statistical metrics like **Cohen's Kappa** or **Fleiss' Kappa** (agreement > 0.8 denotes high reliability).
- **Weak Supervision & Metadata Signals:** In real-world customer reviews, explicit metadata like **1-5 star ratings** serves as a natural proxy or weak ground truth (e.g., 1-2 stars = Negative, 3 = Neutral, 4-5 = Positive).
- **Evaluation & Benchmarks:** We evaluate the sentiment system by running it against a frozen **Golden Test Set** (curated edge cases, sarcasm, negations, domain jargon) and measuring **Macro F1-Score**, **Precision**, **Recall**, and **Confusion Matrix** to ensure no single class is neglected.

---

### 2. How does OpenAI / an LLM identify sentiment?
- **Transformer Architecture (Causal Multi-Head Self-Attention):**
  - **Tokenization & Embeddings:** Reviews are tokenized into subwords (Byte-Pair Encoding) and converted into high-dimensional vectors representing lexical and syntactic features.
  - **Contextual Self-Attention:** Unlike simple keyword counts (bag-of-words), the attention mechanism computes relationships across tokens. It correctly resolves:
    - *Negations:* e.g., distinguishing "not bad" (positive) from "bad" (negative).
    - *Sarcasm & Conditionals:* e.g., "I would have loved this if it actually worked" (identifying subjunctive mood as negative).
    - *Aspect Polarity:* Connecting specific adjectives to specific nouns (e.g., "fast UI" vs "terrible price").
  - **Instruction Tuning & RLHF:** The model was fine-tuned on human feedback to understand subjective valence instructions, calibrated scales (-1.0 to +1.0), and schema-constrained JSON outputs.

---

### 3. Do you blindly trust ChatGPT in production?
- **Resounding NO!** In real enterprise software, blind reliance on LLMs leads to silent failures, hallucinated schemas, and uncalibrated predictions.
- **Our Defensive Engineering Guardrails:**
  1. **Rating-Sentiment Incongruence Checks:** If a user gave a 1-star rating but the LLM classified it as "Positive" (or 5 stars with "Negative"), the system flags it as an **anomaly/contradiction** rather than accepting it blindly.
  2. **Multi-Engine / Hybrid Fallback:** We implement a calibrated deterministic heuristic baseline. When the LLM and heuristic agree, confidence is high; when they disagree, confidence is lowered.
  3. **Evidence Extraction (ABSA):** The model must extract the exact substring quote supporting its decision, eliminating ungrounded hallucinations.
  4. **Human-in-the-Loop (HITL) Audit Queue:** Discrepancies and low-confidence predictions are quarantined into a dedicated review queue for human sign-off.
  5. **Structured Output Enforcement:** Using strict JSON output mode prevents downstream parsing failures.
    """)

st.caption("AI-Powered Customer Feedback & Sentiment Analytics Pipeline | v2.0 Production Ready")
