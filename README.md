# AI Intelligence Data Pipeline

A scalable, fault-tolerant, production-grade data intelligence pipeline engineered for **GraphOne / FrontierAtlas**. Built to acquire, normalize, enrich, and canonicalize multi-dimensional AI ecosystem datasets across startups, products, research papers, real-time news signals, and job postings.

---

## Executive Summary & Assessment Scope

This project implements all six phases specified in the **AI Engineer Assessment**:

1. **Phase I: Massive One-Time Data Acquisition**
   - **Startups:** 1,000 unique records extracted from the Y Combinator directory with canonical naming, employee count, batch, and location.
   - **Products:** 1,000 unique AI products extracted from Product Hunt with pricing model categorization (`FREE`, `FREEMIUM`, `PAID`, `ENTERPRISE`) and maker canonicalization.
   - **Research Papers:** 1,000 unique AI research papers correlated with open-source GitHub repositories from **Papers with Code** and **arXiv**, enriched with live/dynamic GitHub stars.
2. **Phase II: High-Fidelity Signal Ingestion**
   - Ingests signals across **5 distinct AI news sources** (TechCrunch AI, Wired AI, The Verge AI, Decrypt AI, HackerNews AI) and **5 distinct AI job boards** (RemoteOK, Jobicy, Remotive, Arbeitnow, Himalayas).
   - Strict **24-hour freshness guarantee** with custom date normalization handling ISO-8601, RFC-2822, Unix epochs, and relative timestamps (e.g., *"2 hours ago"*), plus missing-date discovery heuristics.
3. **Phase III: Multi-Tier LLM Extraction Engine**
   - **Fallback Chain:** Multi-tier provider cascade: `Google Gemini 1.5 Flash` &rarr; `Groq Llama 3.3 70B` &rarr; `DeepSeek Chat` &rarr; `Deterministic Rule Engine`.
   - **Context Window Budgeting (413 Mitigation):** Pre-extraction DOM sanitizer strips boilerplate HTML; intelligent chunker preserves high-density header/footer metadata while pruning middle fluff to strictly prevent HTTP 413 errors.
   - **Rate Limit Resilience (429 Mitigation):** Exponential backoff with decorrelated full jitter (`sleep = min(max_delay, base_delay * 2^attempt) + Uniform(0, jitter)`).
4. **Phase IV: Deterministic Entity Resolution**
   - Canonicalizes messy organization and product strings (e.g., *"OpenAI"*, *"OpenAI, Inc."*, and *"Open AI"* &rarr; `OpenAI`).
   - Grounded in a verified seed list of **50+ prominent AI enterprises**, corporate suffix stripping, string normalizers, and fuzzy matching (Levenshtein similarity &ge; 0.85).
   - Generates a transparent, auditable **Entity Mapping Log** with confidence scores and resolution methods.
5. **Phase V: Anti-Bot & Scale Thinking**
   - Asynchronous crawler built on `asyncio` and `aiohttp` with per-domain token bucket rate limiters, realistic browser fingerprinting (modern `Sec-Ch-Ua` client hints and User-Agent pools), and connection pooling.
   - Documented and demonstrated **Playwright Async stealth strategy** for bypassing Cloudflare Turnstile, Datadome fingerprinting, and dynamic JavaScript single-page applications (SPAs).
6. **Phase VI: Architecture & Production Design**
   - Complete 3-page technical architecture design document (**`architecture.pdf`**) covering 500,000+ record scale strategy, context window & rate limit management, distributed freshness tracking (Bloom filters + Redis mutex), and polyglot storage justification (PostgreSQL 16 + pgvector + Neo4j Graph).

---

## Project Structure

