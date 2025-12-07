import sqlite3
import cwa  # 匯入上面的 cwa.py

DB_NAME = "weather.db"

def update_database():
    print("1. 開始抓取氣象局最新資料...")
    data = cwa.get_forecast_data()
    
    if not data:
        print("❌ 抓取失敗，不更新資料庫。")
        return

    print(f"2. 抓取成功，共 {len(data)} 筆。正在寫入 SQLite...")
    
    # 連線到 SQLite (如果檔案不存在會自動建立)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 建立 Table (如果不存在的話)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            wx TEXT,
            pop TEXT,
            min_t TEXT,
            max_t TEXT,
            time_desc TEXT
        )
    ''')

    # 清空舊資料 (因為我們要存最新的)
    cursor.execute('DELETE FROM forecast')

    # 插入新資料
    for item in data:
        cursor.execute('''
            INSERT INTO forecast (city, wx, pop, min_t, max_t, time_desc)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (item['city'], item['wx'], item['pop'], item['min_t'], item['max_t'], item['time_desc']))

    conn.commit()
    conn.close()
    print("✅ 資料庫更新完成！(weather.db)")

if __name__ == "__main__":
    update_database()