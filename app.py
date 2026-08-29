import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

st.set_page_config(
    page_title="شاشة التداول اللحظي (مباشر) - EGX",
    page_icon="⚡",
    layout="wide"
)

# ==========================================
# 1. إعدادات تليجرام وقائمة الشورت
# ==========================================
TELEGRAM_BOT_TOKEN = "8689608027:AAF5qs1kKQ4j9TJQHwMp5mw4RmcKpp4TkjI"
TELEGRAM_CHAT_ID = "1177462424"

SHORT_SELLING_TICKERS = {
    "EFID", "JUFO", "EAST", "AMOC", "SKPC", "ABUK", "RMDA", "MFPC", "MCQE",
    "EGAL", "ALCN", "ETEL", "ISPH", "ADIB", "COMI", "HELI", "PHDC", "GBCO",
    "EMFD", "VALU", "RAYA", "HRHO", "BTFH", "TMGH", "ORAS", "CLHO", "CCAP",
    "EFIH", "FWRY", "OCDI", "XTRE"
}

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    max_len = 3500
    success = False
    for i in range(0, len(text), max_len):
        chunk = text[i:i + max_len]
        try:
            res = requests.post(
                url,
                json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "Markdown"},
                timeout=10
            )
            if res.json().get("ok"):
                success = True
        except Exception:
            pass
        time.sleep(0.3)
    return success

# ==========================================
# 2. سحب البيانات اللحظية من مصدر مباشر (Zero Delay)
# ==========================================
def fetch_mubasher_realtime():
    cairo_now = datetime.now(pytz.timezone('Africa/Cairo'))
    url = "https://www.mubasher.info/api/1/stocks/market_summary?country=eg"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
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

# ==========================================
# 3. الواجهة التفاعلية
# ==========================================
st.title("⚡ شاشة المراقبة اللحظية (بيانات حية بدون تأخير)")

with st.sidebar:
    st.header("⚙️ الفلاتر والتحكم")
    refresh_sec = st.slider("معدل التحديث (بالثواني):", min_value=3, max_value=30, value=5)
    min_liq = st.number_input("الحد الأدنى للسيولة (مليون ج.م):", min_value=0.0, value=20.0, step=5.0)
    min_pct = st.number_input("الحد الأدنى للصعود %:", min_value=0.0, value=1.5, step=0.5)

    st.divider()
    st.subheader("📬 إشعارات تليجرام")
    send_test_btn = st.button("📤 إرسال التقرير اللحظي لتليجرام")

all_stocks, update_time = fetch_mubasher_realtime()

# تطبيق الفلاتر
filtered_stocks = [
    s for s in all_stocks
    if s["السيولة (مليون)"] >= min_liq and s["نسبة التغير %"] >= min_pct
]
filtered_stocks.sort(key=lambda x: x["نسبة التغير %"], reverse=True)

# إرسال التقرير يدوياً
if send_test_btn:
    if filtered_stocks:
        msg = f"📊 *تقرير مباشر لحظي ({update_time.strftime('%I:%M %p')})*\n\n"
        for s in filtered_stocks:
            short_str = " [⚡️ شورت]" if s["الشورت"] == "⚡️ شورت" else ""
            msg += f"• *{s['الكود']}* ({s['اسم السهم']}): `{s['السعر اللحظي']}` ج.م (+{s['نسبة التغير %']}%){short_str} | سيولة: `{s['السيولة (مليون)']}` م\n"
        if send_telegram(msg):
            st.sidebar.success("✅ تم إرسال التقرير بنجاح!")
    else:
        send_telegram(f"ℹ️ تقرير ({update_time.strftime('%I:%M %p')}): لا توجد أسهم مطابقة للشروط حالياً.")
        st.sidebar.info("ℹ️ تم إرسال إشعار بعدم وجود فرص.")

# المؤشرات السريعة
col1, col2, col3 = st.columns(3)
col1.metric("⏰ آخر تحديث لحظي", update_time.strftime('%I:%M:%S %p'))
col2.metric("🎯 عدد الفرص", len(filtered_stocks))
total_liq = sum(s["السيولة (مليون)"] for s in filtered_stocks)
col3.metric("💰 إجمالي السيولة للفرص", f"{round(total_liq, 1)} م.ج")

st.divider()

# جدول الأسهم
if filtered_stocks:
    df = pd.DataFrame(filtered_stocks)
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
