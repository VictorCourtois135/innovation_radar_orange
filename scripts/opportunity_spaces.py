"""
Reads all signals, groups them into clusters by embedding similarity, computes
objective scores (urgency, source diversity, source quality) from the signal
data directly, asks the agent for qualitative judgment (novelty, strategic
relevance, and the narrative fields), and combines everything into a single
attractiveness_score — WITHOUT writing anything to the database.

Requires the same environment variables as run_agent_and_save.py, plus the
scores.py module and source_registry.csv in the same folder.
"""

import os
import json
import pyodbc
from collections import defaultdict
from difflib import SequenceMatcher
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

from scores import compute_urgency_score, compute_source_evidence_score, compute_market_signal_strength

load_dotenv()

SQL_SERVER = os.environ["SQL_SERVER"]
SQL_DATABASE = os.environ["SQL_DATABASE"]
SQL_USER = os.environ["SQL_USER"]
SQL_PASSWORD = os.environ["SQL_PASSWORD"]

SQL_CONN_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER=tcp:{SQL_SERVER},1433;"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};PWD={SQL_PASSWORD};"
    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
)

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
BUILDER_AGENT_NAME = os.environ.get("AZURE_AI_BUILDER_AGENT_NAME", "opportunity-space-builder-agent")

# Used only for auto-classifying brand-new sources (optional -- omit to skip auto-classification)
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")

SIMILARITY_THRESHOLD = 0.82
MIN_CLUSTER_SIZE = 3
OUTPUT_CSV_PATH = "opportunity_spaces_preview.csv"

# Weights for the final attractiveness_score (must sum to 1.0) -- matches the
# original deck formula: 30% market signal + 20% source diversity + 15% evidence
# quality + 15% novelty/momentum + 20% strategic relevance
WEIGHT_MARKET_SIGNAL = 0.30
WEIGHT_SOURCE_DIVERSITY = 0.20
WEIGHT_EVIDENCE_QUALITY = 0.15
WEIGHT_NOVELTY_MOMENTUM = 0.15
WEIGHT_STRATEGIC_RELEVANCE = 0.20


