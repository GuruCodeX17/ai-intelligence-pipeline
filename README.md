# AI Intelligence Data Pipeline



## Overview

A Python-based pipeline that collects, processes, and validates AI-related information from multiple sources.



## Features

- Collect AI research papers from arXiv and Crossref.

- Collect AI and machine learning repositories from GitHub.

- Classify GitHub repositories by relevance.

- Collect AI products from Product Hunt RSS.

- Collect AI startups from a community-maintained Y Combinator directory mirror.

- Validate datasets for missing fields, duplicates, invalid URLs, and encoding issues.

- Store raw and processed data in JSON format.



## Technologies

- Python 3.13+

- Requests

- Feedparser

- BeautifulSoup

- Pandas

- Pydantic

- Pytest

- uv



## Installation



```bash

uv sync

```



## Run the Pipeline



```bash

uv run python main.py

```



## Run Tests



```bash

uv run python -m pytest -v

```



## Project Outputs



\*\*Raw datasets\*\*

- data/raw/research\_papers.json

- data/raw/github\_repositories.json

- data/raw/ai\_products.json

- data/raw/ai\_startups.json



\*\*Processed datasets\*\*

- data/processed/github\_quality\_results.json

- data/processed/data\_validation\_report.json



## Project Status

Core data collection, GitHub quality processing, data validation, and automated testing are implemented.


