# 🤖 Innovation Signal Monitoring & Competitive Intelligence  Agent

## 📄 Brief description

This is an Orange Business challenge undertaken at the Becode-data science and AI bootcamp. The mission is to create an innovation radar, where Orange Business can quickly evaluate emerging opportunity spaces in areas of strategic interest to get an informed decision on whether to pursue them. This tool is designed for three main target groups: 
- strategists and innovators
- sales team
- presales and proposal teams


## 🎯 Core objectives & methodology 

### a. Objectives 

We structure our Orange Business mission with the following objectives: 
1. Automate collection of publicly available market insights to pinpoint emerging cutting-edge technologies, deployments of new infrastructures, advances of Orange Business competitors. We focus on both specific tech websites and de novo sites found by the agent in line with strategic priorities of Orange Business. 
2. Store these information into an sql database (db) on Azure
3. Generate opportunity spaces (OS) from the scraped information 
4. Generate a score for each OS to provide a hierarchy of priorities for Orange Business. 
5. Create a customized user interface for the target groups to explore the OS


### b. Methodology

1. We used a Microsoft foundry AI agent (gathering innovation agent) to crawl and extract structured market signals from the open web including customized specialized tech websites, according to Orange Business key interests (i.e., global and regional telecommunications and IT sectors). Prompt can be viewed in "Prompts" folder. We would like to note the following: 
- the agent is forced to capture unique signals (distinct editorial outputs)
- cap of 30 signals per run
- strategic interests: cloud infrastructure, cybersecurity, finance, manufacturing, public services, AI, data intelligence, and IoT, collaboration, etc.
- highlight the signals from Orange Business competitors
- we explicitely monitor for signals from 2024 onwards (prior to that, given the speed of technology innovation, we consider the signals outdated).
- limit hallucinations: if the agent cannot meet the criteria we gave for the number of output, it stops and returns only the number of signals it retrieved for that particular run.
- to have a wide variety of sources and signals, since we run the agent multiple times per day, we slightly modified the prompt not to capture duplicates (for eg, in the following runs we defined new keywords related to Orange business, or new countries where signals are sourced from > highly customizable prompt based on needs)
2. Using a python script, we called the AI agent and stored the output into an SQL database hosted on Azure.
3. We used a Microsoft foundry AI agent to create OS from Orange Business based on their areas of interest. 
4. Using the above agent, we computed a score for each OS with the following considerations:
-
-
-
Prompt can be viewed in "Prompts" folder.
5. We used Streamlit to create an interactive web-based user interface (access through a local web browser). 







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
|AI foundry agent   | AI agent              |
|Streamlit          |  User interface       |
|Git/github         | version control       |


>> explain specific tools used and why they are good for this project. 


## 📁 Repo structure

This repository contains the configuration and operational instructions for an automated **AI Monitoring Agent**. The agent is automated **Extraction Agent** engineered to crawl, evaluate, and extract structured market signals from the open web and specialized tech publications and systematically scan, filter, and extract high-value competitive market signals and regulatory shifts across global and regional telecommunications and IT enterprise sectors. It sits upstream of our data pipeline, feeding clean payloads directly into the processing engine.



## 💻 Installation 




**Open user interface** : 

``` 
streamlit run app.py 
```




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
- customize the prompt to have a wide variety of signals. 

## ⌛Timeline 

This project was completed in two weeks. 

## 🔦 Credits 
The innovation radar was set up by the members of our team at Becode - data science and AI bootcamp: 
- [Gunay Bayramova](https://github.com/Gunay-Bayramova) : team lead
- [Victor Courtois](https://github.com/VictorCourtois135) : repo manager/tech lead
- [Mahalakshmi Palanivel](https://github.com/mahalakshmip1604): data architect/tech lead
- [Anna Diacofotaki](https://github.com/anna-diaco): documentation specialist