```
ai-intelligence-pipeline/
├── architecture.pdf              # 3-Page Detailed Architecture Specification (Phase VI)
├── main.py                       # Master Pipeline Orchestrator
├── pyproject.toml                # Dependencies and project metadata (uv-managed)
├── README.md                     # Setup instructions and architecture overview
│
├── data/
│   ├── raw/                      # Raw JSON datasets
│   │   ├── ai_startups.json      # 1,000 AI Startups
│   │   ├── ai_products.json      # 1,000 AI Products
│   │   ├── research_papers.json  # 1,000 Research Papers with GitHub metrics
│   │   └── github_repositories.json
│   └── processed/                # Validation reports & processed datasets
│       ├── data_validation_report.json
│       └── github_quality_results.json
│
├── exports/                      # Submission Deliverables (Google Sheets & CSV)
│   ├── GraphOne_AI_Intelligence_Pipeline_Submission.xlsx  # Multi-tab Workbook (6 Tabs)
│   ├── 1_startups.csv            # Tab 1: Startups (1,000 rows)
│   ├── 2_products.csv            # Tab 2: Products (1,000 rows)
│   ├── 3_research_papers.csv     # Tab 3: Research Papers (1,000 rows)
│   ├── 4_jobs.csv                # Tab 4: 24-hr Fresh Jobs
│   ├── 5_news.csv                # Tab 5: 24-hr Fresh News
│   ├── 6_entity_mapping_log.csv  # Tab 6: Entity Mapping Audit Log
│   └── architecture.pdf          # Copy of architecture specification
│
├── src/
│   ├── collectors/
│   │   ├── antibot_crawler.py    # Async crawler with domain throttling & stealth headers
│   │   ├── github_collector.py   # GitHub repository search and metadata collector
│   │   ├── product_collector.py  # Product Hunt RSS & verified archive collector (1,000+)
│   │   ├── research_collector.py # arXiv & Papers with Code collector with GitHub stars (1,000+)
│   │   ├── signal_collector.py   # 24-hr Fresh News (5 sources) & Jobs (5 boards)
│   │   └── startup_collector.py  # Y Combinator AI startups collector (1,000+)
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   └── orchestrator.py       # Multi-Tier LLM Fallback (Gemini -> Groq -> DeepSeek -> Rule)
│   │
│   ├── processing/
│   │   ├── data_validator.py     # Structural validation, URL verification, encoding checks
│   │   ├── entity_resolver.py    # Deterministic Entity Resolution with 50+ AI seed DB
│   │   ├── exporter.py           # Multi-sheet Excel & CSV exporter strictly matching schemas
│   │   └── github_quality.py     # Relevance classifier for repositories
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   └── schemas.py            # Canonical Pydantic schemas (Startup, Product, Paper, Job, News)
│   │
│   └── generate_architecture_pdf.py # ReportLab generator for 3-page architecture.pdf
│
└── tests/                        # 53 Automated Pytest Tests (100% Pass Rate)
    ├── test_antibot_crawler.py
    ├── test_data_validator.py
    ├── test_entity_resolver.py
    ├── test_github_collector.py
    ├── test_github_quality.py
    ├── test_llm_orchestrator.py
    ├── test_main.py
    ├── test_product_collector.py
    ├── test_research_collector.py
    ├── test_signal_ingestion.py
    └── test_startup_collector.py
```

---

## Installation & Environment Setup

