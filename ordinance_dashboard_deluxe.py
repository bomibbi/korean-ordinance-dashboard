# -*- coding: utf-8 -*-
# 지방자치단체 조례 통계 분석 대시보드 (연번 1부터 표시 + 탭 1~9 단일 라인 통합)

import os
from datetime import datetime
import re

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(page_title="조례 통계 분석", layout="wide", initial_sidebar_state="collapsed")

# CSS: 사이드바 완전 제거 + 메인 영역 확장 + 탭 강조
st.markdown("""
    <style>
    /* 사이드바 완전 제거 */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* 메인 영역 전체 너비 사용 */
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* 모든 탭의 기본 스타일 (메인 탭 스타일) */
    [data-baseweb="tab-list"] {
        gap: 5px;
        padding: 0px;
        border-bottom: 2px solid #e0e0e0 !important;
        background: transparent !important;
        /* 폭이 좁을 때 가로 스크롤 허용 */
        overflow-x: auto; white-space: nowrap;
    }
    
    button[data-baseweb="tab"] {
        height: 60px;
        padding: 0px 20px;
        background-color: transparent !important;
        border-radius: 0px !important;
        font-size: 20px !important;
        font-weight: 600 !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        box-shadow: none !important;
        color: #666 !important;
    }
    
    button[data-baseweb="tab"]:hover {
        color: #1f77b4 !important;
        background-color: rgba(31, 119, 180, 0.05) !important;
    }
    
    button[aria-selected="true"][data-baseweb="tab"] {
        color: #1f77b4 !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #1f77b4 !important;
        background-color: transparent !important;
    }
    
    /* 하위 탭만 별도 스타일 (덮어쓰기) */
    [data-baseweb="tab-panel"] [data-baseweb="tab-list"] {
        border-bottom: none !important;
        padding: 10px 0px;
    }
    
    [data-baseweb="tab-panel"] button[data-baseweb="tab"] {
        height: 45px !important;
        padding: 8px 20px !important;
        background-color: #f8f9fa !important;
        border-radius: 6px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        border: 1px solid #dee2e6 !important;
        color: #495057 !important;
        margin-right: 8px;
    }
    
    [data-baseweb="tab-panel"] button[aria-selected="true"][data-baseweb="tab"] {
        background-color: #495057 !important;
        color: white !important;
        border: 1px solid #495057 !important;
    }
    
    /* 탭 하이라이트 제거 */
    [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    
    [data-baseweb="tab-border"] {
        display: none !important;
    }
    
    /* 데이터 요약 메트릭 스타일 */
    [data-testid="stMetricValue"] {
        font-size: 18px;
        font-weight: bold;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 14px;
        font-weight: 600;
    }

    /* KPI 카드 */
    .kpi{background:#f0f2f6;padding:25px 30px;border-radius:10px;margin:20px 0 30px 0;}
    .kpi .title{font-size:18px;font-weight:700;margin-bottom:20px;color:#1f1f1f;}
    .kpi .grid{display:flex;justify-content:space-between;gap:20px;}
    .kpi .item{text-align:center;flex:1;}
    .kpi .item .label{font-size:13px;font-weight:600;color:#666;margin-bottom:8px;}
    .kpi .item .value{font-size:22px;font-weight:400;color:#1f1f1f;}
    </style>
""", unsafe_allow_html=True)


# -----------------------------
# 데이터 로드 (현행/연혁 선택)
# -----------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_XLSX = os.path.join(APP_DIR, "data", "korean_ordinance.xlsx")
HIST_PARQUET = os.path.join(APP_DIR, "data", "korean_ordinance_all.parquet")

# 메인 영역 상단에 데이터 유형 선택(사이드바는 숨겨져 있으므로)
data_mode = st.radio("데이터 유형 선택", ["현행", "연혁"], horizontal=True, index=0, help="동일한 9개 탭에 적용할 데이터 집합을 선택합니다.")

@st.cache_data(show_spinner=True)
def load_excel(path: str) -> pd.DataFrame:
    return pd.read_excel(path)

@st.cache_data(show_spinner=True)
def load_parquet(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)

# 데이터 로드
if data_mode == "현행":
    if not os.path.exists(CURRENT_XLSX):
        st.error(f"⚠️ 현행 데이터 파일을 찾을 수 없습니다: {CURRENT_XLSX}")
        st.info("GitHub의 data 폴더에 korean_ordinance.xlsx 파일을 업로드해주세요.")
        st.stop()
    with st.spinner("📂 (현행) 데이터 로딩 중..."):
        df = load_excel(CURRENT_XLSX)
else:
    if not os.path.exists(HIST_PARQUET):
        st.error(f"⚠️ 연혁 데이터 파일을 찾을 수 없습니다: {HIST_PARQUET}")
        st.info("GitHub의 data 폴더에 korean_ordinance_all.parquet 파일을 업로드해주세요.")
        st.stop()
    with st.spinner("🗂️ (연혁) 데이터 로딩 중..."):
        df = load_parquet(HIST_PARQUET)

