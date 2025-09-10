import streamlit as st
import requests
import datetime
import pytz
import re
import pandas as pd
import plotly.express as px

# NEIS API 기본값
ATPT_OFCDC_SC_CODE = "B10"  # 서울시교육청
SD_SCHUL_CODE = "7010806"   # 상암고등학교

def get_meal(date_str):
    """특정 날짜 급식 조회 (YYMMDD 형식)"""
    url = (
        "https://open.neis.go.kr/hub/mealServiceDietInfo"
        f"?ATPT_OFCDC_SC_CODE={ATPT_OFCDC_SC_CODE}"
        f"&SD_SCHUL_CODE={SD_SCHUL_CODE}"
        f"&Type=json&MLSV_YMD={date_str}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "mealServiceDietInfo" not in data:
            return None

        rows = data["mealServiceDietInfo"][1]["row"]
        result = []
        for r in rows:
            dishes = r["DDISH_NM"]
            clean = dishes.replace("<br/>", "\n")
            clean = re.sub(r"\d|\(|\)|\.", "", clean).strip()

            nutrition = r.get("NTR_INFO", "") or ""
            cal_info = r.get("CAL_INFO", "") or ""
            result.append((clean, nutrition, cal_info))
        return result
    except Exception:
        return None

def parse_ntr_info(ntr: str, cal: str) -> pd.DataFrame | None:
    """학교 급식 영양정보 문자열 파싱"""
    pairs = []
    s = ntr.replace("<br/>", "/").replace("\n", "/")
    tokens = [t.strip() for t in s.split("/") if t.strip()]
    for token in tokens:
        m = re.match(r"(.+?)\((.+?)\)\s*:\s*([\d\.]+)", token)
        if m:
            label = m.group(1)
            value = float(m.group(3))
            unit = m.group(2)
            pairs.append((label, value, unit))

    if cal:
        m = re.match(r"([\d\.]+)", cal)
        if m:
            value = float(m.group(1))
            pairs.append(("에너지", value, "Kcal"))

    if not pairs:
        return None
    return pd.DataFrame(pairs, columns=["영양소", "값", "단위"])

# --- UI 시작 ---
st.title("🍽 상암고 급식 조회")

# 오늘 날짜
kst = pytz.timezone("Asia/Seoul")
now = datetime.datetime.now(kst).date()

# 날짜 선택
selected_date = st.date_input("날짜 선택", now)
date_str = selected_date.strftime("%y%m%d")

meal_info = get_meal(date_str)

if meal_info:
    for dishes, ntr, cal in meal_info:
        st.write("")  # 메뉴와 영양정보 사이 공백

        col1, col2 = st.columns([2, 2])
        with col1:
            # 메뉴 글씨 크기만 키우고 줄바꿈 유지
            st.markdown(
                f"<p style='font-size:18px; white-space: pre-line;'>{dishes}</p>",
                unsafe_allow_html=True
            )

        df = parse_ntr_info(ntr, cal)
        if df is not None and not df.empty:
            with col2:
                view_option = st.selectbox(
                    label="",
                    options=["막대그래프", "원 그래프", "표"],
                    key=f"view_{dishes}",
                    label_visibility="collapsed"
                )

                if view_option == "표":
                    st.dataframe(
                        df.style.bar(subset=["값"], color="#FF4B4B"),
                        use_container_width=True
                    )
                elif view_option == "막대그래프":
                    fig = px.bar(df, x="영양소", y="값", text="값",
                                 color_discrete_sequence=["#FF4B4B"],
                                 labels={"값": "", "영양소": ""})
                    fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig, use_container_width=True)
                elif view_option == "원 그래프":
                    # 원 그래프에서는 '에너지' 제외
                    df_pie = df[df["영양소"] != "에너지"]
                    fig = px.pie(df_pie, names="영양소", values="값", color="영양소",
                                 color_discrete_sequence=px.colors.qualitative.Pastel,
                                 labels={"값": "", "영양소": ""})
                    fig.update_traces(textinfo="label+percent")
                    fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("ℹ️ 영양정보를 불러오지 못했습니다.")
else:
    st.warning("해당 날짜에는 급식 정보가 없습니다.")