This project uses modern Python packaging via **[`uv`](https://docs.astral.sh/uv/)** for fast, deterministic dependency resolution.

### Prerequisites
- Python 3.13+
- `uv` installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Setup Virtual Environment & Dependencies

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-intelligence-pipeline

# Sync dependencies into local virtual environment
uv sync
```

### Optional LLM API Keys (Tier 1-3)
If you wish to run live external LLM queries, set your API keys in your environment or a `.env` file:
```bash
export GEMINI_API_KEY="your-gemini-key"
export GROQ_API_KEY="your-groq-key"
export DEEPSEEK_API_KEY="your-deepseek-key"
export GITHUB_TOKEN="your-github-token" # Optional, for higher GitHub API rate limits
```
*Note: If no API keys are provided, the Multi-Tier Orchestrator automatically and gracefully falls back to Tier 4 (Deterministic Rule Engine) with zero errors.*

---

## Running the Pipeline

### 1. Full Production Bulk Run (All 6 Phases & 1,000+ Records)
Runs the entire pipeline, acquires 1,000 startups, 1,000 products, 1,000 research papers, 24-hr fresh signals, performs entity resolution, validates datasets, compiles `architecture.pdf`, and exports the 6 Google Sheets tabs:

```bash
uv run python main.py
```

### 2. Fast Demo Run (For Rapid Verification)
Runs the pipeline in lightweight mode with small sample batches:

```bash
uv run python main.py --demo
```

### 3. Re-compile Architecture PDF Only
Generates the 3-page `architecture.pdf` documentation:

```bash
uv run python src/generate_architecture_pdf.py
```

---

## Running Automated Tests

The codebase includes an extensive suite of **53 unit and integration tests** validating every component:

```bash
uv run python -m pytest -v
```

All 53 tests run in **< 4 seconds** with a 100% pass rate:
- `test_antibot_crawler.py`: Stealth header generation, domain throttling, Playwright architecture.
- `test_data_validator.py`: URL validity, empty fields, duplicates, encoding corruption detection.
- `test_entity_resolver.py`: OpenAI/Anthropic/Cursor canonicalization, alias resolution, fuzzy matching, mapping log audit trail.
- `test_llm_orchestrator.py`: Multi-tier fallback chain, 413 HTML/content chunking, 429 exponential backoff retry with jitter, deterministic rule extractor.
- `test_signal_ingestion.py`: Strict 24-hr freshness window enforcement, relative date parsing (*"2 hours ago"*), RFC-2822 parsing, role family classification.
- `test_product_collector.py`: RSS extraction, tagline cleaning, pricing model inference (`FREE`, `FREEMIUM`, `PAID`, `ENTERPRISE`).
- `test_research_collector.py`: arXiv & Papers with Code ingestion, text cleaning, Crossref filtering.
- `test_startup_collector.py`: YC AI startup parsing, employee count extraction, canonical naming.
- `test_github_collector.py` & `test_github_quality.py`: Repository relevance classification and rate limit handling.

---

## Deliverables & Google Sheets Submission Guide

The assessment requires two deliverables for submission via the [Submission Form](https://forms.gle/3JJhukomumTFueRW7):

### Deliverable 1: Data Output (Google Sheets)
A public Google Sheet link containing 6 tabs:
1. **Startups:** 1,000 rows (Canonical startup name, employee count, source URL, ISO timestamp)
2. **Products:** 1,000 rows (Product name, canonical maker/startup, pricing model enum, source URL)
3. **Research Papers:** 1,000 rows (Title, authors, arXiv/paper URL, GitHub repository, live GitHub stars)
4. **Jobs:** All 24-hr fresh jobs found across 5 job boards (Canonical company, date, remote flag, role family)
5. **News:** All 24-hr fresh news found across 5 AI news sources (Title, published date, summary, full text)
6. **Entity Mapping Log:** Audit trail mapping raw messy strings to canonical names with confidence scores

#### How to import into Google Sheets:
1. Open [Google Sheets](https://sheets.new).
2. Click **File &rarr; Import &rarr; Upload**.
3. Select `exports/GraphOne_AI_Intelligence_Pipeline_Submission.xlsx` from this repository.
4. Choose **Replace spreadsheet** and click **Import data**. All 6 tabs will appear with formatted columns.
5. In the top right corner, click **Share &rarr; General access &rarr; Anyone with the link can view &rarr; Copy link**.

### Deliverable 2: Engineering Output (GitHub Repository)
Submit the link to your GitHub repository containing:
- **`README.md`**: Complete architecture guide and setup instructions (this file).
- **`src/`**: Modular source code for crawler, LLM orchestrator, signal ingester, and entity resolver.
- **`architecture.pdf`**: 3-page comprehensive technical design documentation.

---

## Canonical Entity Schemas

### Startup Entity
```json
{
  "schemaVersion": "1.0",
  "recordType": "STARTUP",
  "source": { "name": "Y Combinator", "url": "https://www.ycombinator.com/companies/stripe" },
  "content": {
    "entityName": "Stripe",
    "data": { "employeeCount": 8000, "location": "San Francisco, CA" }
  },
  "collectedAt": "2026-11-23T10:00:00Z"
}
```

### Product Entity
```json
{
  "schemaVersion": "1.0",
  "recordType": "PRODUCT",
  "source": { "name": "Product Hunt", "url": "https://www.producthunt.com/products/polymail" },
  "content": {
    "productName": "Polymail",
    "startupName": "Polymail",
    "pricingModel": "FREEMIUM",
    "description": "A simple, beautiful, and powerful email client."
  },
  "collectedAt": "2026-11-23T10:00:00Z"
}
```

### Research Paper Entity
```json
{
  "schemaVersion": "1.0",
  "recordType": "RESEARCH_PAPER",
  "content": {
    "title": "Odyssey: A Public GPU-Based Code for Kerr Spacetime",
    "authors": ["Leon Geiger", "AI Team"],
    "paper_url": "https://arxiv.org/abs/1601.02063",
    "github_url": "https://github.com/LeonGeiger/Kerr",
    "github_stars": 42,
    "published_date": "2016-01-01T00:00:00Z"
  },
  "collectedAt": "2026-11-23T10:00:00Z"
}
```

### Job Entity
```json
{
  "schemaVersion": "1.0",
  "recordType": "JOB",
  "source": { "name": "RemoteOK", "url": "https://remoteok.com/l/12345" },
  "content": {
    "company": "Anthropic",
    "title": "Senior Machine Learning Engineer",
    "date": "2026-11-23T04:15:00Z",
    "is_remote": true,
    "role_family": "Engineering"
  },
  "collectedAt": "2026-11-23T10:00:00Z"
}
```

### News Entity
```json
{
  "schemaVersion": "1.0",
  "recordType": "NEWS",
  "source": { "name": "TechCrunch AI", "url": "https://techcrunch.com/2026/11/23/ai-model" },
  "content": {
    "title": "Frontier AI Models Achieve New Autonomous Benchmarks",
    "published_date": "2026-11-23T08:30:00Z",
    "summary": "Researchers announced breakthroughs in autonomous multi-agent pipelines.",
    "full_text": "Detailed article contents..."
  },
  "collectedAt": "2026-11-23T10:00:00Z"
}
```

---

## Authors & Verification

- **Candidate:** Guru Arunachalam ([guruarunachalam17@gmail.com](mailto:guruarunachalam17@gmail.com))
- **Role:** AI Engineer Assessment (GraphOne / FrontierAtlas)
- **Submission Form:** [https://forms.gle/3JJhukomumTFueRW7](https://forms.gle/3JJhukomumTFueRW7)