# 필수 컬럼 확인: 지자체 유형 포함
required_cols = ["광역", "기초", "최종분야", "지방의회_기수", "지자체 유형"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"필수 컬럼이 없습니다: {', '.join(missing)}")
    st.write("현재 컬럼:", df.columns.tolist())
    st.stop()

# 데이터 정제
df = df.dropna(subset=["광역", "기초", "최종분야", "지방의회_기수"])
df["광역"] = df["광역"].astype(str).str.strip()
df["기초"] = df["기초"].astype(str).str.strip()
df["지자체 유형"] = df["지자체 유형"].astype(str).str.strip()
df["최종분야"] = df["최종분야"].astype(str).str.strip()
df["지방의회_기수"] = df["지방의회_기수"].astype(str).str.strip()

# 정렬용 숫자
def extract_number(x):
    if isinstance(x, str) and "분류불가" in x:
        return 0
    try:
        match = re.search(r'\d+', str(x))
        return int(match.group()) if match else 999
    except:
        return 999

df["_기수_정렬용"] = df["지방의회_기수"].apply(extract_number)

# 고유값
광역_list = sorted(df["광역"].dropna().unique().tolist())
분야_list = sorted(df["최종분야"].dropna().unique().tolist())

# 기수 정렬
기수_unique = df[["지방의회_기수", "_기수_정렬용"]].drop_duplicates()
기수_unique = 기수_unique.sort_values("_기수_정렬용")
기수_list = 기수_unique["지방의회_기수"].tolist()
st.session_state["_기수정렬"] = 기수_list

# 구분/표시용
df["is_광역자체"] = df["광역"] == df["기초"]
df["기초_full"] = df["광역"] + " " + df["기초"]

# -----------------------------
# 헤더 및 데이터 요약
# -----------------------------
st.title("📊 지방자치단체 조례 통계 분석 대시보드")
이_조례수 = len(df)
광역_unique = len(광역_list)
기초_unique = df[~df["is_광역자체"]][['광역', '기초']].drop_duplicates().shape[0]
분야_unique = len(분야_list)
기수_range = f"{기수_list[0]} ~ {기수_list[-1]}"

