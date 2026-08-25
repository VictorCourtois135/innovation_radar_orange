# 🤖 Innovation Signal Monitoring & Competitive Intelligence  Agent

This repository contains the configuration and operational instructions for an automated **AI Monitoring Agent**. The agent is automated **Extraction Agent** engineered to crawl, evaluate, and extract structured market signals from the open web and specialized tech publications and systematically scan, filter, and extract high-value competitive market signals and regulatory shifts across global and regional telecommunications and IT enterprise sectors. It sits upstream of our data pipeline, feeding clean payloads directly into the processing engine.

## 🎯 Purpose & Core Objective

The primary purpose of this agent is to automate competitive intelligence gathering. It scans the internet to identify exactly where and how Orange’s core global competitors (including **Deutsche Telekom, Vodafone, Proximus, BT, Verizon, and  AT&T etc**) are advancing, executing infrastructure rollouts, or outcompeting Orange Business in the enterprise market.

The primary mission is to identify 30 **unique, high-quality external web sources** mapping breakthroughs across these technical horizons:

* **Next-Gen Networks:** 5G Standalone (SA), network slicing, non-terrestrial networks (NTN/satellite-to-phone), and fiber rollouts.
* **Cybersecurity:** Zero-trust frameworks, threat prevention, digital sovereignty, and network defense parameters.
* **Cloud Infrastructure:** Edge-computing node distribution, distributed hosting environments, sovereign cloud frameworks, and AI data gigafactories.
* **Legacy Modernization Modules:** Deployment of specialized "Cloud MVP" frameworks to migrate fragmented databases from legacy hardware into centralized, scalable cloud data lakes.
* **Hyper-Regulated Sovereignty Expansion:** Native cloud hosting of massive multi-lingual Large Language Models (LLMs) (e.g., LightOn architectures), keeping all operational computing completely fenced within European data boundaries.
* **Airspace & Anti-Drone Defenses:** Utilizing telecom infrastructure and localized fixed networks for low-altitude airspace monitoring and drone defense.
* **AI-Orchestrated Micro-SOCs:** Hyper-automated, downscaled security operations centers driven by localized threat prevention.
* **Unified CRM-CCaaS Ecosystems:** Blending customer relationship platforms with cloud contact center technologies for seamless enterprise operations.
* **Automated Data Quality & Governance Frameworks:** Machine-learning-driven compliance rules that autonomously protect identity (SSI) and secure network defense parameters.

These discoveries must be mapped across at least one of the following targeted enterprise verticals:

* **Industry & Manufacturing (e.g., Private LTE/5G, IoT, Smart Factories)**
* **Retail & FMCG (Fast-Moving Consumer Goods)**
* **IT Services & Cloud Integration**
* **Finance & Insurance**
* **Automotive & Mobility**
* **Healthcare & Life Sciences**
* **Energy & Utilities**
* **Logistics & Transport**
* **Public Sector & Defense**

---

## 🛠️ Operational Rules & Data Integrity    

To maintain an uncompromised baseline of analytical value, the agent operates under strict operational guardrails:

* **No Syndication Duplicates:** The agent enforces a rigid uniqueness constraint. All gathered signals must represent distinct editorial coverages or official filings rather than repetitive press syndications.
* **Temporal Focus (2026):** Absolute priority is given to current 2026 initiatives, such as active multi-country 2G/3G network sunset roadmaps, 5G Advanced slicing commercialization, and live vertical case studies.
* **Anti-Bias / Independence:** All 30 sources must originate strictly from independent regulators, target competitors, or verified third-party media platforms.
* **Anti-Hallucination Limits:** If the agent cannot find pristine, high-fidelity sources matching the criteria after deep scanning, it is programmed to stop and return only what is strictly verified. It operates with a hard execution cap of a **maximum of 35 web searches** to ensure efficiency and prevent infinite query loops.

---

## 📊 Standardized Data Output

To feed seamlessly into downstream relational databases, automated innovation radars, or enterprise business intelligence dashboards, the agent bypasses all conversational chat commentary or markdown formatting wrappers. It outputs **ONLY** a single, raw, valid JSON object following this strict schema:

```json
{
  "signals": [
    {
      "id": 1,
      "source_url": "https://example-telecom-press.com",
      "source_name": "Publication or Regulator Name",
      "title": "Exact Title of the Published Article or Official Document",
      "publication_date": "2026-08-14",
      "targeted_vertical": "Industry & Manufacturing",
      "country": "Belgium",
      "summary": "A granular, cohesive 3-5 sentence analytical breakdown detailing the technology deployed, the competitive impact, and the strategic positioning of the operator within that regional vertical market.",
      "raw_excerpt": "Direct verbatim quote or key structural excerpt harvested from the source string to verify authenticity (Max 300 characters)."
    }
  ]
}
```

### 📈 Upstream Metadata Design Notes

1. **Explicit Tags vs. Vector Spaces:** While vector embeddings calculate semantic similarity to build raw thematic clusters, the agent explicitly extracts string literals (`technology_keyword`, `targeted_vertical`, `use_case_tag`). This dual-layer approach combines unsupervised machine learning (embeddings) with deterministic structural filters for robust dashboard querying.
2. **Normalized Datetime Hooks:** The `publication_date` string is restricted to strict `YYYY-MM-DD` compliance, ensuring programmatic freshness calculations and automatic deprecation sorting down the line.
