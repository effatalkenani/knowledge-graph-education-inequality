# Wales Education Geospatial Knowledge Graph

A Neo4j knowledge graph and Streamlit demonstrator for exploring educational inequality across Welsh administrative and statistical geographies.

## Project Contents

* `app.py` — Streamlit demonstrator, SCQ interface, map explorer and natural-language parser.
* `load_to_neo4j.py` — source-data preparation, geometry processing and Neo4j loading.
* `data/` — directory expected by the loader for the source datasets. Large source files are supplied separately through Microsoft Teams.
* `requirements.txt` — required Python packages.
* `.env.example` — environment-variable template.
* `education-inequality-project.dump` — Neo4j database dump supplied separately through Microsoft Teams.

## Separately Supplied Files

The complete `QPKG-Project-Files` folder is supplied separately through Microsoft Teams. It contains:

* the Neo4j database dump and backup;
* the complete source datasets;
* the large YAGO2geo Turtle (`.ttl`) and N-Triples (`.nt`) files;
* the larger spreadsheet and geospatial source files; and
* copies of the implementation files.

These files are not committed to this repository because some exceed GitHub’s web-upload or repository file-size limits. The GitHub repository contains the application code, loader, configuration template, requirements file and documentation needed to understand and run the project.

## Database

* Neo4j Aura source version: `5.27-aura`
* Local restored version: `2026.07.1`
* Database name: `education-inequality-project`
* Nodes: `49,486`
* Relationships: `271,835`

## Local Setup

### 1. Restore the database

Obtain `education-inequality-project.dump` from the separately supplied `QPKG-Project-Files/database` folder.

Create a Neo4j Desktop instance compatible with Neo4j `2026.07.1`, then restore:

```text
education-inequality-project.dump
```

Use this database name:

```text
education-inequality-project
```

### 2. Install the Python packages

From the project directory, run:

```bash
python -m pip install -r requirements.txt
```

### 3. Configure the environment

Copy:

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

The Neo4j password is the password created for the local Neo4j instance. The Gemini key must be supplied for the target deployment.

The completed `.env` file is excluded from version control.

### 4. Run the application

Start the Neo4j database, then run:

```bash
python -m streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Switching between Local and Cloud

> **Important:** The database connection mode is controlled by the `APP_MODE` environment variable. To use the restored Neo4j Desktop database, set `APP_MODE=LOCAL`. To connect to Neo4j Aura, change it to `APP_MODE=CLOUD`. No changes to `app.py` or `load_to_neo4j.py` are required.

## Cloud Configuration

To connect the application to Neo4j Aura, set:

```env
APP_MODE=CLOUD
NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=
NEO4J_DATABASE=
OPENAI_API_KEY=
```

For Streamlit Community Cloud, add these values under the application’s **Secrets** settings rather than committing them to GitHub.

## Natural-Language Parser

* Provider: Google Gemini through its OpenAI-compatible endpoint
* Model: `gemini-3.6-flash`
* Fallback: deterministic rule-based parser
* Endpoint:

```text
https://generativelanguage.googleapis.com/v1beta/openai/
```

If Gemini is temporarily unavailable, the application reports the service condition and uses the rule-based parser.

## Data Loading

The complete graph can be restored directly from the database dump supplied through Microsoft Teams.

To reconstruct the graph from the source data instead, copy the separately supplied source datasets into the project’s `data/` directory, configure the database connection, and run:

```bash
python load_to_neo4j.py
```

The loader uses `MERGE` to prevent duplicate nodes and relationships when a loading stage is rerun.

## Security

Credentials and API keys are read from environment variables or Streamlit Secrets. The following files are excluded from version control:

```text
.env
.streamlit/secrets.toml
*.backup
*.dump
```