# --- Step 1: find clusters of related signals ------------------------
def find_clusters(conn) -> list[list[int]]:
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT s1.id, s2.id
        FROM signals s1
        JOIN signals s2 ON s1.id < s2.id
        WHERE s1.embedding IS NOT NULL AND s2.embedding IS NOT NULL
          AND 1 - VECTOR_DISTANCE('cosine', s1.embedding, s2.embedding) > {SIMILARITY_THRESHOLD}
        """
    )
    edges = cur.fetchall()

    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x
    def union(x, y):
        parent[find(x)] = find(y)

    for id_1, id_2 in edges:
        union(id_1, id_2)

    clusters = defaultdict(list)
    for node in list(parent):
        clusters[find(node)].append(node)

    return [members for members in clusters.values() if len(members) >= MIN_CLUSTER_SIZE]


# --- Step 2: compute objective scores directly from the signal data ----
def compute_cluster_scores(conn, signal_ids: list[int]) -> dict:
    cur = conn.cursor()
    placeholders = ",".join("?" * len(signal_ids))
    cur.execute(
        f"SELECT publication_date, source_name FROM signals WHERE id IN ({placeholders})",
        signal_ids,
    )
    rows = cur.fetchall()

    publication_dates = [r.publication_date for r in rows]
    source_names = [r.source_name for r in rows]

    urgency_scores = [compute_urgency_score(d) for d in publication_dates]
    urgency_time_horizon = sum(urgency_scores) / len(urgency_scores) if urgency_scores else 30.0  # average

    evidence = compute_source_evidence_score(
        source_names,
        openai_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_key=AZURE_OPENAI_KEY,
        deployment=AZURE_OPENAI_DEPLOYMENT,
        api_version=AZURE_OPENAI_API_VERSION,
    )

    return {
        "source_diversity_score": round(evidence["diversity_ratio"] * 100, 1),
        "evidence_quality": evidence["source_quality_score"],
        "urgency_time_horizon": round(urgency_time_horizon, 1),
        "total_articles": evidence["total_articles"],
        "distinct_sources": evidence["distinct_sources"],
    }


# --- Step 3: ask the agent for qualitative judgment only ----------------
_project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
_openai_client = _project.get_openai_client(agent_name=BUILDER_AGENT_NAME)


def extract_opportunity(conn, signal_ids: list[int]) -> dict:
    cur = conn.cursor()
    placeholders = ",".join("?" * len(signal_ids))
    cur.execute(
        f"SELECT title, summary, source_name FROM signals WHERE id IN ({placeholders})",
        signal_ids,
    )
    rows = cur.fetchall()

    combined = "\n\n".join(f"Source: {r.source_name}\nTitle: {r.title}\nSummary: {r.summary}" for r in rows)

    # NOTE: the agent's Instructions in Foundry must be updated to only ask for
    # vertical, use_case, technology, why_hot, why_matters, next_action,
    # strategic_relevance, capability_check_note (and skip). market_signal_strength,
    # source_diversity, evidence_quality, and urgency_time_horizon are no longer
    # requested from the agent -- they are all computed directly from the signal
    # data (see compute_cluster_scores). strategic_relevance is the ONLY score
    # still asked from the LLM, since it's the only genuinely qualitative judgment.
    user_input = f"SIGNALS:\n{combined}"

    conversation = _openai_client.conversations.create()
    response = _openai_client.responses.create(
        conversation=conversation.id,
        input=user_input,
    )

    text = response.output_text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    # Detect an outright model refusal (not malformed JSON -- a genuine "I can't help" reply)
    # before attempting to parse, so it's reported accurately rather than lumped in with
    # formatting errors.
    refusal_markers = ("i'm sorry", "i cannot assist", "i can't assist", "i cannot help", "i can't help")
    if text.lower().startswith(refusal_markers) or any(m in text.lower()[:120] for m in refusal_markers):
        print(f"  [WARNING] Agent refused to respond for this cluster. Raw response: {repr(text)}")
        return {"skip": True, "reason": f"Agent declined to respond: {text[:200]}"}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = text.replace("\\'", "'")
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            print(f"  [WARNING] Failed to parse agent response as JSON even after repair attempt: {e}")
            print(f"  [WARNING] Raw response was: {repr(text)}")
            return {"skip": True, "reason": f"JSON parsing error, treated as skip: {e}"}


# --- Step 4: combine into the final attractiveness_score ----------------
def compute_attractiveness_score(cluster_scores: dict, strategic_relevance: float) -> float:
    return round(
        WEIGHT_MARKET_SIGNAL * cluster_scores["market_signal_strength"]
        + WEIGHT_SOURCE_DIVERSITY * cluster_scores["source_diversity_score"]
        + WEIGHT_EVIDENCE_QUALITY * cluster_scores["evidence_quality"]
        + WEIGHT_NOVELTY_MOMENTUM * cluster_scores["urgency_time_horizon"]
        + WEIGHT_STRATEGIC_RELEVANCE * strategic_relevance,
        1,
    )


# --- Merge near-duplicate opportunities ----------------------------------
NAME_SIMILARITY_THRESHOLD = 0.6


def merge_near_duplicate_opportunities(opportunities: list[dict]) -> list[dict]:
    merged = []
    used = [False] * len(opportunities)

    for i, opp_a in enumerate(opportunities):
        if used[i]:
            continue
        group = [opp_a]
        used[i] = True

        for j in range(i + 1, len(opportunities)):
            if used[j]:
                continue
            opp_b = opportunities[j]

            name_similarity = SequenceMatcher(None, opp_a["name"].lower(), opp_b["name"].lower()).ratio()
            why_matters_similarity = SequenceMatcher(
                None, opp_a["why_matters"].lower(), opp_b["why_matters"].lower()
            ).ratio()

            if name_similarity >= NAME_SIMILARITY_THRESHOLD or why_matters_similarity >= 0.55:
                group.append(opp_b)
                used[j] = True

        if len(group) == 1:
            merged.append(opp_a)
        else:
            best = max(group, key=lambda o: o["attractiveness_score"])
            all_signal_ids = sorted(set(sid for o in group for sid in o["signal_ids"]))
            best = {**best, "signal_ids": all_signal_ids, "merged_from": len(group)}
            merged.append(best)
            print(f"Merged {len(group)} near-duplicate opportunities into: {best['name']}")

    return merged


# --- Save to Azure SQL Database ---------------------------------------
def save_opportunity(conn, data: dict, cluster_scores: dict, strategic_relevance: float,
                      attractiveness_score: float, signal_ids: list[int]) -> int:
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM opportunity_spaces WHERE vertical = ? AND use_case = ? AND technology = ?",
        data["vertical"], data["use_case"], data["technology"],
    )
    existing = cur.fetchone()

    if existing:
        opportunity_id = existing[0]
        cur.execute(
            """
            UPDATE opportunity_spaces SET
                why_hot = ?, why_matters = ?, next_action = ?, capability_check_note = ?,
                market_signal_strength = ?, source_diversity_score = ?, evidence_quality = ?,
                urgency_time_horizon = ?, strategic_relevance = ?,
                total_articles = ?, distinct_sources = ?, updated_at = SYSUTCDATETIME()
            WHERE id = ?
            """,
            data["why_hot"], data["why_matters"], data["next_action"],
            data.get("capability_check_note"),
            cluster_scores["market_signal_strength"], cluster_scores["source_diversity_score"],
            cluster_scores["evidence_quality"], cluster_scores["urgency_time_horizon"],
            strategic_relevance, cluster_scores["total_articles"], cluster_scores["distinct_sources"],
            opportunity_id,
        )
    else:
        cur.execute(
            """
            INSERT INTO opportunity_spaces
                (vertical, use_case, technology, why_hot, why_matters, next_action,
                 capability_check_note, market_signal_strength, source_diversity_score,
                 evidence_quality, urgency_time_horizon, strategic_relevance,
                 total_articles, distinct_sources)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data["vertical"], data["use_case"], data["technology"],
            data["why_hot"], data["why_matters"], data["next_action"],
            data.get("capability_check_note"),
            cluster_scores["market_signal_strength"], cluster_scores["source_diversity_score"],
            cluster_scores["evidence_quality"], cluster_scores["urgency_time_horizon"],
            strategic_relevance, cluster_scores["total_articles"], cluster_scores["distinct_sources"],
        )
        opportunity_id = cur.fetchone()[0]

    for signal_id in signal_ids:
        cur.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM opportunity_space_signals WHERE opportunity_space_id = ? AND signal_id = ?)
            INSERT INTO opportunity_space_signals (opportunity_space_id, signal_id) VALUES (?, ?)
            """,
            opportunity_id, signal_id, opportunity_id, signal_id,
        )

    conn.commit()
    return opportunity_id


# --- Main -----------------------------------------------------------
def main():
    conn = pyodbc.connect(SQL_CONN_STRING)
    collected = []  # holds everything needed to save, before merging duplicates

    try:
        clusters = find_clusters(conn)
        print(f"Found {len(clusters)} clusters of related signals.\n")

        for i, signal_ids in enumerate(clusters, start=1):
            cluster_scores = compute_cluster_scores(conn, signal_ids)
            data = extract_opportunity(conn, signal_ids)

            if data.get("skip"):
                print(f"{'=' * 60}")
                print(f"Cluster {signal_ids} SKIPPED — {data.get('reason', 'no reason given')}")
                print(f"{'=' * 60}\n")
                continue

            market_signal = compute_market_signal_strength(
                cluster_scores["total_articles"], trend_keyword=data["technology"]
            )
            cluster_scores["market_signal_strength"] = market_signal["market_signal_strength"]

            strategic_relevance = data.get("strategic_relevance", 50)
            attractiveness_score = compute_attractiveness_score(cluster_scores, strategic_relevance)
            name = f"{data['vertical']} x {data['use_case']} x {data['technology']}"

            print(f"{'=' * 60}")
            print(f"Opportunity space #{i}  (from signals {signal_ids})")
            print(f"Name:                   {name}")
            print(f"ATTRACTIVENESS SCORE:   {attractiveness_score}  <-- headline score")
            print(f"{'=' * 60}")
            print(f"Vertical:               {data['vertical']}")
            print(f"Use case:               {data['use_case']}")
            print(f"Technology:             {data['technology']}")
            print(f"Why hot:                {data['why_hot']}")
            print(f"Why it matters:         {data['why_matters']}")
            print(f"Next action:            {data['next_action']}")
            print(f"--- score detail ---")
            trends_note = (f"trends={market_signal['trends_score']} used" if market_signal["trends_used_in_score"]
                           else f"trends={market_signal['trends_score']} ignored as noise" if market_signal["trends_score"] is not None
                           else "trends=no data")
            print(f"Market signal strength: {cluster_scores['market_signal_strength']} "
                  f"(volume={market_signal['volume_score']}, {trends_note}, "
                  f"{cluster_scores['total_articles']} articles)")
            print(f"Source diversity:       {cluster_scores['source_diversity_score']} "
                  f"({cluster_scores['distinct_sources']} distinct / {cluster_scores['total_articles']} articles)")
            print(f"Evidence quality:       {cluster_scores['evidence_quality']}")
            print(f"Urgency/time horizon:   {cluster_scores['urgency_time_horizon']} (computed from recency)")
            print(f"Strategic relevance:    {strategic_relevance} (LLM judgment)")
            print()

            collected.append({
                "data": data,
                "cluster_scores": cluster_scores,
                "strategic_relevance": strategic_relevance,
                "attractiveness_score": attractiveness_score,
                "signal_ids": signal_ids,
                "name": name,
                "vertical": data["vertical"],
                "why_matters": data["why_matters"],
            })

        if not collected:
            print("No opportunities to save.")
            return

        merged = merge_near_duplicate_opportunities(collected)
        print(f"\n{len(collected) - len(merged)} near-duplicates merged. Saving {len(merged)} opportunities to database...\n")

        for item in merged:
            opportunity_id = save_opportunity(
                conn, item["data"], item["cluster_scores"], item["strategic_relevance"],
                item["attractiveness_score"], item["signal_ids"],
            )
            print(f"Saved: {item['name']}  (attractiveness={item['attractiveness_score']})  "
                  f"-> opportunity_spaces.id = {opportunity_id}")

        print(f"\nDone. {len(merged)} opportunities saved/updated in the database.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()