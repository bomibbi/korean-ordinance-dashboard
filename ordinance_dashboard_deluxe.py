# -*- coding: utf-8 -*-
# 지방자치단체 조례 통계 분석 대시보드

import os
from datetime import datetime

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(page_title="조례 통계 분석", layout="wide")

# -----------------------------
# 데이터 로드 (GitHub data 폴더에서)
# -----------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_DIR, "data", "korean_ordinance.xlsx")

@st.cache_data(show_spinner=True)
def load_excel(path):
    return pd.read_excel(path)

# -----------------------------
# 헤더
# -----------------------------
st.title("📊 지방자치단체 조례 통계 분석 대시보드")
st.markdown("---")

# 데이터 로드
if not os.path.exists(DATA_PATH):
    st.error(f"⚠️ 데이터 파일을 찾을 수 없습니다: {DATA_PATH}")
    st.info("GitHub의 data 폴더에 korean_ordinance.xlsx 파일을 업로드해주세요.")
    st.stop()

with st.spinner("📂 데이터 로딩 중..."):
    df = load_excel(DATA_PATH)

st.success(f"✅ 데이터 로드 완료: {len(df):,}건")

# 필수 컬럼 확인
required_cols = ["광역", "기초", "최종분야", "지방의회_기수"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"필수 컬럼이 없습니다: {', '.join(missing)}")
    st.write("현재 컬럼:", df.columns.tolist())
    st.stop()

# 데이터 정제
df = df.dropna(subset=required_cols)

# 지방의회_기수 정리 (문자열 그대로 유지, 정렬용 숫자 컬럼 추가)
df["지방의회_기수"] = df["지방의회_기수"].astype(str).str.strip()

def extract_number(x):
    if "분류불가" in x:
        return 0
    try:
        import re
        match = re.search(r'\d+', x)
        return int(match.group()) if match else 999
    except:
        return 999

df["_기수_정렬용"] = df["지방의회_기수"].apply(extract_number)

# 고유값
광역_list = sorted(df["광역"].dropna().unique().tolist())
분야_list = sorted(df["최종분야"].dropna().unique().tolist())

# 기수 정렬 (분류불가 → 1기 → …)
기수_unique = df[["지방의회_기수", "_기수_정렬용"]].drop_duplicates()
기수_unique = 기수_unique.sort_values("_기수_정렬용")
기수_list = 기수_unique["지방의회_기수"].tolist()

# 광역 자체 / 기초 구분
df["is_광역자체"] = df["광역"] == df["기초"]

# -----------------------------
# 사이드바 - 데이터 요약
# -----------------------------
with st.sidebar:
    st.header("📊 데이터 요약")
    st.metric("총 조례 수", f"{len(df):,}")
    st.metric("광역자치단체", len(광역_list))
    기초_unique = df[~df["is_광역자체"]]["기초"].nunique()
    st.metric("기초자치단체", 기초_unique)
    st.metric("조례 분야", len(분야_list))
    st.metric("지방의회 기수", f"{기수_list[0]} ~ {기수_list[-1]}")
    st.markdown("---")
    st.info("💡 각 탭의 표를 확인하고 CSV로 다운로드할 수 있습니다.")

# -----------------------------
# 공통 유틸
# -----------------------------
def download_csv(data, filename):
    csv = data.to_csv(encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )

def move_sum_first(df_display: pd.DataFrame) -> pd.DataFrame:
    """합계 컬럼을 맨 앞으로 이동 (존재할 때만)"""
    cols = df_display.columns.tolist()
    if "합계" in cols:
        return df_display[["합계"] + [c for c in cols if c != "합계"]]
    return df_display

def show_df(df_display: pd.DataFrame, *, height=400, index_to_column=False):
    """
    - index_to_column=True: 인덱스(광역/기초/기수)를 컬럼으로 승격해 보이게 함 (탭1~4용)
    - 모든 경우: 숫자 인덱스는 숨김
    """
    data = df_display.reset_index() if index_to_column else df_display
    try:
        st.dataframe(data, use_container_width=True, height=height, hide_index=True)
    except TypeError:
        # 구버전 Streamlit 호환: pandas Styler로 인덱스 숨김
        st.dataframe(data.style.hide(axis="index"), use_container_width=True, height=height)

