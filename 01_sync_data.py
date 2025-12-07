from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
import urllib3

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. API 設定
API_KEY = "CWA-5D2BD77F-1B94-40C6-A752-E8DF4FA8D92F"
API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
DB_NAME = "data.db"
# 設定本地檔案路徑 (如果有下載好的 JSON 可優先讀取)
LOCAL_JSON_PATH = Path.home() / "Downloads" / "F-A0010-001.json"

def init_db():
    # 刪除舊檔確保 Schema 更新
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print(f"🗑️ 已刪除舊資料庫 {DB_NAME} (為了更新欄位結構)...")
        except:
            pass

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 2. 建立更詳細的 Schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            forecast_date TEXT, 
            min_temp REAL,
            max_temp REAL,
            description TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ 資料庫 data.db 已建立 (包含日期欄位)。")


def _load_payload() -> Dict[str, Any]:
    """優先讀取本地檔案，若無則下載 API"""
    if LOCAL_JSON_PATH.exists():
        print(f"📂 讀取本地檔案: {LOCAL_JSON_PATH}")
        with LOCAL_JSON_PATH.open("r", encoding="utf-8-sig") as handle: # 加上 utf-8-sig 處理 BOM
            return json.load(handle)

    print("☁️ 本地無檔案，正在連線 CWA API...")
    params = {"Authorization": API_KEY, "downloadType": "WEB", "format": "JSON"}
    response = requests.get(API_URL, params=params, verify=False, timeout=30)
    response.raise_for_status()
    # 強制設定編碼為 utf-8，避免亂碼
    response.encoding = "utf-8"
    return response.json()


def _iter_forecast_locations(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """解析農業氣象預報結構，支援多種 JSON 路徑格式"""
    cwa = payload.get("cwaopendata", {})
    
    # 定義可能的 data 區塊路徑
    # 路徑 1: dataset -> data (部分 API 版本)
    # 路徑 2: resources -> resource -> data (您目前的 JSON 版本)
    potential_data_blocks = []

    # 檢查 dataset 路徑
    dataset = cwa.get("dataset", {})
    if "data" in dataset:
        potential_data_blocks.append(dataset.get("data", {}))

    # 檢查 resources 路徑
    resources = cwa.get("resources", {})
    resource = resources.get("resource", {})
    # resource 有時是列表，有時是字典，這裡做個簡單檢查
    if isinstance(resource, dict):
        if "data" in resource:
            potential_data_blocks.append(resource.get("data", {}))
    elif isinstance(resource, list):
        for res in resource:
            if isinstance(res, dict) and "data" in res:
                potential_data_blocks.append(res.get("data", {}))

    found_locations = False
    
    for block in potential_data_blocks:
        agr_forecasts = block.get("agrWeatherForecasts", {})
        weather_forecasts = agr_forecasts.get("weatherForecasts", {})
        locations = weather_forecasts.get("location")

        if isinstance(locations, list):
            found_locations = True
            for entry in locations:
                if isinstance(entry, dict):
                    yield entry
            # 如果在某個 block 找到了資料，通常就可以結束了，避免重複
            break
            
    if not found_locations:
        # 如果都沒找到，印出 debug 訊息幫助除錯
        print("⚠️ 在 agrWeatherForecasts 路徑下未找到 location 資料。")


def _iter_tide_locations(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Fallback: 解析潮汐預報結構"""
    # 同樣嘗試在多個位置尋找 dataset
    cwa = payload.get("cwaopendata", {})
    dataset = cwa.get("dataset", {})
    locations = dataset.get("location")
    
    if isinstance(locations, list):
        for entry in locations:
            if isinstance(entry, dict):
                yield entry


def _extract_temperature(element: Optional[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    if not element:
        return None
    daily = element.get("daily")
    if isinstance(daily, list):
        return [item for item in daily if isinstance(item, dict)]
    return None


def fetch_and_save():
    print("📡 開始執行資料同步...")
    try:
        payload = _load_payload()
    except Exception as exc:
        print(f"❌ 下載或解析 JSON 失敗：{exc}")
        return

    # 使用 context manager 自動關閉連線
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        insert_count = 0

        # 嘗試解析農業氣象
        print("🔍 嘗試解析農業氣象結構...")
        forecasts = list(_iter_forecast_locations(payload))
        
        if forecasts:
            print(f"✅ 偵測到農業氣象資料 (共 {len(forecasts)} 個地區)，開始寫入...")
            for entry in forecasts:
                loc_name = entry.get("locationName")
                elements = entry.get("weatherElements", {})
                
                min_series = _extract_temperature(elements.get("MinT"))
                max_series = _extract_temperature(elements.get("MaxT"))
                weather_series = _extract_temperature(elements.get("Wx"))

                # 確保三個序列都存在
                if not (min_series and max_series and weather_series):
                    print(f"⚠️ 跳過 {loc_name}: 資料不完整")
                    continue

                # 取三者最小長度，避免 index out of range
                limit = min(len(min_series), len(max_series), len(weather_series))
                
                for idx in range(limit):
                    min_item = min_series[idx]
                    max_item = max_series[idx]
                    wx_item = weather_series[idx]

                    date_str = min_item.get("dataDate") or max_item.get("dataDate")
                    min_temp = min_item.get("temperature")
                    max_temp = max_item.get("temperature")
                    description = wx_item.get("weather")

                    try:
                        cursor.execute(
                            """
                            INSERT INTO weather (location, forecast_date, min_temp, max_temp, description)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                loc_name,
                                date_str,
                                float(min_temp) if min_temp is not None else None,
                                float(max_temp) if max_temp is not None else None,
                                description,
                            ),
                        )
                        insert_count += 1
                    except Exception as exc:
                        print(f"⚠️ 寫入 {loc_name} {date_str} 失敗：{exc}")

        else:
            # Fallback 到潮汐模式
            print("⚠️ 未偵測到農業氣象資料，改用潮汐結構...")
            for entry in _iter_tide_locations(payload):
                loc_name = entry.get("locationName")
                times = entry.get("time", [])
                first = times[0] if isinstance(times, list) and times else {}
                start_time = first.get("startTime", "")
                
                date_str = start_time[:10] if len(start_time) >= 10 else start_time or "未知日期"
                description = start_time or "潮汐預報"

                cursor.execute(
                    """
                    INSERT INTO weather (location, forecast_date, min_temp, max_temp, description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (loc_name, date_str, 0.0, 0.0, description),
                )
                insert_count += 1

        conn.commit()

    if insert_count:
        print(f"🎉 成功寫入 {insert_count} 筆詳細資料！")
        print("➡️ 請執行 streamlit run 02_app.py 查看結果。")
    else:
        print("⚠️ 寫入 0 筆資料。請確認來源 JSON 格式是否正確。")

if __name__ == "__main__":
    init_db()
    fetch_and_save()