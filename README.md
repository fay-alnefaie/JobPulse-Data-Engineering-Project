# JobPulse 🇸🇦

## Saudi Job Market Data Pipeline

JobPulse is a data engineering project that collects job listings from Saudi Arabian job platforms, processes and transforms the data, and provides analytical insights through an interactive dashboard.

The project is designed using the **Medallion Architecture**:

**Bronze → Silver → Gold**

with **Airflow** for orchestration, **Snowflake** as the data warehouse, **dbt** for data transformation, **Azure Blob Storage** for raw data storage, and **Power BI** for visualization.

---

## 📌 Project Objectives

JobPulse aims to:

* Collect job listings from multiple recruitment platforms.
* Build reliable and reusable web scrapers.
* Handle pagination to collect large numbers of job listings.
* Preserve raw data as daily snapshots.
* Clean, standardize, and validate job data.
* Remove duplicate job listings.
* Store structured data in a cloud data warehouse.
* Build analytical datasets for the Saudi job market.
* Automate the data pipeline.
* Provide an interactive Power BI dashboard.

---

## 🏗️ Architecture

```text
                                                           DATA SOURCES
                                                       ┌─────────┴──────────┐
                                                       │         |          │
                                                    Tanqeeb    Jadarat   GulfTalent
                                                       │                    │
                                                       └─────────┬──────────┘
                                                                 ▼
                                                      ┌────────────────────┐
                                                      │   Python Scrapers  │
                                                      │   Requests + BS4   │
                                                      └─────────┬──────────┘
                                                                │
                                                                ▼
                                                      ┌─────────────────────┐
                                                      │   BRONZE / RAW      │
                                                      │  Azure Blob Storage │
                                                      │   Daily Snapshots   │
                                                      └──────────┬──────────┘
                                                                 │
                                                              Airflow
                                                            Orchestration
                                                                 │
                                                                 ▼
                                                      ┌─────────────────────┐
                                                      │       SILVER        │
                                                      │      Snowflake      │
                                                      │ Clean / Validated   │
                                                      │    Deduplicated     │
                                                      └──────────┬──────────┘
                                                                 │
                                                                dbt
                                                                 │
                                                                 ▼
                                                      ┌─────────────────────┐
                                                      │        GOLD         │
                                                      │      Snowflake      │
                                                      │  Analytics Tables   │
                                                      └──────────┬──────────┘
                                                                 │
                                                                 ▼
                                                          ┌─────────────┐
                                                          │  Power BI   │
                                                          │  Dashboard  │
                                                          └─────────────┘
```

---

## 🥉 Bronze Layer

The Bronze layer contains the raw data exactly as collected from the source.

No cleaning or transformation is applied at this stage.

Daily snapshots are stored separately:

```text
bronze/
└── tanqeeb/
    ├── 2026-09-05/
    │   └── jobs.csv
    ├── 2026-09-06/
    │   └── jobs.csv
    └── 2026-09-07/
        └── jobs.csv
```

This allows the project to preserve historical snapshots and track changes in the job market over time.

---

## 🥈 Silver Layer

The Silver layer contains cleaned, standardized, validated, and deduplicated job data.

Typical transformations include:

* Removing unnecessary whitespace.
* Standardizing text fields.
* Splitting location into:

  * Workplace type
  * Country
  * City
* Converting experience ranges into minimum and maximum years.
* Standardizing job types.
* Handling missing values.
* Generating a unique `job_id`.
* Removing duplicate records.
* Validating important fields.

Example:

```text
On-site - Saudi - Riyadh
```

becomes:

```text
workplace_type = On-site
country        = Saudi Arabia
city           = Riyadh
```

---

## 🥇 Gold Layer

The Gold layer contains analytical datasets designed for reporting and visualization.

Examples include:

```text
jobs_by_city
jobs_by_job_type
jobs_by_experience
jobs_by_source
jobs_over_time
```

These tables are designed to answer questions such as:

* Which Saudi cities have the most job opportunities?
* Which job types are most common?
* What experience levels are most requested?
* Which platforms provide the most listings?
* How does job availability change over time?

---

## 🔄 Pipeline

The planned pipeline is:

```text
                                                  Scrape
                                                    ↓
                                                  Save Raw Data
                                                    ↓
                                                  Upload to Azure
                                                    ↓
                                                  Load into Snowflake
                                                    ↓
                                                  Clean & Transform
                                                    ↓
                                                  Silver
                                                    ↓
                                                  dbt Transformations
                                                    ↓
                                                  Gold
                                                    ↓
                                                  Power BI
```

Airflow will orchestrate and schedule these tasks once the individual pipeline stages are stable.

---

## 🛠️ Technology Stack

### Data Collection

* Python
* Requests
* BeautifulSoup
* Pandas

### Cloud & Storage

* Microsoft Azure
* Azure Blob Storage

### Data Warehouse

* Snowflake

### Data Transformation

* dbt
* SQL
* Pandas

### Orchestration

* Apache Airflow

### Visualization

* Microsoft Power BI

### Development

* Git
* GitHub
* Docker
* Linux / WSL

---

## 📂 Project Structure

```text
JobPulse/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── src/
│   ├── scraper/
│   │   ├── tanqeeb_scraper.py
│   │   ├── gulftalent_scraper.py
│   │   └── utils.py
│   │
│   ├── transformation/
│   │   └── clean_jobs.py
│   │
│   └── validation/
│       └── data_quality.py
│
├── data/
│   └── bronze/
│
├── dbt/
│   └── jobpulse/
│
├── airflow/
│   └── dags/
│       └── jobpulse_pipeline.py
│
├── tests/
│
├── docs/
│   ├── architecture.md
│   └── data_dictionary.md
│
└── dashboard/
    └── JobPulse.pbix
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd JobPulse
```

### 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

Linux / WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy:

```text
.env.example
```

to:

```text
.env
```

Then add the required credentials.

### 5. Run the scraper

```bash
python src/scraper/tanqeeb_scraper.py
```

---

## 🔐 Environment Variables

Credentials and configuration values are stored in `.env`.

The `.env` file must **never be committed to GitHub**.

Use `.env.example` as a template.

---

## 🧪 Data Quality

The pipeline will include validation checks for:

* Missing `job_id`.
* Duplicate `job_id`.
* Missing job titles.
* Invalid experience values.
* Invalid job types.
* Unexpected null values.
* Invalid or inconsistent locations.

Data quality checks may be implemented using Python/Pandas and dbt tests.

---

## 📊 Dashboard

The final Power BI dashboard will provide an overview of the Saudi job market, including:

### Key Metrics

* Total Jobs
* Jobs by City
* Jobs by Job Type
* Jobs by Experience Level
* Jobs by Source
* Jobs Over Time

### Planned Visualizations

* Job distribution by city.
* Job type distribution.
* Experience-level distribution.
* Top companies.
* Top job titles.
* Job trends over time.

---

## 👥 Team

**JobPulse — Data Engineering Team 4**

Team members:

* Fay Al-Nefaie
* Sumayah Dhafer
* Zainab Malik
* Jana Jamal

---

## ⚠️ Disclaimer

This project is developed for educational and data engineering purposes.

Data collection is performed in accordance with the terms, policies, and technical restrictions of the source websites.