# -----------------------------
# 탭 구성
# -----------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1️⃣ 기수별 광역 분석",
    "2️⃣ 광역별 기수 분석", 
    "3️⃣ 광역별 기초자치단체 분석",
    "4️⃣ 기수별 분야 분석",
    "5️⃣ 광역 분야 집중도",
    "6️⃣ 조례 수 순위"
])

# -----------------------------
# 탭1: 기수별 광역
# -----------------------------
with tab1:
    st.header("1️⃣ 기수별 광역자치단체 조례 분야 분석")
    st.caption("각 기수별로 광역자치단체의 조례 분야 비율과 건수를 보여줍니다")
    
    for 기수 in 기수_list:
        with st.expander(f"📊 {기수} 분석", expanded=(기수==기수_list[-1])):
            기수_df = df[df["지방의회_기수"] == 기수]
            if len(기수_df) == 0:
                st.warning(f"{기수} 데이터가 없습니다")
                continue
            
            pivot = 기수_df.pivot_table(index="광역", columns="최종분야", aggfunc='size', fill_value=0)
            row_sums = pivot.sum(axis=1)

            display_df = pd.DataFrame(index=pivot.index)
            for col in pivot.columns:
                display_df[col] = [
                    f"{int(pivot.loc[idx, col])}건 ({pivot.loc[idx, col]/row_sums[idx]*100:.2f}%)"
                    if row_sums[idx] > 0 else "0건 (0%)"
                    for idx in pivot.index
                ]
            display_df['합계'] = [f"{int(row_sums[idx])}건" for idx in pivot.index]
            display_df = move_sum_first(display_df)

            # ✅ Y축(광역) 보존 + 숫자 인덱스 숨김
            show_df(display_df, height=600, index_to_column=True)

            # 히트맵
            pivot_pct = pivot.div(row_sums, axis=0) * 100
            if not pivot_pct.empty:
                chart_data = pivot_pct.reset_index().melt(id_vars='광역', var_name='분야', value_name='비율')
                chart = alt.Chart(chart_data).mark_rect().encode(
                    x=alt.X('분야:N', title=''),
                    y=alt.Y('광역:N', title=''),
                    color=alt.Color('비율:Q', scale=alt.Scale(scheme='blues'), title='비율(%)'),
                    tooltip=['광역', '분야', alt.Tooltip('비율:Q', format='.2f')]
                ).properties(title=f'{기수} 광역별 분야 비율 히트맵', height=400)
                st.altair_chart(chart, use_container_width=True)

            download_df = pivot.copy()
            download_df['합계'] = row_sums
            download_csv(download_df, f"기수별_광역분석_{기수.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭2: 광역별 기수 변화
# -----------------------------
with tab2:
    st.header("2️⃣ 광역자치단체별 기수당 조례 분야 변화")
    st.caption("각 광역자치단체별로 기수에 따른 분야 비율 및 증가율을 보여줍니다 (광역 자체 + 소속 기초 포함)")
    
    for 광역 in 광역_list:
        with st.expander(f"📊 {광역} 분석"):
            광역_df = df[df["광역"] == 광역]
            pivot = 광역_df.pivot_table(index="지방의회_기수", columns="최종분야", aggfunc='size', fill_value=0)
            row_sums = pivot.sum(axis=1)
            pivot_pct = pivot.div(row_sums, axis=0) * 100
            pivot_growth = pivot_pct.diff()

            # ✅ 평균증가율 컬럼 제거(표에는 미포함)
            result_rows = []
            for idx, gi in enumerate(pivot_pct.index):
                row_data = {'기수': gi}
                for 분야 in pivot_pct.columns:
                    건수 = int(pivot.loc[gi, 분야])
                    비율 = pivot_pct.loc[gi, 분야]
                    if idx > 0:
                        증가율 = pivot_growth.loc[gi, 분야]
                        row_data[분야] = f"{건수}건 ({비율:.2f}%, {증가율:+.2f}%p)"
                    else:
                        row_data[분야] = f"{건수}건 ({비율:.2f}%)"
                row_data['합계'] = f"{int(row_sums.loc[gi])}건"
                result_rows.append(row_data)

            result_df = pd.DataFrame(result_rows).set_index('기수')
            result_df = move_sum_first(result_df)

            # ✅ Y축(기수) 보존 + 숫자 인덱스 숨김
            show_df(result_df, height=400, index_to_column=True)

            # 라인 차트
            chart_data = pivot.reset_index().melt(id_vars='지방의회_기수', var_name='분야', value_name='조례수')
            line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('지방의회_기수:N', title='지방의회 기수', sort=기수_list),
                y=alt.Y('조례수:Q', title='조례 수 (건)'),
                color=alt.Color('분야:N', title='분야'),
                tooltip=['지방의회_기수', '분야', '조례수']
            ).properties(title=f'{광역} 기수별 분야 조례 수 변화', height=400)
            st.altair_chart(line_chart, use_container_width=True)

            download_df = pivot.copy()
            download_df['합계'] = row_sums
            download_csv(download_df, f"광역별_기수변화_{광역}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭3: 광역 내 기초 현황
# -----------------------------
with tab3:
    st.header("3️⃣ 광역별 기초자치단체 조례 현황")
    st.caption("각 광역자치단체 내 기초단체별 조례 분야 비율과 건수를 보여줍니다 (광역 자체 포함, 중복 없음)")
    
    전국_기초_df = df[~df["is_광역자체"]]
    전국_기초_pivot = 전국_기초_df.pivot_table(index="기초", columns="최종분야", aggfunc='size', fill_value=0)
    전국_기초_비율 = 전국_기초_pivot.div(전국_기초_pivot.sum(axis=1), axis=0) * 100
    전국_평균_비율 = 전국_기초_비율.mean(axis=0)
    전국_평균_건수 = 전국_기초_pivot.mean(axis=0)
    
    for 광역 in 광역_list:
        with st.expander(f"📊 {광역} 분석"):
            광역_df = df[df["광역"] == 광역]
            pivot = 광역_df.pivot_table(index="기초", columns="최종분야", aggfunc='size', fill_value=0)
            if pivot.empty:
                st.warning(f"{광역}에 데이터가 없습니다")
                continue

            row_sums = pivot.sum(axis=1)
            display_df = pd.DataFrame(index=pivot.index)
            for col in pivot.columns:
                display_df[col] = [
                    f"{int(pivot.loc[idx, col])}건 ({pivot.loc[idx, col]/row_sums[idx]*100:.2f}%)"
                    if row_sums[idx] > 0 else "0건 (0%)"
                    for idx in pivot.index
                ]
            display_df['합계'] = [f"{int(row_sums[idx])}건" for idx in pivot.index]

            # 226개 평균 행
            평균_row = {}
            for col in 분야_list:
                if col in 전국_평균_건수.index:
                    avg_건수 = 전국_평균_건수[col]
                    avg_비율 = 전국_평균_비율[col]
                    평균_row[col] = f"{avg_건수:.1f}건 ({avg_비율:.2f}%)"
                else:
                    평균_row[col] = "0건 (0%)"
            평균_row['합계'] = f"{전국_기초_pivot.sum(axis=1).mean():.1f}건"
            display_df.loc['226개 평균'] = 평균_row

            display_df = move_sum_first(display_df)

            # ✅ Y축(기초) 보존 + 숫자 인덱스 숨김
            show_df(display_df, height=600, index_to_column=True)

            # 히트맵
            heatmap_pivot = pivot.copy()
            heatmap_row_sums = heatmap_pivot.sum(axis=1)
            heatmap_pct = heatmap_pivot.div(heatmap_row_sums, axis=0) * 100
            if not heatmap_pct.empty:
                chart_data = heatmap_pct.reset_index().melt(id_vars='기초', var_name='분야', value_name='비율')
                chart = alt.Chart(chart_data).mark_rect().encode(
                    x=alt.X('분야:N', title=''),
                    y=alt.Y('기초:N', title='', sort='-x'),
                    color=alt.Color('비율:Q', scale=alt.Scale(scheme='greens'), title='비율(%)'),
                    tooltip=['기초', '분야', alt.Tooltip('비율:Q', format='.2f')]
                ).properties(title=f'{광역} 기초단체별 분야 비율 히트맵', height=400)
                st.altair_chart(chart, use_container_width=True)

            download_df = pivot.copy()
            download_df['합계'] = row_sums
            download_csv(download_df, f"기초단체_현황_{광역}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭4: 전국 기수별 분야 추이
# -----------------------------
with tab4:
    st.header("4️⃣ 전국 기수별 분야 변화 추이")
    st.caption("전국 전체 데이터를 기준으로 기수에 따른 분야별 조례 변화를 시계열로 보여줍니다")
    
    전국_pivot = df.pivot_table(index="지방의회_기수", columns="최종분야", aggfunc='size', fill_value=0)
    전국_row_sums = 전국_pivot.sum(axis=1)
    전국_비율 = 전국_pivot.div(전국_row_sums, axis=0) * 100

    display_df = pd.DataFrame(index=전국_pivot.index)
    for col in 전국_pivot.columns:
        display_df[col] = [
            f"{int(전국_pivot.loc[idx, col])}건 ({전국_비율.loc[idx, col]:.2f}%)"
            for idx in 전국_pivot.index
        ]
    display_df['합계'] = [f"{int(전국_row_sums[idx])}건" for idx in 전국_pivot.index]
    display_df = move_sum_first(display_df)

    # ✅ Y축(지방의회_기수) 보존 + 숫자 인덱스 숨김
    show_df(display_df, height=400, index_to_column=True)

    chart_data = 전국_pivot.reset_index().melt(id_vars='지방의회_기수', var_name='분야', value_name='조례수')
    line_chart = alt.Chart(chart_data).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X('지방의회_기수:N', title='지방의회 기수', sort=기수_list),
        y=alt.Y('조례수:Q', title='조례 수 (건)'),
        color=alt.Color('분야:N', title='분야'),
        tooltip=['지방의회_기수', '분야', '조례수']
    ).properties(title='전국 기수별 분야 조례 수 변화 추이', height=500)
    st.altair_chart(line_chart, use_container_width=True)

    download_df = 전국_pivot.copy()
    download_df['합계'] = 전국_row_sums
    download_csv(download_df, f"전국_기수별_분야변화_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭5: 광역 간 분야 집중도
# -----------------------------
with tab5:
    st.header("5️⃣ 광역자치단체 간 분야 집중도 비교")
    st.caption("""
    **집중도 해석:**
    - 집중도(표준편차)가 **높을수록**: 특정 분야에 조례가 집중
    - 집중도(표준편차)가 **낮을수록**: 조례가 여러 분야에 고르게 분산
    """)
    
    광역_분야_pivot = df.pivot_table(index="광역", columns="최종분야", aggfunc='size', fill_value=0)
    광역_비율 = 광역_분야_pivot.div(광역_분야_pivot.sum(axis=1), axis=0) * 100
    집중도 = 광역_비율.std(axis=1).sort_values(ascending=False)
    
    최대_분야 = []
    for 광역 in 집중도.index:
        max_col = 광역_비율.loc[광역].idxmax()
        max_val = 광역_비율.loc[광역, max_col]
        최대_분야.append(f"{max_col} ({max_val:.1f}%)")
    
    집중도_df = pd.DataFrame({
        '광역': 집중도.index,
        '집중도(표준편차)': 집중도.values,
        '집중 분야': 최대_분야,
        '총조례수': 광역_분야_pivot.sum(axis=1).loc[집중도.index].values
    })

    # ✅ 숫자 인덱스만 숨김 (컬럼 구조 유지)
    show_df(집중도_df, height=600, index_to_column=False)
    download_csv(집중도_df, f"광역_분야집중도_{datetime.now().strftime('%Y%m%d')}.csv")

    st.markdown("---")
    st.subheader("광역별 분야 비율 히트맵")
    heatmap_data = 광역_비율.reset_index().melt(id_vars='광역', var_name='분야', value_name='비율')
    heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('분야:N', title=''),
        y=alt.Y('광역:N', title='', sort=집중도.index.tolist()),
        color=alt.Color('비율:Q', scale=alt.Scale(scheme='viridis'), title='비율(%)'),
        tooltip=['광역', '분야', alt.Tooltip('비율:Q', format='.2f')]
    ).properties(title='광역별 분야 비율 전체 비교', height=500)
    st.altair_chart(heatmap, use_container_width=True)

# -----------------------------
# 탭6: 조례 수 순위
# -----------------------------
with tab6:
    st.header("6️⃣ 조례 수 순위")
    st.caption("기초자치단체, 광역자치단체, 전체 순위를 보여줍니다")
    
    # 1) 기초
    기초_조례수 = df[~df["is_광역자체"]].groupby(['광역', '기초']).size().reset_index(name='총조례수')
    기초_조례수 = 기초_조례수.sort_values('총조례수', ascending=False).reset_index(drop=True)
    기초_조례수['순위'] = range(1, len(기초_조례수) + 1)
    기초_조례수 = 기초_조례수[['순위', '광역', '기초', '총조례수']]
    
    # 2) 광역
    광역_조례수 = df[df["is_광역자체"]].groupby('광역').size().reset_index(name='총조례수')
    광역_조례수 = 광역_조례수.sort_values('총조례수', ascending=False).reset_index(drop=True)
    광역_조례수['순위'] = range(1, len(광역_조례수) + 1)
    광역_조례수 = 광역_조례수[['순위', '광역', '총조례수']]
    
    # 3) 전체
    전체_조례수 = df.groupby(['광역', '기초']).size().reset_index(name='총조례수')
    전체_조례수['구분'] = 전체_조례수.apply(lambda x: '광역' if x['광역'] == x['기초'] else '기초', axis=1)
    전체_조례수 = 전체_조례수.sort_values('총조례수', ascending=False).reset_index(drop=True)
    전체_조례수['순위'] = range(1, len(전체_조례수) + 1)
    전체_조례수 = 전체_조례수[['순위', '구분', '광역', '기초', '총조례수']]
    
    순위_tab1, 순위_tab2, 순위_tab3 = st.tabs(["기초자치단체 순위", "광역자치단체 순위", "전체 순위"])
    
    with 순위_tab1:
        st.subheader("🏆 기초자치단체 조례 수 순위")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**Top 50**")
            show_df(기초_조례수.head(50), height=600)
        with col2:
            st.markdown("**Top 30 차트**")
            top30 = 기초_조례수.head(30).copy()
            top30['기초_full'] = top30['광역'] + ' ' + top30['기초']
            bar_chart = alt.Chart(top30).mark_bar().encode(
                x=alt.X('총조례수:Q', title='총 조례 수'),
                y=alt.Y('기초_full:N', sort='-x', title=''),
                color=alt.Color('광역:N', title='광역'),
                tooltip=['순위', '광역', '기초', '총조례수']
            ).properties(height=600)
            st.altair_chart(bar_chart, use_container_width=True)
        st.markdown("---")
        st.subheader("전체 기초자치단체 순위")
        show_df(기초_조례수, height=400)
        download_csv(기초_조례수, f"기초단체_순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with 순위_tab2:
        st.subheader("🏆 광역자치단체 조례 수 순위")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**전체 순위**")
            show_df(광역_조례수, height=600)
        with col2:
            st.markdown("**순위 차트**")
            bar_chart = alt.Chart(광역_조례수).mark_bar().encode(
                x=alt.X('총조례수:Q', title='총 조례 수'),
                y=alt.Y('광역:N', sort='-x', title=''),
                color=alt.Color('총조례수:Q', scale=alt.Scale(scheme='blues'), legend=None),
                tooltip=['순위', '광역', '총조례수']
            ).properties(height=600)
            st.altair_chart(bar_chart, use_container_width=True)
        download_csv(광역_조례수, f"광역단체_순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with 순위_tab3:
        st.subheader("🏆 전체 조례 수 순위 (기초 + 광역)")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**Top 50**")
            show_df(전체_조례수.head(50), height=600)
        with col2:
            st.markdown("**Top 30 차트**")
            top30 = 전체_조례수.head(30).copy()
            top30['표시명'] = top30.apply(
                lambda x: f"{x['광역']}" if x['구분'] == '광역' else f"{x['광역']} {x['기초']}",
                axis=1
            )
            bar_chart = alt.Chart(top30).mark_bar().encode(
                x=alt.X('총조례수:Q', title='총 조례 수'),
                y=alt.Y('표시명:N', sort='-x', title=''),
                color=alt.Color('구분:N', title='구분', scale=alt.Scale(domain=['광역', '기초'], range=['#e74c3c', '#3498db'])),
                tooltip=['순위', '구분', '광역', '기초', '총조례수']
            ).properties(height=600)
            st.altair_chart(bar_chart, use_container_width=True)
        st.markdown("---")
        st.subheader("전체 순위")
        show_df(전체_조례수, height=400)
        download_csv(전체_조례수, f"전체_순위_{datetime.now().strftime('%Y%m%d')}.csv")

st.markdown("---")
st.caption("© 2025 지방자치단체 조례 통계 분석 대시보드")
