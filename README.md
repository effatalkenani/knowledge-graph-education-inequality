# Education Inequality Spatial Analysis with Qualitative Place Knowledge Graphs

A Neo4j knowledge graph and Streamlit demonstrator for exploring educational inequality across Welsh administrative and statistical geographies.

## Live Demonstrator

The deployed Streamlit demonstrator is available at:

[Open the Wales Education Knowledge Graph demonstrator](https://knowledge-graph-education-inequality-j2pdrhnemloecnkg3bherf.streamlit.app/)

## Service Availability

The demonstrator uses Streamlit Community Cloud and a Neo4j Aura database. If either service has been paused after a period of inactivity, the application may take a minute or two to start. During this time, it may display a loading message or report that the database is not connected.

If the application does not load:

1. Confirm that the Neo4j Aura instance is running.
2. Open or reboot the application through Streamlit Community Cloud.
3. Wait one or two minutes, then refresh the application.

A temporary loading or connection message does not indicate that the project data are missing.

## Project Contents

- `app.py` — Streamlit demonstrator containing the spatial query interface, map explorer, school exploration workflow and natural-language parser.
- `load_to_neo4j.py` — source-data preparation, geometry processing and Neo4j loading script.
- `data/` — source datasets used to construct the knowledge graph.
- `database/education-inequality-project.dump` — Neo4j database dump containing the constructed QPKG.
- `scraping/` — scripts and supporting files used to collect additional school attributes from My Local School.
- `requirements.txt` — required Python packages.
- `.env.example` — environment-variable configuration template.
- `README.md` — project setup and execution instructions.

## Database

- Neo4j Aura source version: `5.27-aura`
- Local restored version: `2026.07.1`
- Database name: `education-inequality-project`
- Nodes: `49,486`
- Relationships: `271,835`

## Local Setup

### 1. Restore the Database

Create a compatible Neo4j Desktop instance and restore the database from:

```text
database/education-inequality-project.dump
```

Use the following database name:

```text
education-inequality-project
```

### 2. Install the Python Packages

From the project directory, run:

```bash
python -m pip install -r requirements.txt
```

### 3. Configure the Environment

Create a copy of:

```text
.env.example
```

Rename the copy to:

```text
.env
```

For local operation, set:

```env
APP_MODE=LOCAL
LOCAL_NEO4J_PASSWORD=PUT_YOUR_LOCAL_NEO4J_PASSWORD_HERE
OPENAI_API_KEY=PUT_YOUR_GEMINI_API_KEY_HERE
```

`LOCAL_NEO4J_PASSWORD` must contain the password created for the local Neo4j instance.

`OPENAI_API_KEY` must contain a valid Gemini API key used through the OpenAI-compatible endpoint.

The completed `.env` file should not be shared because it contains credentials.

### 4. Run the Application

Start the Neo4j database, then run:

```bash
python -m streamlit run app.py
```

Open the following address in a web browser:

```text
http://localhost:8501
```

## Switching Between Local and Cloud Modes

The database connection mode is controlled by the `APP_MODE` environment variable.

For the restored Neo4j Desktop database, use:

```env
APP_MODE=LOCAL
```

To connect to Neo4j Aura, use:

```env
APP_MODE=CLOUD
```

No changes to `app.py` or `load_to_neo4j.py` are required when switching modes.

## Cloud Configuration

For Neo4j Aura, configure:

```env
APP_MODE=CLOUD
NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=
NEO4J_DATABASE=
OPENAI_API_KEY=
```

When deploying through Streamlit Community Cloud, enter these values in the application's **Secrets** settings. Do not place credentials directly in the source code.

## Natural-Language Parser

- Provider: Google Gemini through its OpenAI-compatible endpoint
- Model: `gemini-3.6-flash`
- Fallback: deterministic rule-based parser
- Endpoint:

```text
https://generativelanguage.googleapis.com/v1beta/openai/
```

If Gemini is unavailable, the application reports the service condition and uses the deterministic rule-based parser.

## Data Loading

The completed graph can be restored directly from:

```text
database/education-inequality-project.dump
```

To reconstruct the graph from the source datasets instead, place the required files in the `data/` directory, configure the database connection and run:

```bash
python load_to_neo4j.py
```

The loader uses `MERGE` operations to prevent duplicate nodes and relationships when a loading stage is rerun.

## School Data Collection

The `scraping/` directory contains the scripts and supporting files used to collect the additional school attributes from My Local School.

Run the following commands from the project directory.

First, move into the scraping directory:

```bash
cd scraping
```

Then extract the school list from the saved search-results page:

```bash
python extract_school_list.py
```

This script reads:

```text
search_page.html
```

and produces:

```text
school_list.json
```

Next, run the school-detail scraper:

```bash
python mls_ultimate_scraper.py
```

The scraper reads `school_list.json`, collects the corresponding school pages and produces:

```text
mls_output/schools.jsonl
mls_output/welsh_schools_data_full.csv
```

The `schools.jsonl` file acts as a checkpoint, allowing an interrupted collection process to resume. During execution, individual school pages may also be stored in `mls_output/html_cache/`. This cache is optional and does not need to be included in the submitted project files because missing pages can be downloaded again.

The cleaned final school dataset used by the graph-loading process is included in the main `data/` directory.

## Security

Database credentials and API keys are read from environment variables or Streamlit Secrets. They are not stored directly in the source code.

The following sensitive or generated files should not be shared publicly:

```text
.env
.streamlit/secrets.toml
*.backup
```

Before submitting or sharing the project, confirm that no passwords, database credentials or API keys are included.
