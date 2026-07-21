# Wales Education Inequality Spatial Analyser

A Cardiff University MSc Project exploring the use of Qualitative Place Knowledge Graphs to analyse educational inequality in Wales.

**Supervisor:** Prof. Alia Abdelmoty

--- 

## 🚀 Live Demo

The application is deployed and accessible via Streamlit Cloud:

**🔗 [https://knowledge-graph-education-inequality-j2pdrhnemloecnkg3bherf.streamlit.app/](https://knowledge-graph-education-inequality-j2pdrhnemloecnkg3bherf.streamlit.app/)**

![App Screenshot](https://files.manuscdn.com/user_upload_by_module/session_file/310519663081150898/nMQRebjZrGGcVGxM.webp)  <!-- You should replace this with a real screenshot URL -->

## 🎯 Project Overview

This project aims to provide a comprehensive spatial analysis tool for understanding educational inequality across Wales. By integrating multiple datasets, the application visualizes schools in relation to key deprivation and accessibility metrics. The core of the project is to build and leverage a qualitative place knowledge graph to uncover deeper insights and answer complex spatial queries.

This initial prototype focuses on data integration, interactive visualization, and providing a user-friendly interface for data exploration.

## ✨ Features

*   **Interactive Map:** A fully interactive map of Wales displaying all **1,446 schools**.
*   **Deprivation Analysis:** School markers are color-coded based on the **Welsh Index of Multiple Deprivation (WIMD) 2019** ranks, providing an immediate visual cue for inequality.
*   **Advanced Filtering:** Users can filter the data using a combination of manual filters:
    *   School Type (e.g., Primary, Secondary)
    *   Deprivation Level (High, Medium, Low)
    *   Transport Access (Near/Far from public transport stops)
    *   Local Authority
*   **Statistical Summaries:** Dynamic cards that update to show key statistics based on the current filters.
*   **Data Views:** Toggle between the interactive map, a detailed data table, and a (forthcoming) knowledge graph visualization.

## 🛠️ Technology Stack

*   **Language:** Python
*   **Web Framework:** Streamlit
*   **Data Manipulation:** Pandas
*   **Mapping:** Folium
*   **Graph Analysis:** NetworkX

## 📂 Data Sources

*   **Schools Data:** DataMapWales
*   **Deprivation Data:** WIMD 2019
*   **Transport Data:** National Public Transport Access Nodes (NaPTAN)

## ⚙️ Local Setup & Installation

To run this project locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/effatalkenani/knowledge-graph-education-inequality.git
    cd knowledge-graph-education-inequality
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required packages:**
    A `requirements.txt` file is included for easy setup.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Streamlit application:**
    The application is located in the `wales_edu_project` directory.
    ```bash
    streamlit run wales_edu_project/app.py
    ```

## 📄 Requirements File

For deployment and local setup, here is the content of `requirements.txt`:

```
streamlit
folium==0.14.0
pandas
networkx
openpyxl
streamlit-folium
```
