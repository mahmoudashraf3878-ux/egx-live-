import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

st.set_page_config(
    page_title="شاشة التداول اللحظي - EGX",
    page_icon="⚡",
    layout="wide"
)

SHORT_SELLING_TICKERS = {
    "EFID", "JUFO", "EAST", "AMOC", "SKPC", "ABUK", "RMDA", "MFPC", "MCQE",
    "EGAL", "ALCN", "ETEL", "ISPH", "ADIB", "COMI", "HELI", "PHDC", "GBCO",
    "EMFD", "VALU", "RAYA", "HRHO", "BTFH", "TMGH", "ORAS", "CLHO", "CCAP",
    "EFIH", "FWRY", "OCDI", "XTRE"
}

def fetch_realtime_data():
    cairo_now = datetime.now(pytz.timezone('Africa/Cairo'))
    url = "https://www.mubasher.info/api/1/stocks/market_summary?country=eg"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.mubasher.info/countries/eg/stock-market",
        "Accept": "application/json"
    }

    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code != 200:
            return [], cairo_now
        stocks = res.json().get("stocks", [])
    except Exception:
        return [], cairo_now

    qualified = []
    for s in stocks:
        symbol = str(s.get("ticker", "")).strip().upper()
        name = s.get("name", symbol)
        last_price = s.get("lastPrice") or 0.0
        change_p = s.get("changePercentage") or 0.0
        turnover = s.get("turnover") or 0.0
        high_price = s.get("highPrice") or last_price
        low_price = s.get("lowPrice") or last_price

        if last_price <= 0:
            continue

        turnover_m = turnover / 1_000_000.0

        if turnover_m >= 20.0 and (1.5 <= change_p <= 20.0):
            decimals = 3 if last_price < 1.0 else 2
            is_shortable = "⚡️ شورت" if symbol in SHORT_SELLING_TICKERS else "—"

            qualified.append({
                "الكود": symbol,
                "اسم السهم": name,
                "السعر اللحظي": round(last_price, decimals),
                "نسبة التغير %": round(change_p, 2),
                "أعلى سعر": round(high_price, decimals),
                "أدنى سعر": round(low_price, decimals),
                "السيولة (مليون)": round(turnover_m, 2),
                "الشورت": is_shortable
            })

    return qualified, cairo_now

st.title("⚡ شاشة المراقبة اللحظية للأسهم (EGX Real-Time)")

with st.sidebar:
    st.header("⚙️ الفلاتر والتحكم")
    refresh_sec = st.slider("معدل التحديث (بالثواني):", min_value=3, max_value=30, value=5)
    min_liq = st.number_input("الحد الأدنى للسيولة (مليون ج.م):", min_value=1.0, value=20.0, step=5.0)
    min_pct = st.number_input("الحد الأدنى للصعود %:", min_value=0.5, value=1.5, step=0.5)

data_list, update_time = fetch_realtime_data()

col1, col2, col3 = st.columns(3)
col1.metric("⏰ آخر نبضة", update_time.strftime('%I:%M:%S %p'))
col2.metric("🎯 عدد الفرص", len(data_list))
total_turnover = sum(x["السيولة (مليون)"] for x in data_list) if data_list else 0
col3.metric("💰 إجمالي السيولة", f"{round(total_turnover, 1)} م.ج")

st.divider()

if data_list:
    df = pd.DataFrame(data_list)
    df = df[(df["السيولة (مليون)"] >= min_liq) & (df["نسبة التغير %"] >= min_pct)]
    df = df.sort_values(by="نسبة التغير %", ascending=False).reset_index(drop=True)

    st.dataframe(
        df.style.format({
            "السعر اللحظي": "{:.2f}",
            "نسبة التغير %": "+{:.2f}%",
            "أعلى سعر": "{:.2f}",
            "أدنى سعر": "{:.2f}",
            "السيولة (مليون)": "{:.2f} م"
        }),
        use_container_width=True,
        height=520
    )
else:
    st.warning("⏳ لا توجد أسهم مطابقة للشروط في هذه اللحظة...")

time.sleep(refresh_sec)
st.rerun()