st.markdown(f"""
<div class="kpi">
  <div class="title">📈 데이터 요약</div>
  <div class="grid">
    <div class="item"><div class="label">총 조례 수</div><div class="value">{이_조례수:,}</div></div>
    <div class="item"><div class="label">광역자치단체</div><div class="value">{광역_unique}개</div></div>
    <div class="item"><div class="label">기초자치단체</div><div class="value">{기초_unique}개</div></div>
    <div class="item"><div class="label">조례 분야</div><div class="value">{분야_unique}개</div></div>
    <div class="item"><div class="label">지방의회 기수</div><div class="value">{기수_range}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# 유틸리티
# -----------------------------
def add_serial(dataframe: pd.DataFrame, colname: str = "연번") -> pd.DataFrame:
    """표시/다운로드용 연번(1..n) 컬럼을 선두에 추가. 이미 유사 번호 컬럼이 있으면 추가 생략."""
    out = dataframe.reset_index(drop=True).copy()
    # 충돌 최소화: 연번/번호/순번/Serial 컬럼이 이미 있으면 추가하지 않음
    for c in ["연번", "번호", "순번", "Serial"]:
        if c in out.columns:
            return out
    out.insert(0, colname, np.arange(1, len(out) + 1))
    return out

def download_csv(data, filename):
    """CSV 다운로드 버튼. 연번 1부터 포함."""
    csv = add_serial(data).to_csv(index=False, encoding='cp949')
    st.download_button(
        label="📥 Excel로 열기용",
        data=csv,
        file_name=filename.replace(".csv", ".xls"),
        mime="application/vnd.ms-excel"
    )

# ───────── 스코프 필터/시각화 유틸 ─────────
_SPECIAL_WIDE = {"서울특별시","부산광역시","대구광역시","인천광역시","광주광역시","대전광역시","울산광역시","세종특별자치시"}

def filter_gwangyeok_scope(df_in: pd.DataFrame, scope: str) -> pd.DataFrame:
    if scope == "전체":
        return df_in
    elif scope == "특·광·세종":
        return df_in[df_in["광역"].isin(_SPECIAL_WIDE)]
    elif scope == "도만":
        return df_in[~df_in["광역"].isin(_SPECIAL_WIDE)]
    return df_in

def filter_kicho_scope(df_in: pd.DataFrame, base_scope: str, sg_sub: str = None) -> pd.DataFrame:
    if base_scope == "전체 시·군·구":
        m = df_in["지자체 유형"].isin(["광역지자체_자치구","광역지자체_군","기초지자체_시","기초지자체_군"])
        return df_in[m]
    elif base_scope == "시·군만":
        m = df_in["지자체 유형"].isin(["기초지자체_시","기초지자체_군","광역지자체_군"])
        out = df_in[m]
        if sg_sub == "시만":
            return out[out["지자체 유형"] == "기초지자체_시"]
        elif sg_sub == "군만":
            return out[out["지자체 유형"].isin(["기초지자체_군","광역지자체_군"])]
        return out
    elif base_scope == "자치구만":
        return df_in[df_in["지자체 유형"] == "광역지자체_자치구"]
    return df_in

def pivot_counts(df_in: pd.DataFrame, idx: str, col: str) -> pd.DataFrame:
    return df_in.pivot_table(index=idx, columns=col, aggfunc="size", fill_value=0)

def render_pct_heatmap(pv: pd.DataFrame, idx_name: str, title: str, scheme: str = 'blues', height: int = 420):
    if pv.empty:
        st.info("데이터가 없습니다.")
        return
    rowsum = pv.sum(axis=1).replace(0, np.nan)
    pct = pv.div(rowsum, axis=0) * 100
    m = pct.reset_index().melt(id_vars=pct.index.name, var_name='분야', value_name='비율')
    chart = alt.Chart(m).mark_rect().encode(
        x=alt.X('분야:N', title=''),
        y=alt.Y(f'{idx_name}:N', title=''),
        color=alt.Color('비율:Q', title='비율(%)', scale=alt.Scale(scheme=scheme)),
        tooltip=[idx_name,'분야',alt.Tooltip('비율:Q', format='.2f')]
    ).properties(title=title, height=height)
    st.altair_chart(chart, use_container_width=True)

def render_line_by_term(pv: pd.DataFrame, title: str, ylabel: str = "조례 수 (건)", height: int = 420, term_sort=None):
    if pv.empty:
        st.info("데이터가 없습니다.")
        return
    long = pv.reset_index().melt(id_vars=pv.index.name, var_name="분야", value_name="조례수")
    x_sort = term_sort if term_sort else st.session_state.get("_기수정렬", None)
    chart = alt.Chart(long).mark_line(point=True).encode(
        x=alt.X(f'{pv.index.name}:N', sort=x_sort),
        y=alt.Y('조례수:Q', title=ylabel),
        color=alt.Color('분야:N', title='분야'),
        tooltip=[pv.index.name,'분야','조례수']
    ).properties(title=title, height=height)
    st.altair_chart(chart, use_container_width=True)

# -----------------------------
# 탭 구성: 1~9를 단일 호출로 통합
# -----------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "1️⃣ 기수별 광역 분석",
    "2️⃣ 광역별 기수 분석", 
    "3️⃣ 광역별 기초자치단체 분석",
    "4️⃣ 기수별 분야 분석",
    "5️⃣ 분야 집중도",
    "6️⃣ 조례 수 순위",
    "7️⃣ 전국 분석(신)",
    "8️⃣ 광역지자치단체 분석(신)",
    "9️⃣ 기초지자치단체 분석(신)"
])

# -----------------------------
# 탭1: 기수별 광역 조례 분야 분석
# -----------------------------
with tab1:
    st.header("1️⃣ 기수별 광역자치단체 조례 분야 분석")
    st.caption("각 기수별로 광역자치단체의 조례 분야 비율과 건수를 보여줍니다")
    
    선택_기수 = st.selectbox("📌 기수 선택", 기수_list, index=len(기수_list)-1, key="tab1_select")
    기수_df = df[df["지방의회_기수"] == 선택_기수]
    
    if len(기수_df) == 0:
        st.warning(f"{선택_기수} 데이터가 없습니다")
    else:
        pivot = 기수_df.pivot_table(
            index="광역",
            columns="최종분야",
            aggfunc='size',
            fill_value=0
        )
        row_sums = pivot.sum(axis=1)
        display_df = pd.DataFrame(index=pivot.index)
        display_df['합계'] = row_sums.astype(int)
        for col in pivot.columns:
            display_df[f'{col}_건수'] = pivot[col].astype(int)
            display_df[f'{col}_%'] = (pivot[col] / row_sums * 100).round(2)
        
        광역_개수 = len(pivot.index)
        avg_counts = pivot.mean(axis=0)
        avg_row = {'합계': int(row_sums.mean())}
        for col in pivot.columns:
            avg_row[f'{col}_건수'] = round(avg_counts[col], 1)
            avg_pct = (avg_counts[col] / avg_counts.sum() * 100) if avg_counts.sum() > 0 else 0
            avg_row[f'{col}_%'] = round(avg_pct, 2)
        display_df.loc[f'{광역_개수}개 평균'] = avg_row
        
        st.dataframe(add_serial(display_df.reset_index()), use_container_width=True, height=600, hide_index=True)
        
        pivot_pct = pivot.div(row_sums, axis=0) * 100
        if not pivot_pct.empty:
            chart_data = pivot_pct.reset_index().melt(id_vars='광역', var_name='분야', value_name='비율')
            chart = alt.Chart(chart_data).mark_rect().encode(
                x=alt.X('분야:N', title=''),
                y=alt.Y('광역:N', title=''),
                color=alt.Color('비율:Q', scale=alt.Scale(scheme='blues'), title='비율(%)'),
                tooltip=['광역', '분야', alt.Tooltip('비율:Q', format='.2f')]
            ).properties(
                title=f'{선택_기수} 광역별 분야 비율 히트맵',
                height=400
            )
            st.altair_chart(chart, use_container_width=True)
        
        download_df = pivot.copy()
        download_df['합계'] = row_sums
        download_csv(download_df.reset_index(), f"기수별_광역분석_{선택_기수.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭2: 광역별 기수당 조례 분야 변화
# -----------------------------
with tab2:
    st.header("2️⃣ 광역자치단체별 기수당 조례 분야 변화")
    st.caption("각 광역자치단체별로 기수에 따른 분야 비율 및 증가율을 보여줍니다 (광역 자체 + 소속 기초 전체 포함)")
    
    선택_광역 = st.selectbox("📌 광역 선택", 광역_list, key="tab2_select")
    광역_df2 = df[df["광역"] == 선택_광역]
    
    pivot = 광역_df2.pivot_table(
        index="지방의회_기수",
        columns="최종분야",
        aggfunc='size',
        fill_value=0
    )
    row_sums = pivot.sum(axis=1)
    pivot_pct = pivot.div(row_sums, axis=0) * 100
    pivot_growth = pivot_pct.diff()
    
    result_df = pd.DataFrame(index=pivot.index)
    result_df['합계'] = row_sums.astype(int)
    for 분야 in pivot.columns:
        result_df[f'{분야}_건수'] = pivot[분야].astype(int)
        result_df[f'{분야}_%'] = pivot_pct[분야].round(2)
        result_df[f'{분야}_%p'] = pivot_growth[분야].round(2)
    
    st.dataframe(add_serial(result_df.reset_index()), use_container_width=True, height=400, hide_index=True)
    
    chart_data = pivot.reset_index().melt(id_vars='지방의회_기수', var_name='분야', value_name='조례수')
    line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
        x=alt.X('지방의회_기수:N', title='지방의회 기수', sort=기수_list),
        y=alt.Y('조례수:Q', title='조례 수 (건)'),
        color=alt.Color('분야:N', title='분야'),
        tooltip=['지방의회_기수', '분야', '조례수']
    ).properties(
        title=f'{선택_광역} 기수별 분야 조례 수 변화',
        height=400
    )
    st.altair_chart(line_chart, use_container_width=True)
    
    download_df = pivot.copy()
    download_df['합계'] = row_sums
    download_csv(download_df.reset_index(), f"광역별_기수변화_{선택_광역}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭3: 광역 내 기초자치단체 조례 현황
# -----------------------------
with tab3:
    st.header("3️⃣ 광역별 기초자치단체 조례 현황")
    st.caption("각 광역자치단체 내 기초단체별 조례 분야 비율과 건수를 보여줍니다 (광역 자체 포함, 중복 없음)")
    
    전국_기초_df = df[~df["is_광역자체"]]
    전국_기초_pivot = 전국_기초_df.pivot_table(
        index="기초",
        columns="최종분야",
        aggfunc='size',
        fill_value=0
    )
    전국_기초_비율 = 전국_기초_pivot.div(전국_기초_pivot.sum(axis=1), axis=0) * 100
    전국_평균_비율 = 전국_기초_비율.mean(axis=0)
    전국_평균_건수 = 전국_기초_pivot.mean(axis=0)
    
    선택_광역3 = st.selectbox("📌 광역 선택", 광역_list, key="tab3_select")
    광역_df3 = df[df["광역"] == 선택_광역3]
    
    pivot = 광역_df3.pivot_table(
        index="기초",
        columns="최종분야",
        aggfunc='size',
        fill_value=0
    )
    
    if pivot.empty:
        st.warning(f"{선택_광역3}에 데이터가 없습니다")
    else:
        row_sums = pivot.sum(axis=1)
        display_df = pd.DataFrame(index=pivot.index)
        display_df['합계'] = row_sums.astype(int)
        for col in pivot.columns:
            display_df[f'{col}_건수'] = pivot[col].astype(int)
            display_df[f'{col}_%'] = (pivot[col] / row_sums * 100).round(2)
        
        평균_row = {'합계': round(전국_기초_pivot.sum(axis=1).mean(), 1)}
        for col in 분야_list:
            if col in 전국_평균_건수.index:
                평균_row[f'{col}_건수'] = round(전국_평균_건수[col], 1)
                평균_row[f'{col}_%'] = round(전국_평균_비율[col], 2)
            else:
                평균_row[f'{col}_건수'] = 0
                평균_row[f'{col}_%'] = 0
        display_df.loc['226개 평균'] = 평균_row
        
        st.dataframe(add_serial(display_df.reset_index()), use_container_width=True, height=600, hide_index=True)
        
        heatmap_pivot = pivot.copy()
        heatmap_pct = heatmap_pivot.div(heatmap_pivot.sum(axis=1), axis=0) * 100
        
        if not heatmap_pct.empty:
            chart_data = heatmap_pct.reset_index().melt(id_vars='기초', var_name='분야', value_name='비율')
            chart = alt.Chart(chart_data).mark_rect().encode(
                x=alt.X('분야:N', title=''),
                y=alt.Y('기초:N', title='', sort='-x'),
                color=alt.Color('비율:Q', scale=alt.Scale(scheme='greens'), title='비율(%)'),
                tooltip=['기초', '분야', alt.Tooltip('비율:Q', format='.2f')]
            ).properties(
                title=f'{선택_광역3} 기초단체별 분야 비율 히트맵',
                height=400
            )
            st.altair_chart(chart, use_container_width=True)
        
        download_df = pivot.copy()
        download_df['합계'] = row_sums
        download_csv(download_df.reset_index(), f"기초단체_현황_{선택_광역3}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭4: 전체 기수별 분야 변화 추이
# -----------------------------
with tab4:
    st.header("4️⃣ 전국 기수별 분야 변화 추이")
    st.caption("전국 전체 데이터를 기준으로 기수에 따른 분야별 조례 변화를 시계열로 보여줍니다")
    
    전국_pivot = df.pivot_table(
        index="지방의회_기수",
        columns="최종분야",
        aggfunc='size',
        fill_value=0
    )
    전국_row_sums = 전국_pivot.sum(axis=1)
    전국_비율 = 전국_pivot.div(전국_row_sums, axis=0) * 100
    
    display_df = pd.DataFrame(index=전국_pivot.index)
    display_df['합계'] = 전국_row_sums.astype(int)
    for col in 전국_pivot.columns:
        display_df[f'{col}_건수'] = 전국_pivot[col].astype(int)
        display_df[f'{col}_%'] = 전국_비율[col].round(2)
    
    st.dataframe(add_serial(display_df.reset_index()), use_container_width=True, height=400, hide_index=True)
    
    chart_data = 전국_pivot.reset_index().melt(
        id_vars='지방의회_기수', 
        var_name='분야', 
        value_name='조례수'
    )
    line_chart = alt.Chart(chart_data).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X('지방의회_기수:N', title='지방의회 기수', sort=기수_list),
        y=alt.Y('조례수:Q', title='조례 수 (건)'),
        color=alt.Color('분야:N', title='분야'),
        tooltip=['지방의회_기수', '분야', '조례수']
    ).properties(
        title='전국 기수별 분야 조례 수 변화 추이',
        height=500
    )
    st.altair_chart(line_chart, use_container_width=True)
    
    download_df = 전국_pivot.copy()
    download_df['합계'] = 전국_row_sums
    download_csv(download_df.reset_index(), f"전국_기수별_분야변화_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭5: 분야 집중도 비교 (기초자치단체 기준)
# -----------------------------
with tab5:
    st.header("5️⃣ 기초자치단체 간 분야 집중도 비교")
    st.caption("""
    **집중도 해석:**
    - 집중도(표준편차)가 **높을수록**: 특정 분야에 조례가 집중되어 있음 (분야 간 불균등)
    - 집중도(표준편차)가 **낮을수록**: 조례가 여러 분야에 고르게 분산되어 있음 (분야 간 균등)
    
    예: 집중도 1위 지역은 특정 분야(예: 복지)에만 조례가 많고, 다른 분야는 상대적으로 적음
    """)
    
    기초_분야_pivot = df[~df["is_광역자체"]].pivot_table(
        index='기초_full',
        columns='최종분야',
        aggfunc='size',
        fill_value=0
    )
    기초_비율 = 기초_분야_pivot.div(기초_분야_pivot.sum(axis=1), axis=0) * 100
    집중도 = 기초_비율.std(axis=1).sort_values(ascending=False)
    
    최대_분야 = []
    for 기초_full in 집중도.index:
        max_col = 기초_비율.loc[기초_full].idxmax()
        max_val = 기초_비율.loc[기초_full, max_col]
        최대_분야.append(f"{max_col} ({max_val:.1f}%)")
    
    집중도_df = pd.DataFrame({
        '기초자치단체': 집중도.index,
        '집중도(표준편차)': 집중도.values,
        '집중 분야': 최대_분야,
        '조례수': 기초_분야_pivot.sum(axis=1).loc[집중도.index].values
    }).reset_index(drop=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("기초단체별 집중도 순위")
        st.dataframe(add_serial(집중도_df.round(2)), use_container_width=True, height=600, hide_index=True)
        download_csv(집중도_df.round(2), f"기초_분야집중도_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with col2:
        st.subheader("집중도 막대 차트 (Top 30)")
        top30_집중도 = 집중도_df.head(30)
        bar_chart = alt.Chart(top30_집중도).mark_bar().encode(
            x=alt.X('집중도(표준편차):Q', title='집중도 (표준편차)'),
            y=alt.Y('기초자치단체:N', sort='-x', title=''),
            color=alt.Color('집중도(표준편차):Q', scale=alt.Scale(scheme='oranges'), legend=None),
            tooltip=['기초자치단체', alt.Tooltip('집중도(표준편차):Q', format='.2f'), '집중 분야', '조례수']
        ).properties(height=600)
        st.altair_chart(bar_chart, use_container_width=True)
    
    st.markdown("---")
    st.subheader("기초단체별 분야 비율 히트맵 (Top 50)")
    
    top50_기초 = 집중도.head(50).index
    heatmap_data = 기초_비율.loc[top50_기초].reset_index().melt(id_vars='기초_full', var_name='분야', value_name='비율')
    
    heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('분야:N', title=''),
        y=alt.Y('기초_full:N', title='', sort=top50_기초.tolist()),
        color=alt.Color('비율:Q', scale=alt.Scale(scheme='viridis'), title='비율(%)'),
        tooltip=['기초_full', '분야', alt.Tooltip('비율:Q', format='.2f')]
    ).properties(
        title='기초단체별 분야 비율 전체 비교 (집중도 Top 50)',
        height=800
    )
    st.altair_chart(heatmap, use_container_width=True)

# -----------------------------
# 탭6: 조례 수 순위
# -----------------------------
with tab6:
    st.header("6️⃣ 조례 수 순위")
    st.caption("기초자치단체, 광역자치단체, 전체 순위를 보여줍니다")
    
    # 1. 기초자치단체만 순위
    기초_조례수 = df[~df["is_광역자체"]].groupby(['광역', '기초']).size().reset_index(name='조례수')
    기초_조례수 = 기초_조례수.sort_values('조례수', ascending=False).reset_index(drop=True)
    기초_조례수['순위'] = range(1, len(기초_조례수) + 1)
    기초_조례수 = 기초_조례수[['순위', '광역', '기초', '조례수']]
    
    # 2. 광역자치단체만 순위
    광역_조례수 = df[df["is_광역자체"]].groupby('광역').size().reset_index(name='조례수')
    광역_조례수 = 광역_조례수.sort_values('조례수', ascending=False).reset_index(drop=True)
    광역_조례수['순위'] = range(1, len(광역_조례수) + 1)
    광역_조례수 = 광역_조례수[['순위', '광역', '조례수']]
    
    # 3. 전체 순위 (기초 + 광역)
    전체_조례수 = df.groupby(['광역', '기초']).size().reset_index(name='조례수')
    전체_조례수['구분'] = 전체_조례수.apply(lambda x: '광역' if x['광역'] == x['기초'] else '기초', axis=1)
    전체_조례수 = 전체_조례수.sort_values('조례수', ascending=False).reset_index(drop=True)
    전체_조례수['순위'] = range(1, len(전체_조례수) + 1)
    전체_조례수 = 전체_조례수[['순위', '구분', '광역', '기초', '조례수']]
    
    순위_tab1, 순위_tab2, 순위_tab3 = st.tabs(["기초자치단체 순위", "광역자치단체 순위", "전체 순위"])
    
    with 순위_tab1:
        st.subheader("🏆 기초자치단체 조례 수 순위")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**Top 50**")
            st.dataframe(add_serial(기초_조례수.head(50)), use_container_width=True, height=600, hide_index=True)
        with col2:
            st.markdown("**Top 30 차트**")
            top30 = 기초_조례수.head(30).copy()
            top30['기초_full'] = top30['광역'] + ' ' + top30['기초']
            bar_chart = alt.Chart(top30).mark_bar().encode(
                x=alt.X('조례수:Q', title='총 조례 수'),
                y=alt.Y('기초_full:N', sort='-x', title=''),
                color=alt.Color('광역:N', title='광역'),
                tooltip=['순위', '광역', '기초', '조례수']
            ).properties(height=600)
            st.altair_chart(bar_chart, use_container_width=True)
        st.markdown("---")
        st.subheader("전체 기초자치단체 순위")
        st.dataframe(add_serial(기초_조례수), use_container_width=True, height=400, hide_index=True)
        download_csv(기초_조례수, f"기초단체_순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with 순위_tab2:
        st.subheader("🏆 광역자치단체 조례 수 순위")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**전체 순위**")
            st.dataframe(add_serial(광역_조례수), use_container_width=True, height=600, hide_index=True)
        with col2:
            st.markdown("**순위 차트**")
            bar_chart = alt.Chart(광역_조례수).mark_bar().encode(
                x=alt.X('조례수:Q', title='총 조례 수'),
                y=alt.Y('광역:N', sort='-x', title=''),
                color=alt.Color('조례수:Q', scale=alt.Scale(scheme='blues'), legend=None),
                tooltip=['순위', '광역', '조례수']
            ).properties(height=600)
            st.altair_chart(bar_chart, use_container_width=True)
        download_csv(광역_조례수, f"광역단체_순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with 순위_tab3:
        st.subheader("🏆 전체 조례 수 순위 (기초 + 광역)")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**Top 50**")
            st.dataframe(add_serial(전체_조례수.head(50)), use_container_width=True, height=600, hide_index=True)
        with col2:
            st.markdown("**Top 30 차트**")
            top30 = 전체_조례수.head(30).copy()
            top30['표시명'] = top30.apply(
                lambda x: f"{x['광역']}" if x['구분'] == '광역' else f"{x['광역']} {x['기초']}", 
                axis=1
            )
            bar_chart = alt.Chart(top30).mark_bar().encode(
                x=alt.X('조례수:Q', title='총 조례 수'),
                y=alt.Y('표시명:N', sort='-x', title=''),
                color=alt.Color('구분:N', title='구분', scale=alt.Scale(domain=['광역', '기초'], range=['#e74c3c', '#3498db'])),
                tooltip=['순위', '구분', '광역', '기초', '조례수']
            ).properties(height=600)
            st.altair_chart(bar_chart, use_container_width=True)
        st.markdown("---")
        st.subheader("전체 순위")
        st.dataframe(add_serial(전체_조례수), use_container_width=True, height=400, hide_index=True)
        download_csv(전체_조례수, f"전체_순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    st.markdown("---")
    st.subheader("광역별 기초단체 평균 조례 수")
    광역_평균 = 기초_조례수.groupby('광역')['조례수'].agg(['mean', 'count']).reset_index()
    광역_평균.columns = ['광역', '평균조례수', '기초단체수']
    광역_평균 = 광역_평균.sort_values('평균조례수', ascending=False).round(2)
    st.dataframe(add_serial(광역_평균), use_container_width=True, hide_index=True)
    bar_chart2 = alt.Chart(광역_평균).mark_bar().encode(
        x=alt.X('평균조례수:Q', title='평균 조례 수'),
        y=alt.Y('광역:N', sort='-x', title=''),
        color=alt.Color('평균조례수:Q', scale=alt.Scale(scheme='teals'), legend=None),
        tooltip=['광역', alt.Tooltip('평균조례수:Q', format='.2f'), '기초단체수']
    ).properties(height=400)
    st.altair_chart(bar_chart2, use_container_width=True)

# ─────────────────────────────────
# 탭7~9: 스코프형 신규 메뉴
# ─────────────────────────────────
with tab7:
    st.header("7️⃣ 전국 분석(신)")
    st.caption("전국 단위에서 기수×분야 흐름과 비중 변화를 확인합니다.")
    pv_nat = pivot_counts(df, idx="지방의회_기수", col="최종분야")
    st.subheader("① 전국 기수별·분야별 추이")
    st.dataframe(add_serial(pv_nat.assign(합계=pv_nat.sum(axis=1)).reset_index()), use_container_width=True, height=420, hide_index=True)
    render_line_by_term(pv_nat, title="전국 기수별 분야 조례 수 변화", height=460, term_sort=기수_list)
    download_csv(pv_nat.assign(합계=pv_nat.sum(axis=1)).reset_index(), f"전국_기수별_분야_{datetime.now().strftime('%Y%m%d')}.csv")
    st.subheader("② 전국 분야 비중 변화")
    render_pct_heatmap(pv_nat, idx_name="지방의회_기수", title="전국 기수별 분야 비율 히트맵", scheme="tealblues", height=460)

with tab8:
    st.header("8️⃣ 광역지자치단체 분석(신)")
    colA, colB = st.columns([1.2, 2.0])
    with colA:
        scope = st.radio("광역 범위", ["전체","특·광·세종","도만"], horizontal=True, index=0, key="wide_scope_new")
    with colB:
        sel_term = st.selectbox("기수(미선택 시 전체)", ["전체"] + 기수_list, index=0, key="wide_term_new")

    scoped = filter_gwangyeok_scope(df, scope)

    st.subheader("① 광역별 분야별 비교")
    tdf = scoped if sel_term == "전체" else scoped[scoped["지방의회_기수"] == sel_term]
    pv = pivot_counts(tdf, idx="광역", col="최종분야")
    st.caption(f"스코프: {scope} | 기준: {'전체' if sel_term=='전체' else sel_term}")
    st.dataframe(add_serial(pv.assign(합계=pv.sum(axis=1)).reset_index()), use_container_width=True, height=480, hide_index=True)
    render_pct_heatmap(pv, idx_name="광역", title=f"광역별 분야 비율 히트맵 ({'전체' if sel_term=='전체' else sel_term})", scheme="blues", height=480)
    download_csv(pv.assign(합계=pv.sum(axis=1)).reset_index(), f"광역별_분야_{scope}_{datetime.now():%Y%m%d}.csv")

    st.markdown("---")
    st.subheader("② 광역별 기수별 변화")
    sel_w = st.selectbox("광역 선택", sorted(scoped["광역"].unique().tolist()), index=0, key="wide_pick_new")
    wdf = scoped[scoped["광역"] == sel_w]
    pvW = pivot_counts(wdf, idx="지방의회_기수", col="최종분야")
    st.dataframe(add_serial(pvW.assign(합계=pvW.sum(axis=1)).reset_index()), use_container_width=True, height=420, hide_index=True)
    render_line_by_term(pvW, title=f"{sel_w} 기수별 분야 조례 수 변화", height=420, term_sort=기수_list)
    download_csv(pvW.assign(합계=pvW.sum(axis=1)).reset_index(), f"{sel_w}_기수별_분야_{datetime.now():%Y%m%d}.csv")

    with st.expander("ℹ️ 용어/스코프 안내", expanded=False):
        st.markdown("""
- **특·광·세종**: 서울특별시, 6대 광역시, 세종특별자치시
- **도만**: 8도 + 강원·제주 특별자치도
- 세종은 기초자치단체가 없는 단층제 광역입니다.
        """)

with tab9:
    st.header("9️⃣ 기초지자치단체 분석(신)")
    c1, c2, c3 = st.columns([1.5,1.2,2.5])
    with c1:
        base_scope = st.radio("기초 범위", ["전체 시·군·구","시·군만","자치구만"], horizontal=True, index=0, key="local_scope_new")
    with c2:
        sg_sub = None
        if base_scope == "시·군만":
            sg_sub = st.radio("세부", ["전체","시만","군만"], horizontal=True, index=0, key="local_sub_new")
    with c3:
        sel_w2 = st.multiselect("광역 선택(미선택 시 전국)", options=sorted(df["광역"].unique().tolist()), default=[], key="local_wide_new")

    ldf = filter_kicho_scope(df, base_scope, sg_sub if base_scope=="시·군만" else None)
    if sel_w2:
        ldf = ldf[ldf["광역"].isin(sel_w2)]

    st.subheader("① 기초 단위 분야별 비교")
    pvL = pivot_counts(ldf, idx="기초_full", col="최종분야")
    st.caption(f"스코프: {base_scope}{' · '+sg_sub if sg_sub and base_scope=='시·군만' else ''} | 광역: {', '.join(sel_w2) if sel_w2 else '전국'}")
    st.dataframe(add_serial(pvL.assign(합계=pvL.sum(axis=1)).reset_index().rename(columns={"기초_full":"지자체"})), use_container_width=True, height=520, hide_index=True)
    render_pct_heatmap(pvL, idx_name="기초_full", title="기초 단위 분야 비율 히트맵", scheme="greens", height=520)
    download_csv(pvL.assign(합계=pvL.sum(axis=1)).reset_index().rename(columns={"기초_full":"지자체"}), f"기초_분야_{base_scope}_{datetime.now():%Y%m%d}.csv")

    st.markdown("---")
    st.subheader("② 기초 단위 기수별·분야별 변화")
    klist = sorted(ldf["기초_full"].unique().tolist())
    if len(klist)==0:
        st.info("선택된 스코프/광역에 해당하는 기초 단위가 없습니다.")
    else:
        sel_local = st.selectbox("기초 선택", klist, index=0, key="local_pick_new")
        ldf2 = ldf[ldf["기초_full"] == sel_local]
        pvL2 = pivot_counts(ldf2, idx="지방의회_기수", col="최종분야")
        st.dataframe(add_serial(pvL2.assign(합계=pvL2.sum(axis=1)).reset_index()), use_container_width=True, height=380, hide_index=True)
        render_line_by_term(pvL2, title=f"{sel_local} 기수별 분야 조례 수 변화", height=420, term_sort=기수_list)
        download_csv(pvL2.assign(합계=pvL2.sum(axis=1)).reset_index(), f"{sel_local}_기수별_분야_{datetime.now():%Y%m%d}.csv")

    with st.expander("ℹ️ 분류 규칙 안내", expanded=False):
        st.markdown("""
- **전체 시·군·구**: `지자체 유형`이 자치구/시/군 전체(광역시 산하 군 포함).
- **시·군만**: `기초지자체_시`, `기초지자체_군`, **`광역지자체_군`(인천 강화·옹진, 부산 기장)** 포함.
- **자치구만**: `광역지자체_자치구`만.
        """)

st.markdown("---")
st.caption("© 2025 지방자치단체 조례 통계 분석 대시보드 (v2: 스코프형 메뉴 + 연번 1부터)")
