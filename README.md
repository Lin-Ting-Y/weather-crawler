# Weather Crawler Dashboard

Taiwan agricultural weather forecast ETL pipeline with a Streamlit dashboard. The
project ingests CWA open data (dataset `F-A0010-001`), stores the results in a
local SQLite database, and visualises the 7-day forecast for each location.

## 🌐 Live Demo

- Streamlit Cloud: https://weather-crawler.streamlit.app/

## ✨ Key Features

- Automated ETL (`01_sync_data.py`) that fetches or loads `F-A0010-001`
  forecasts and persists them into `data.db::weather`.
- Streamlit UI (`02_app.py`) that auto-builds the database when missing, offers
  per-location views, and an "全部地區" overview with aggregated metrics and
  trend lines.
- Local JSON fallback (`~/Downloads/F-A0010-001.json`) for development without
  network access.
- SQLite schema includes `location`, `forecast_date`, `min_temp`, `max_temp`,
  and daily weather description, keeping the dashboard lightweight and
  responsive.

## 🧰 Tech Stack

- Python 3.11+
- Requests, Pandas, Streamlit
- SQLite (built-in `sqlite3` module)

## 🧪 Local Setup & Workflow

1. **Clone the repository**
   ```bash
   git clone https://github.com/Lin-Ting-Y/weather-crawler.git
   cd weather-crawler
   ```

2. **Create / activate a virtual environment (optional but recommended)**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   If you do not want to use a requirements file, install the runtime packages
   manually:
   ```bash
   pip install streamlit pandas requests
   ```

4. **Generate the SQLite database**
   ```bash
   python 01_sync_data.py
   ```
   - The script attempts to read `~/Downloads/F-A0010-001.json` before hitting
     the live API.
   - It trims the database (drops + recreates) each time to keep the schema in
     sync.
   - Successful runs yield 42 rows (6 locations × 7 forecast days).

5. **Launch the dashboard**
   ```bash
   streamlit run 02_app.py
   ```
   - When `data.db` is absent, the app invokes `01_sync_data.py` automatically
     and shows the logs on the page.
   - The sidebar lets you pick a single location or the "全部地區" overview.
   - The dataframe view uses progress columns to highlight temperature ranges.

6. **Stop the app**
   - Hit `Ctrl+C` in the terminal running Streamlit.

## 🚀 Deploying to Streamlit Cloud

1. Push the repository to GitHub (e.g., `https://github.com/Lin-Ting-Y/weather-crawler`).
2. On https://share.streamlit.io/ select the repo and branch (`main`).
3. Configure the main module as `02_app.py`.
4. Streamlit Cloud installs dependencies from `requirements.txt`, runs the app,
   and, on first request, the app generates `data.db` automatically.

## 📂 Project Structure

```
├── 01_sync_data.py      # ETL script for CWA F-A0010-001 → SQLite
├── 02_app.py            # Streamlit dashboard with auto-sync support
├── F-A0010-001.json     # Sample dataset (optional local fallback)
├── README.md            # Project documentation (this file)
├── test/
│   └── test.py          # Placeholder test module
└── ...                  # Additional reference files / assets
```

## 📝 Operational Notes

- **API Key**: The script uses the built-in CWA test key. Replace `API_KEY` in
  `01_sync_data.py` if you have your own key with higher rate limits.
- **Local JSON fallback**: Apply `F-A0010-001.json` under your `Downloads`
  folder to work offline.
- **Database reset**: Each ETL run deletes the existing `data.db` to avoid stale
  schemas or duplicate rows.
- **Logging**: `01_sync_data.py` prints progress messages (in Traditional
  Chinese) indicating ETL status and inserted row counts.
- **Git ignore**: Binary artifacts (`*.db`, `__pycache__/`, etc.) are excluded
  from version control.

## 🩺 Troubleshooting

- **Dashboard shows no data**: Either `data.db` is missing or the ETL failed.
  Check the Streamlit page captions for ETL logs and re-run `01_sync_data.py` if
  needed.
- **Streamlit Cloud build fails**: Ensure `requirements.txt` exists and includes
  `streamlit`, `pandas`, and `requests`. The current deployment at
  https://weather-crawler.streamlit.app/ reflects the working configuration.
- **API timeout**: The script disables SSL verification to avoid cert-related
  issues. If fetching still fails, place a valid JSON payload under
  `~/Downloads/F-A0010-001.json` and rerun.

## 📄 License

MIT License © Lin-Ting-Y
