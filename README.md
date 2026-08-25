# 🤖 Innovation Signal Monitoring & Competitive Intelligence  Agent

## 📄 Brief description

This is an Orange Business challenge undertaken at the Becode-data science and AI bootcamp. The mission is to create an innovation radar, where Orange Business can quickly evaluate emerging opportunity spaces in areas of strategic interest to get an informed decision on whether to pursue them. This tool is designed for three main target groups: 
- strategists and innovators
- sales team
- presales and proposal teams


## 🎯 Core objectives & methodology 

### a. Objectives 

We structure our Orange Business mission with the following objectives: 
- automate collection of publicaly available market insights to pinpoint emerging cutting-edge technologies, deployments of new infrastructures, advances of Orange Business competitors. We focus on both specific tech websites and de novo sites found by the agent in line with strategic priorities of Orange Business. 
- store these information into an sql database (db) on Azure
- generate opportunity spaces from the scraped information 
- generate a score for each opportunity space to provide a hierarchy of priorities for Orange Business. We will provide **30 unique, high-quality OP** 
- create a customized user interface for the target groups to explore the data


### b. Methodology

We first created an AI extracting agent to crawl and extract structured market signals from the open web including customized specialized tech websites, according to Orange Business key interests (i.e., global and regional telecommunications and IT sectors). We then store these results into an SQL database hosted in Azure. Subsequently, we use a second engineered AI agent, that allows us to create opportunity spaces from the previous input. 




The primary purpose of this agent is to automate competitive intelligence gathering. It scans the internet to identify exactly where and how Orange’s core global competitors (including **Deutsche Telekom, Vodafone, Proximus, BT, Verizon, and  AT&T etc**) are advancing, executing infrastructure rollouts, or outcompeting Orange Business in the enterprise market.

The primary mission is to identify 30 **unique, high-quality external web sources** mapping breakthroughs across the areas of interest of Orange Business:

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

## 🛕 Project architecture

![pipeline](20260825_readme_images.png)

*Schematic representation of our pipeline*


## 🛠️ Tech stack 

|Tool               |       Function        |
|-------------------|-----------------------|
|Python             | Programming language  |
|SQL                | db type               |
|drawDB             | db schema             |
|Azure              | cloud computing       |
| AI foundry agent  | AI agent              |
| Streamlit         |  User interface       |
|Git/github         | version control       |


>> explain specific tools used and why they are good for this project. 


## 📁 Repo structure

This repository contains the configuration and operational instructions for an automated **AI Monitoring Agent**. The agent is automated **Extraction Agent** engineered to crawl, evaluate, and extract structured market signals from the open web and specialized tech publications and systematically scan, filter, and extract high-value competitive market signals and regulatory shifts across global and regional telecommunications and IT enterprise sectors. It sits upstream of our data pipeline, feeding clean payloads directly into the processing engine.



## 💻 Installation 




**Open user interface** : 

``` 
streamlit run app.py 
```


## 📃Operational Rules & Data Integrity    

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


## 🎡 Database structure
![](db_schema.png)
*We generated three tables: one containing the articles, one with the opportunity space and a table connecting the two*

## 📈 Upstream Metadata Design Notes

1. **Explicit Tags vs. Vector Spaces:** While vector embeddings calculate semantic similarity to build raw thematic clusters, the agent explicitly extracts string literals (`technology_keyword`, `targeted_vertical`, `use_case_tag`). This dual-layer approach combines unsupervised machine learning (embeddings) with deterministic structural filters for robust dashboard querying.
2. **Normalized Datetime Hooks:** The `publication_date` string is restricted to strict `YYYY-MM-DD` compliance, ensuring programmatic freshness calculations and automatic deprecation sorting down the line.

## 💫 Top 5 unique features 
top 5


## 🔍 Limitations and future outlooks
At least 3


## 👽 Usage of AI and its importance

## 💡 Scoring explained 

## ✅ Accuracy of results 

## ⚔️ Challenges 
- country name: because of prompt eg USA or united states etc. 
- time 30 vs 50 results (50 not running); even sometimes 30 run with no issue, but sometimes it run +++ time. 
- keep optimizing the prompt to cover all the innovative topics, all over the world, competitive. 
- Cost: increases with keywords input. 
- create the db with student subscription 
- scoring 
- google trends API: limit of requests per specific time (not sure if day, hour etc.)
- 

## ⌛Timeline 

This project was completed in two weeks. 

## 🔦 Credits 
The innovation radar was set up by the members of our team at Becode - data science and AI bootcamp: 
- [Gunay Bayramova](https://github.com/Gunay-Bayramova) : team lead
- [Vicror Courtois](https://github.com/VictorCourtois135) : repo manager/tech lead
- [Mahalakshmi Palanivel](https://github.com/mahalakshmip1604): data architect/tech lead
- [Anna Diacofotaki](https://github.com/anna-diaco): documentation specialist