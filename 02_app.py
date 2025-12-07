import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).with_name("data.db")
SYNC_SCRIPT = Path(__file__).with_name("01_sync_data.py")

# 設定網頁標題與寬度佈局
st.set_page_config(page_title=" 農業氣象週報", page_icon="🌾", layout="wide")

# --- CSS 美化 (讓表格標頭變色) ---
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 24px;
    }
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

st.title("一週農業氣象預報")
st.markdown("資料來源：**CWA F-A0010-001** | 資料庫：**SQLite (data.db)**")

ALL_OPTION = "全部地區"


def ensure_database() -> bool:
    if DB_PATH.exists():
        return True
    if not SYNC_SCRIPT.exists():
        st.error("❌ 找不到 data.db，且缺少 01_sync_data.py。請確認專案檔案。")
        return False
    with st.spinner("首次使用，正在建立資料庫..."):
        try:
            result = subprocess.run(
                [sys.executable, str(SYNC_SCRIPT)],
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                st.caption(result.stdout)
            if result.stderr:
                st.caption(result.stderr)
        except subprocess.CalledProcessError as exc:
            st.error("自動同步資料失敗。請手動執行 01_sync_data.py。")
            if exc.stdout:
                st.error(exc.stdout)
            if exc.stderr:
                st.error(exc.stderr)
            return False
    return DB_PATH.exists()


if not ensure_database():
    st.stop()

if not os.path.exists(DB_PATH):
    st.error("❌ 找不到 data.db，請先執行 01_sync_data.py")
else:
    conn = sqlite3.connect(DB_PATH)
    # 關鍵修正：確保選取所有欄位，包含 forecast_date
    df = pd.read_sql_query("SELECT * FROM weather", conn)
    conn.close()
    
    if df.empty:
        st.warning("⚠️ 資料表是空的，請檢查同步程式。")
    else:
        # --- 1. 側邊欄篩選器 ---
        with st.sidebar:
            st.header("🔍 篩選條件")
            locations = df["location"].unique()
            options = [ALL_OPTION] + sorted(locations.tolist())
            selected_loc = st.selectbox("請選擇地區：", options)
            
            st.info("💡 說明：\n此資料來自 CWA 農業氣象預報，包含未來一週的每日溫度預測。")

        # 篩選出資料；選擇「全部地區」時保留所有紀錄
        if selected_loc == ALL_OPTION:
            filtered_df = df.copy()
        else:
            filtered_df = df[df["location"] == selected_loc].copy()

        parsed_dates = False
        try:
            filtered_df["forecast_date"] = pd.to_datetime(filtered_df["forecast_date"])
            sort_cols = ["forecast_date", "location"] if selected_loc == ALL_OPTION else ["forecast_date"]
            filtered_df = filtered_df.sort_values(sort_cols)
            parsed_dates = True
        except Exception:
            sort_cols = ["forecast_date", "location"] if selected_loc == ALL_OPTION else ["forecast_date"]
            filtered_df = filtered_df.sort_values(sort_cols)

        # --- 2. 顯示概況 ---
        if selected_loc == ALL_OPTION:
            st.subheader("🌍 全部地區總覽")
            avg_min = filtered_df["min_temp"].mean()
            avg_max = filtered_df["max_temp"].mean()
            unique_locations = filtered_df["location"].nunique()

            col1, col2, col3 = st.columns(3)
            col1.metric("平均最低溫", f"{avg_min:.1f} °C")
            col2.metric("平均最高溫", f"{avg_max:.1f} °C")
            col3.metric("地區數量", f"{unique_locations} 個")
        else:
            st.subheader(f"📍 {selected_loc} - 未來一週天氣概況")
            avg_min = filtered_df["min_temp"].mean()
            avg_max = filtered_df["max_temp"].mean()

            col1, col2, col3 = st.columns(3)
            col1.metric("平均最低溫", f"{avg_min:.1f} °C", delta="週平均")
            col2.metric("平均最高溫", f"{avg_max:.1f} °C", delta_color="inverse")
            col3.metric("資料筆數", f"{len(filtered_df)} 天份")

        # --- 3. 氣溫趨勢圖 (Line Chart) ---
        st.divider()
        st.subheader("📈 氣溫走勢圖")

        chart_data = None
        if not filtered_df.empty and parsed_dates:
            indexed = filtered_df.set_index("forecast_date")
            if selected_loc == ALL_OPTION:
                chart_data = (
                    indexed.resample("D")[["min_temp", "max_temp"]]
                    .mean()
                    .rename(columns={"min_temp": "平均最低溫", "max_temp": "平均最高溫"})
                )
            else:
                chart_data = indexed[["min_temp", "max_temp"]].rename(
                    columns={"min_temp": "最低溫", "max_temp": "最高溫"}
                )

        if chart_data is not None and not chart_data.empty:
            st.line_chart(
                chart_data,
                color=["#3498db", "#e74c3c"],
                height=300,
            )
        else:
            st.info("暫時無法繪製折線圖（日期格式可能有誤）。")

        # --- 4. 詳細資料表格 ---
        st.divider()
        st.subheader("📋 詳細預報數據")

        display_df = filtered_df.copy()
        if parsed_dates:
            display_df["forecast_date"] = display_df["forecast_date"].dt.strftime("%Y-%m-%d")

        if selected_loc == ALL_OPTION:
            display_df = display_df[["location", "forecast_date", "description", "min_temp", "max_temp"]]
            display_df.columns = [
                "地區 (Location)",
                "日期 (Date)",
                "天氣現象 (Description)",
                "最低溫 (°C)",
                "最高溫 (°C)",
            ]
        else:
            display_df = display_df[["forecast_date", "description", "min_temp", "max_temp"]]
            display_df.columns = [
                "日期 (Date)",
                "天氣現象 (Description)",
                "最低溫 (°C)",
                "最高溫 (°C)",
            ]

        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "最低溫 (°C)": st.column_config.ProgressColumn(
                    "最低溫",
                    format="%.1f°C",
                    min_value=0,
                    max_value=40,
                ),
                "最高溫 (°C)": st.column_config.ProgressColumn(
                    "最高溫",
                    format="%.1f°C",
                    min_value=0,
                    max_value=40,
                ),
            },
        )
