import os
import json
import time

# The OpenAI SDK is only required if you actually want live LLM calls.
# If it isn't installed, or no API key is set, the module transparently
# falls back to the deterministic keyword-based heuristic below.
try:
    from openai import OpenAI, OpenAIError
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

SYSTEM_PROMPT = """You are an expert customer feedback and sentiment analyst. For each review you are given, \
return a single JSON object with exactly these fields:

- "sentiment_class": one of "Positive", "Neutral", "Negative"
- "sentiment_score": a float from -1.0 (very negative) to 1.0 (very positive)
- "confidence_score": a float from 0.0 to 1.0 representing model certainty
- "feedback_category": one of "UI/UX", "Performance", "Customer Support", "Pricing", "Features", "General"
- "evidence_quote": a brief direct excerpt or key phrase from the review that justifies the sentiment
- "suggested_action": a short, concrete, one-sentence recommendation for the product/support team

Respond with ONLY the JSON object, no extra text, no markdown fences."""


def _build_user_prompt(review):
    return (
        f"Review text: \"{review['review_text']}\"\n"
        f"Star rating (1-5): {review['rating']}\n\n"
        "Analyze this review and return the JSON object described in the system prompt."
    )


def _check_incongruence(rating, sentiment_class):
    """
    Detects semantic mismatch / incongruence between star rating and sentiment class.
    E.g., 1-star rated review classified as Positive (sarcasm or hallucination),
    or 5-star rated review classified as Negative.
    """
    if rating <= 2 and sentiment_class == "Positive":
        return True
    if rating >= 4 and sentiment_class == "Negative":
        return True
    return False


def _call_llm(review, client):
    """
    Calls the OpenAI Chat Completions API for a single review and parses
    the structured JSON response. Raises on failure so the caller can
    retry or fall back to the heuristic.
    """
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(review)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=250,
    )
    content = response.choices[0].message.content
    parsed = json.loads(content)

    required_keys = {"sentiment_class", "sentiment_score", "feedback_category", "suggested_action"}
    if not required_keys.issubset(parsed.keys()):
        raise ValueError(f"LLM response missing required keys: {parsed}")

    sentiment_class = parsed["sentiment_class"]
    rating = int(review.get("rating", 3))
    is_conflicted = _check_incongruence(rating, sentiment_class)
    confidence = float(parsed.get("confidence_score", 0.90 if not is_conflicted else 0.45))

    return {
        "sentiment_class": sentiment_class,
        "sentiment_score": round(float(parsed["sentiment_score"]), 2),
        "confidence_score": round(confidence, 2),
        "feedback_category": parsed["feedback_category"],
        "evidence_quote": parsed.get("evidence_quote", review["review_text"][:40] + "..."),
        "suggested_action": parsed["suggested_action"],
        "is_conflicted": is_conflicted,
        "model_used": LLM_MODEL
    }


