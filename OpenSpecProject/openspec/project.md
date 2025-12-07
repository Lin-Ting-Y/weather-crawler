# Project Context

## Purpose
Build a real-time Taiwan Weather Dashboard using **Streamlit** that mimics the UI logic of the [CWA Observation Page](https://www.cwa.gov.tw/V8/C/W/OBS_Temp.html). The system fetches real-time observation data (API `O-A0003-001`), persists it to a local SQLite database (`sqlitedata.db`), and visualizes temperature data with location filtering.

## Tech Stack
- **Language**: Python 3.9+
- **Frontend Framework**: Streamlit (No Flask/HTML)
- **Data Engineering**: Pandas, SQLite3, Requests
- **Tooling**: OpenSpec (for spec adherence)

## Project Conventions

### Global File Naming (Mandatory)
- **Auto-numbering**: All executable scripts must start with a 2-digit prefix.
	- `01_sync_data.py`: Data ingestion script.
	- `02_app.py`: Streamlit dashboard application.
	- `03_utils.py`: Shared helper functions (if needed).

### Data Persistence
- **Database File**: Must be named **`sqlitedata.db`**.
- **Schema Strategy**: Flatten nested JSON into a relational table `station_observations` containing at least: `station_name`, `city`, `temperature`, `weather_status`, `update_time`.

### Architecture Patterns
- **Decoupled Ingestion**: The web app (`02_app.py`) reads *only* from SQLite. It does not fetch from the API directly to ensure speed and stability.
- **Batch Update**: `01_sync_data.py` is responsible for fetching from CWA and updating SQLite.

## Domain Context
- **Source**: CWA OpenData API `O-A0003-001` (Real-time Weather Observation).
- **Key Metrics**:
	- `AirTemperature` (Core metric for the dashboard).
	- `Weather` (Weather phenomenon for icons/text).
	- `StationName` & `GeoInfo` (For location dropdown filtering).
- **UI Reference**: Replicate the interaction of the CWA OBS page:
	1. User selects a region/city via a **Dropdown**.
	2. Dashboard displays a grid/list of stations with their current temperatures.

## Important Constraints
- **API Key**: Use `CWA-5D2BD77F-1B94-40C6-A752-E8DF4FA8D92F`.
- **Error Handling**: Graceful fallback if `sqlitedata.db` is missing (prompt user to run script `01`).
- **Performance**: Streamlit app should cache data loading from SQLite if necessary.

## External Dependencies
- CWA OpenData API: `https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001`
- Python packages: `streamlit`, `pandas`, `requests`
