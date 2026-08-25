"""
Reusable scoring helpers: source tier/type lookup (via fuzzy substring matching
against a canonical registry), recency-based urgency scoring, and market signal
strength (blending collected-signal volume with real Google Trends interest).
"""

import csv
import json
import math
import os
import re
import time
from datetime import datetime, date, timedelta

# scripts/extract_opportunities_preview.py -> go up one level, then into source/
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
SOURCE_REGISTRY_PATH = os.path.join(_PROJECT_ROOT, "source", "source_registry.csv")


def load_source_registry() -> list[dict]:
    with open(SOURCE_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


_registry = load_source_registry()


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def classify_unknown_source(source_name: str, openai_endpoint: str, openai_key: str,
                             deployment: str, api_version: str) -> dict:
    """Called only once per never-before-seen source. Asks the model to classify
    it, then the caller is expected to persist the result via append_to_registry()."""
    import requests

    prompt = f"""Classify this news/publication source for a B2B telecom market-intelligence tool.

Source name: "{source_name}"

Respond ONLY with JSON:
{{
  "canonical_name": "cleaned-up organization name, no descriptors/suffixes",
  "tier": "1, 2, or 3 (1=regulator/major analyst/wire service, 2=trade press/analyst blog, 3=company-owned press release/vendor blog)",
  "signal_type": "regulation, analyst_report, news, or press_release"
}}"""

    response = requests.post(
        f"{openai_endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}",
        headers={"api-key": openai_key, "content-type": "application/json"},
        json={"messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}},
        timeout=30,
    )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def append_to_registry(entry: dict, notes: str = "auto-classified"):
    with open(SOURCE_REGISTRY_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([entry["canonical_name"], entry["tier"], entry["signal_type"], notes])
    _registry.append({
        "canonical_name": entry["canonical_name"],
        "tier": str(entry["tier"]),
        "signal_type": entry["signal_type"],
        "notes": notes,
    })


def lookup_source(source_name: str, openai_endpoint: str = None, openai_key: str = None,
                   deployment: str = None, api_version: str = None) -> dict:
    """Matches a raw source_name against the canonical registry using substring
    matching. If nothing matches AND OpenAI credentials are provided, auto-classifies
    the source once and persists it to the registry for all future lookups."""
    normalized_input = normalize(source_name)
    matches = [row for row in _registry if normalize(row["canonical_name"]) in normalized_input]

    if matches:
        return max(matches, key=lambda row: len(row["canonical_name"]))

    if openai_endpoint and openai_key and deployment:
        print(f"  [Registry] New source encountered: '{source_name}' — auto-classifying...")
        classified = classify_unknown_source(source_name, openai_endpoint, openai_key, deployment, api_version)
        append_to_registry(classified)
        return {"canonical_name": classified["canonical_name"], "tier": str(classified["tier"]),
                "signal_type": classified["signal_type"]}

    # No credentials provided -> safe neutral default (middle of 1-5 scale), do not persist
    return {"canonical_name": source_name, "tier": "3", "signal_type": "news"}


def compute_urgency_score(publication_date_str: str, reference_date: date = None) -> float:
    """Scores recency 0-100 using a continuous decay curve (not step buckets),
    so signals are meaningfully differentiated even within the 'recent' window.
    Half-life of ~9 months: a signal 9 months old scores ~50, 18 months ~25, etc.
    Handles missing/unparseable dates gracefully."""
    if reference_date is None:
        reference_date = date.today()

    if not publication_date_str:
        return 30.0  # unknown date -> low-moderate default, not zero

    parsed = None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(publication_date_str.strip()[: len(fmt) + 2], fmt).date()
            break
        except ValueError:
            continue

    if parsed is None:
        return 30.0

    age_days = (reference_date - parsed).days

    if age_days < 0:
        return 100.0  # future-dated (rare, e.g. embargoed announcement)

    HALF_LIFE_DAYS = 270  # ~9 months
    score = 100.0 * (0.5 ** (age_days / HALF_LIFE_DAYS))
    return round(max(score, 5.0), 1)  # floor at 5, never exactly 0


TRENDS_CACHE_PATH = os.path.join(_PROJECT_ROOT, "source", "trends_cache.json")
TRENDS_CACHE_EXPIRY_DAYS = 7  # re-check a SUCCESSFUL keyword's popularity after a week
TRENDS_FAILURE_RETRY_HOURS = 24  # but retry a FAILED lookup (rate-limited/timed out) after just 1 day


def _load_trends_cache() -> dict:
    try:
        with open(TRENDS_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_trends_cache_entry(keyword: str, score):
    cache = _load_trends_cache()
    cache[keyword] = {"score": score, "fetched_at": datetime.now().isoformat()}
    os.makedirs(os.path.dirname(TRENDS_CACHE_PATH), exist_ok=True)
    with open(TRENDS_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


_trends_disk_cache = _load_trends_cache()  # loaded once per process, persists across runs

# Always-on delay between successful calls, to avoid ever triggering a block in the first place.
# Deliberately slow -- reliability over speed, since Google's unofficial API has no official rate.
BASE_DELAY_SECONDS = 20


def get_google_trends_score(keyword: str):
    """Queries Google Trends for the average search interest (0-100) of a
    keyword over the last 12 months. Returns None if the query fails or no
    data is available (e.g. keyword too niche/new) -- caller should fall back
    to the article-volume-only score in that case.

    Results are cached to disk (`trends_cache.json`) for TRENDS_CACHE_EXPIRY_DAYS
    days, so the same keyword is never re-queried across multiple runs within
    that window.

    Deliberately patient: waits ~20-30s between calls even on success (Google's
    unofficial API has no documented rate limit, so this is a conservative
    guess), and on a 429 retries up to 5 times with a long exponential backoff
    (up to several minutes) before giving up on THAT keyword only. Unlike an
    earlier version, a failure on one keyword does NOT disable Trends for the
    rest of the run -- the next keyword gets its own full set of retries, since
    rate-limiting in practice seems to often be per-request-burst rather than a
    hard, run-long IP ban."""
    cached_entry = _trends_disk_cache.get(keyword)
    if cached_entry:
        fetched_at = datetime.fromisoformat(cached_entry["fetched_at"])
        age = datetime.now() - fetched_at
        was_successful = cached_entry["score"] is not None
        still_fresh = (age.days < TRENDS_CACHE_EXPIRY_DAYS if was_successful
                       else age < timedelta(hours=TRENDS_FAILURE_RETRY_HOURS))
        if still_fresh:
            return cached_entry["score"]
        # else: fall through and actually retry -- either the success expired,
        # or this was a past failure (rate-limit/timeout) old enough to retry

    import random
    max_retries = 5
    base_backoff = 20  # seconds, before exponential growth

    for attempt in range(max_retries):
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload([keyword], timeframe="today 12-m")
            data = pytrends.interest_over_time()

            if data.empty or keyword not in data.columns:
                _save_trends_cache_entry(keyword, None)
                return None

            avg_interest = float(data[keyword].mean())
            _save_trends_cache_entry(keyword, avg_interest)
            time.sleep(BASE_DELAY_SECONDS + random.uniform(0, 10))  # deliberately slow, be polite
            return avg_interest

        except Exception as e:
            is_rate_limit = "429" in str(e)
            if is_rate_limit and attempt < max_retries - 1:
                wait = base_backoff * (2 ** attempt)  # 20, 40, 80, 160s
                print(f"  [Google Trends] Rate limited on '{keyword}', waiting {wait}s before "
                      f"retry {attempt + 2}/{max_retries}...")
                time.sleep(wait)
                continue
            elif is_rate_limit:
                print(f"  [Google Trends] Still rate limited on '{keyword}' after {max_retries} "
                      f"attempts. Skipping this keyword only (next keywords will still be tried).")
            else:
                print(f"  [Google Trends] Could not fetch data for '{keyword}': {e}")
            _save_trends_cache_entry(keyword, None)
            return None


def compute_market_signal_strength(total_articles: int, trend_keyword: str = None,
                                     saturation_point: int = 10,
                                     trends_noise_floor: float = 15.0) -> dict:
    """Measures market signal strength by combining two independent sources:
    (1) volume of collected signals (log-scaled, diminishing returns) --
        reflects how much press coverage this specific cluster generated
    (2) real-world Google Trends search interest for the technology keyword --
        reflects actual market/buyer interest, independent of what our own
        collection agent happened to find

    IMPORTANT: these are combined with max(), not an average. Google Trends is
    strongly biased toward consumer-searched terms and often returns near-zero
    (noise, not a genuine 'low interest' reading) for precise B2B/technical
    compound terms (e.g. "Private 5G + MEC"). Averaging that near-zero value in
    would unfairly punish legitimate B2B topics purely because they're too
    technical for consumer search behavior. Taking the max instead means a
    topic only needs to show strength on ONE dimension (press volume OR public
    search interest) to score well -- neither metric alone is fully reliable,
    but genuine strength on either is a real positive signal.
    Trends values below `trends_noise_floor` are treated as no-data (not a
    real 'low' reading) and ignored entirely, falling back to volume only."""
    if total_articles <= 0:
        volume_score = 0.0
    else:
        volume_score = 100.0 * math.log(1 + total_articles) / math.log(1 + saturation_point)
        volume_score = round(min(100.0, volume_score), 1)

    trends_score = get_google_trends_score(trend_keyword) if trend_keyword else None

    if trends_score is None or trends_score < trends_noise_floor:
        blended = volume_score
        trends_used = False
    else:
        blended = max(volume_score, trends_score)
        trends_used = True

    return {
        "market_signal_strength": round(blended, 1),
        "volume_score": volume_score,
        "trends_score": round(trends_score, 1) if trends_score is not None else None,
        "trends_used_in_score": trends_used,
    }


def compute_source_evidence_score(source_names: list[str], openai_endpoint: str = None,
                                   openai_key: str = None, deployment: str = None,
                                   api_version: str = None) -> dict:
    """Given the list of source_name values (with duplicates) for a cluster,
    returns diversity and quality metrics using the canonical registry."""
    total_articles = len(source_names)
    canonical_names = [
        lookup_source(name, openai_endpoint, openai_key, deployment, api_version)["canonical_name"]
        for name in source_names
    ]
    distinct_sources = set(canonical_names)
    distinct_count = len(distinct_sources)

    diversity_ratio = distinct_count / total_articles if total_articles else 0

    tiers = [
        int(lookup_source(name, openai_endpoint, openai_key, deployment, api_version)["tier"])
        for name in source_names
    ]
    avg_tier = sum(tiers) / len(tiers) if tiers else 3
    # 5-tier scale: tier 1=100, tier 2=75, tier 3=50, tier 4=25, tier 5=0
    quality_score = max(0, 100 - (avg_tier - 1) * 25)

    return {
        "total_articles": total_articles,
        "distinct_sources": distinct_count,
        "diversity_ratio": round(diversity_ratio, 2),
        "avg_source_tier": round(avg_tier, 2),
        "source_quality_score": round(quality_score, 1),
    }