def _call_llm_with_retries(review, client):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _call_llm(review, client)
        except (OpenAIError, json.JSONDecodeError, ValueError, KeyError) as exc:
            last_error = exc
            print(f"[AI Enricher] LLM call failed (attempt {attempt}/{MAX_RETRIES}) "
                  f"for {review.get('review_id')}: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"LLM enrichment failed after {MAX_RETRIES} attempts") from last_error


def _heuristic_enrich(review):
    """
    Deterministic keyword-based fallback and baseline verification.
    Used automatically when no OpenAI API key is configured or as an
    ensemble validator against LLM predictions.
    """
    text = review["review_text"].lower()
    rating = int(review.get("rating", 3))

    category_triggers = {
        "UI/UX": ["interface", "design", "ui", "ux", "clean", "confusing", "dark mode", "layout", "eyes"],
        "Performance": ["fast", "slow", "lag", "lags", "crash", "crashed", "speed", "loading", "responsive"],
        "Customer Support": ["support", "service", "customer service", "help", "resolved", "respond"],
        "Pricing": ["value", "money", "pricing", "expensive", "cost"],
        "Features": ["workflow", "integrations", "integration", "export", "search", "updates", "popup", "notifications"],
    }

    detected_category = "General"
    matched_keyword = ""
    for cat, keywords in category_triggers.items():
        for keyword in keywords:
            if keyword in text:
                detected_category = cat
                matched_keyword = keyword
                break
        if matched_keyword:
            break

    # Determine sentiment and evidence quote
    evidence = matched_keyword if matched_keyword else review["review_text"][:35]

    if rating >= 4:
        sentiment_class = "Positive"
        sentiment_score = round(0.5 + (rating - 4) * 0.25, 2)
        action_item = "Leverage positive feedback for testimonials / marketing."
        confidence = 0.88
    elif rating <= 2:
        sentiment_class = "Negative"
        sentiment_score = round(-0.5 - (2 - rating) * 0.25, 2)
        confidence = 0.86
        if "lag" in text or "slow" in text:
            action_item = "Optimize database queries and background export runners."
        elif "support" in text or "service" in text:
            action_item = "Escalate ticket response SLA to team lead."
        elif "crash" in text:
            action_item = "Deploy critical bug patch for state-saving logic."
        elif "pricing" in text or "expensive" in text:
            action_item = "Review Tier pricing models and consider discounts."
        elif "dark mode" in text:
            action_item = "Prioritize Dark Mode addition in next sprint."
        else:
            action_item = "Flag to Product Management for user interview."
    else:
        sentiment_class = "Neutral"
        sentiment_score = 0.0
        confidence = 0.75
        action_item = "Monitor for future detailed review updates."

    is_conflicted = _check_incongruence(rating, sentiment_class)
    if is_conflicted:
        confidence = 0.40

    return {
        "sentiment_class": sentiment_class,
        "sentiment_score": sentiment_score,
        "confidence_score": round(confidence, 2),
        "feedback_category": detected_category,
        "evidence_quote": f"Matched term: '{evidence}'" if matched_keyword else review["review_text"][:40],
        "suggested_action": action_item,
        "is_conflicted": is_conflicted,
        "model_used": "deterministic-heuristic"
    }


def enrich_reviews_with_ai(reviews):
    """
    Enriches reviews with sentiment, category, and suggested-action tags.

    If OPENAI_API_KEY is set and the openai package is installed, each
    review is sent to a live LLM (default: gpt-4o-mini) for analysis.
    Otherwise, or if a call fails after retries, this falls back to a
    deterministic keyword heuristic so the pipeline always completes.
    """
    print("[AI Enricher] Initializing LLM sentiment processing agent...")

    api_key = os.environ.get("OPENAI_API_KEY")
    use_live_llm = bool(api_key) and _OPENAI_AVAILABLE
    client = None

    if bool(api_key) and not _OPENAI_AVAILABLE:
        print("[AI Enricher] OPENAI_API_KEY is set but the 'openai' package isn't installed. "
              "Run 'pip install openai' to enable live LLM calls. Falling back to heuristic mode.")
    elif use_live_llm:
        print(f"[AI Enricher] OpenAI key found. Using live '{LLM_MODEL}' calls for enrichment.")
        client = OpenAI(api_key=api_key)
    else:
        print("[AI Enricher] No OPENAI_API_KEY found. Using deterministic keyword heuristic.")

    enriched_reviews = []
    live_failures = 0

    for review in reviews:
        enrichment = None

        if use_live_llm:
            try:
                enrichment = _call_llm_with_retries(review, client)
            except RuntimeError as exc:
                live_failures += 1
                print(f"[AI Enricher] Falling back to heuristic for {review.get('review_id')}: {exc}")

        if enrichment is None:
            enrichment = _heuristic_enrich(review)
            # Small delay to mimic per-item processing cost in heuristic-only mode
            if not use_live_llm:
                time.sleep(0.02)

        enriched_reviews.append({**review, **enrichment})

    mode = "live LLM" if use_live_llm else "heuristic"
    print(f"[AI Enricher] Enrichment complete. Tagged {len(enriched_reviews)} records "
          f"via {mode} mode" + (f" ({live_failures} fell back to heuristic)." if use_live_llm else "."))

    return enriched_reviews


def analyze_single_review(review_text, rating=3, customer_name="Anonymous", source="Web"):
    """
    Convenience method for real-time inference on a single review.
    Used by REST API endpoints and interactive web dashboards.
    """
    review = {
        "review_id": f"LIVE_{int(time.time() * 1000)}",
        "customer_name": customer_name,
        "source": source,
        "rating": int(rating),
        "review_text": review_text,
        "review_date": time.strftime("%Y-%m-%d"),
    }
    return enrich_reviews_with_ai([review])[0]


if __name__ == "__main__":
    test_reviews = [
        {
            "review_id": "REV_1",
            "review_text": "The interface is confusing.",
            "rating": 2,
            "source": "Google",
            "customer_name": "Test User",
            "review_date": "2026-07-27",
        }
    ]
    print(enrich_reviews_with_ai(test_reviews))
