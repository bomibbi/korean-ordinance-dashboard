# -*- coding: utf-8 -*-
# 지방자치단체 조례 통계 분석 대시보드

import os
from datetime import datetime

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
    }
    
    button[data-baseweb="tab"] {
        height: 55px;
        padding: 0px 20px;
        background-color: transparent !important;
        border-radius: 0px !important;
        font-size: 17px !important;
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
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# 데이터 로드 (GitHub data 폴더에서)
# -----------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_DIR, "data", "korean_ordinance.xlsx")

@st.cache_data(show_spinner=True)
def load_excel(path):
    return pd.read_excel(path)

# 데이터 로드
if not os.path.exists(DATA_PATH):
    st.error(f"⚠️ 데이터 파일을 찾을 수 없습니다: {DATA_PATH}")
    st.info("GitHub의 data 폴더에 korean_ordinance.xlsx 파일을 업로드해주세요.")
    st.stop()

with st.spinner("📂 데이터 로딩 중..."):
    df = load_excel(DATA_PATH)

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

# 정렬을 위한 숫자 컬럼 생성
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

# 고유값 추출
광역_list = sorted(df["광역"].dropna().unique().tolist())
분야_list = sorted(df["최종분야"].dropna().unique().tolist())

# 기수 리스트 정렬 (분류불가 → 1기 → 2기 → ... → 9기)
기수_unique = df[["지방의회_기수", "_기수_정렬용"]].drop_duplicates()
기수_unique = 기수_unique.sort_values("_기수_정렬용")
기수_list = 기수_unique["지방의회_기수"].tolist()

# 광역 자체 / 기초 구분
df["is_광역자체"] = df["광역"] == df["기초"]

# 기초_full 생성 (광역+기초 조합으로 고유 식별)
df["기초_full"] = df["광역"] + " " + df["기초"]

# -----------------------------
# 헤더 및 데이터 요약
# -----------------------------
st.title("📊 지방자치단체 조례 통계 분석 대시보드")

# 데이터 요약 변수 계산
이_조례수 = len(df)
광역_unique = len(광역_list)
기초_unique = df[~df["is_광역자체"]][['광역', '기초']].drop_duplicates().shape[0]
분야_unique = len(분야_list)
기수_range = f"{기수_list[0]} ~ {기수_list[-1]}"

# 데이터 요약을 HTML로 직접 렌더링
st.markdown(f"""
<div style="background-color: #f0f2f6; padding: 25px 30px; border-radius: 10px; margin: 20px 0 30px 0;">
    <div style="font-size: 18px; font-weight: 700; margin-bottom: 20px; color: #1f1f1f;">📈 데이터 요약</div>
    <div style="display: flex; justify-content: space-between; gap: 20px;">
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 13px; font-weight: 600; color: #666; margin-bottom: 8px;">총 조례 수</div>
            <div style="font-size: 22px; font-weight: 400; color: #1f1f1f;">{이_조례수:,}</div>
        </div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 13px; font-weight: 600; color: #666; margin-bottom: 8px;">광역자치단체</div>
            <div style="font-size: 22px; font-weight: 400; color: #1f1f1f;">{광역_unique}개</div>
        </div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 13px; font-weight: 600; color: #666; margin-bottom: 8px;">기초자치단체</div>
            <div style="font-size: 22px; font-weight: 400; color: #1f1f1f;">{기초_unique}개</div>
        </div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 13px; font-weight: 600; color: #666; margin-bottom: 8px;">조례 분야</div>
            <div style="font-size: 22px; font-weight: 400; color: #1f1f1f;">{분야_unique}개</div>
        </div>
        <div style="flex: 1; text-align: center;">
            <div style="font-size: 13px; font-weight: 600; color: #666; margin-bottom: 8px;">지방의회 기수</div>
            <div style="font-size: 22px; font-weight: 400; color: #1f1f1f;">{기수_range}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# -----------------------------
# 유틸리티 함수
# -----------------------------
def download_csv(data, filename):
    """CSV 다운로드 버튼"""
    csv = data.to_csv(encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )

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
# 탭1: 기수별 광역 조례 분야 분석
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
            
            # 피벗 테이블 생성 (광역별 전체 조례)
            pivot = 기수_df.pivot_table(
                index="광역",
                columns="최종분야",
                aggfunc='size',
                fill_value=0
            )
            
            # 합계(건) 계산
            row_sums = pivot.sum(axis=1)
            
            # 건수와 비율 결합 표시
            display_df = pd.DataFrame(index=pivot.index)
            
            # 합계 컬럼을 맨 앞에 추가
            display_df['합계'] = [f"{int(row_sums[idx])}건" for idx in pivot.index]
            
            for col in pivot.columns:
                display_df[col] = [
                    f"{int(pivot.loc[idx, col])}건 ({pivot.loc[idx, col]/row_sums[idx]*100:.2f}%)" 
                    if row_sums[idx] > 0 else "0건 (0%)"
                    for idx in pivot.index
                ]
            
            # N개 평균 행 추가 (실제 광역 개수)
            광역_개수 = len(pivot.index)
            avg_counts = pivot.mean(axis=0)
            avg_row = {'합계': f"{int(row_sums.mean())}건"}
            for col in pivot.columns:
                avg_val = avg_counts[col]
                avg_pct = (avg_val / avg_counts.sum() * 100) if avg_counts.sum() > 0 else 0
                avg_row[col] = f"{avg_val:.1f}건 ({avg_pct:.2f}%)"
            display_df.loc[f'{광역_개수}개 평균'] = avg_row
            
            # 표시
            st.dataframe(display_df, use_container_width=True, height=600)
            
            # 히트맵 (비율만, 평균 제외)
            pivot_pct = pivot.div(row_sums, axis=0) * 100
            heatmap_data = pivot_pct
            if not heatmap_data.empty:
                chart_data = heatmap_data.reset_index().melt(id_vars='광역', var_name='분야', value_name='비율')
                
                chart = alt.Chart(chart_data).mark_rect().encode(
                    x=alt.X('분야:N', title=''),
                    y=alt.Y('광역:N', title=''),
                    color=alt.Color('비율:Q', scale=alt.Scale(scheme='blues'), title='비율(%)'),
                    tooltip=['광역', '분야', alt.Tooltip('비율:Q', format='.2f')]
                ).properties(
                    title=f'{기수} 광역별 분야 비율 히트맵',
                    height=400
                )
                
                st.altair_chart(chart, use_container_width=True)
            
            # CSV 다운로드 (건수 테이블)
            download_df = pivot.copy()
            download_df['합계'] = row_sums
            download_csv(download_df, f"기수별_광역분석_{기수.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭2: 광역별 기수당 조례 분야 변화
# -----------------------------
with tab2:
    st.header("2️⃣ 광역자치단체별 기수당 조례 분야 변화")
    st.caption("각 광역자치단체별로 기수에 따른 분야 비율 및 증가율을 보여줍니다 (광역 자체 + 소속 기초 전체 포함)")
    
    for 광역 in 광역_list:
        with st.expander(f"📊 {광역} 분석"):
            광역_df = df[df["광역"] == 광역]
            
            # 피벗 테이블 (해당 광역의 모든 조례)
            pivot = 광역_df.pivot_table(
                index="지방의회_기수",
                columns="최종분야",
                aggfunc='size',
                fill_value=0
            )
            
            # 비율 계산
            row_sums = pivot.sum(axis=1)
            pivot_pct = pivot.div(row_sums, axis=0) * 100
            
            # 증가율 계산 (이전 기수 대비)
            pivot_growth = pivot_pct.diff()
            
            # 결합 테이블 (건수, 비율, 증가율) - 평균증가율 제거
            result_rows = []
            for idx, 기수 in enumerate(pivot_pct.index):
                row_data = {'기수': 기수, '합계': f"{int(row_sums.loc[기수])}건"}
                
                for 분야 in pivot_pct.columns:
                    건수 = int(pivot.loc[기수, 분야])
                    비율 = pivot_pct.loc[기수, 분야]
                    
                    if idx > 0:
                        증가율 = pivot_growth.loc[기수, 분야]
                        row_data[분야] = f"{건수}건 ({비율:.2f}%, {증가율:+.2f}%p)"
                    else:
                        row_data[분야] = f"{건수}건 ({비율:.2f}%)"
                
                result_rows.append(row_data)
            
            result_df = pd.DataFrame(result_rows).set_index('기수')
            
            st.dataframe(result_df, use_container_width=True, height=400)
            
            # 라인 차트 (Y축: 조례 수)
            chart_data = pivot.reset_index().melt(id_vars='지방의회_기수', var_name='분야', value_name='조례수')
            
            line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('지방의회_기수:N', title='지방의회 기수', sort=기수_list),
                y=alt.Y('조례수:Q', title='조례 수 (건)'),
                color=alt.Color('분야:N', title='분야'),
                tooltip=['지방의회_기수', '분야', '조례수']
            ).properties(
                title=f'{광역} 기수별 분야 조례 수 변화',
                height=400
            )
            
            st.altair_chart(line_chart, use_container_width=True)
            
            # CSV 다운로드
            download_df = pivot.copy()
            download_df['합계'] = row_sums
            download_csv(download_df, f"광역별_기수변화_{광역}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭3: 광역 내 기초자치단체 조례 현황
# -----------------------------
with tab3:
    st.header("3️⃣ 광역별 기초자치단체 조례 현황")
    st.caption("각 광역자치단체 내 기초단체별 조례 분야 비율과 건수를 보여줍니다 (광역 자체 포함, 중복 없음)")
    
    # 전국 기초 평균 계산 (광역 자체 제외)
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
    
    for 광역 in 광역_list:
        with st.expander(f"📊 {광역} 분석"):
            광역_df = df[df["광역"] == 광역]
            
            # 기초별로 피벗 (광역 자체 포함 - 모든 기초 값)
            pivot = 광역_df.pivot_table(
                index="기초",
                columns="최종분야",
                aggfunc='size',
                fill_value=0
            )
            
            if pivot.empty:
                st.warning(f"{광역}에 데이터가 없습니다")
                continue
            
            # 건수와 비율 결합
            row_sums = pivot.sum(axis=1)
            display_df = pd.DataFrame(index=pivot.index)
            
            # 합계 컬럼을 맨 앞에 추가
            display_df['합계'] = [f"{int(row_sums[idx])}건" for idx in pivot.index]
            
            for col in pivot.columns:
                display_df[col] = [
                    f"{int(pivot.loc[idx, col])}건 ({pivot.loc[idx, col]/row_sums[idx]*100:.2f}%)"
                    if row_sums[idx] > 0 else "0건 (0%)"
                    for idx in pivot.index
                ]
            
            # 226개 평균 행 추가
            평균_row = {'합계': f"{전국_기초_pivot.sum(axis=1).mean():.1f}건"}
            for col in 분야_list:
                if col in 전국_평균_건수.index:
                    avg_건수 = 전국_평균_건수[col]
                    avg_비율 = 전국_평균_비율[col]
                    평균_row[col] = f"{avg_건수:.1f}건 ({avg_비율:.2f}%)"
                else:
                    평균_row[col] = "0건 (0%)"
            display_df.loc['226개 평균'] = 평균_row
            
            st.dataframe(display_df, use_container_width=True, height=600)
            
            # 히트맵 (226개 평균 제외)
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
                ).properties(
                    title=f'{광역} 기초단체별 분야 비율 히트맵',
                    height=400
                )
                
                st.altair_chart(chart, use_container_width=True)
            
            # CSV 다운로드
            download_df = pivot.copy()
            download_df['합계'] = row_sums
            download_csv(download_df, f"기초단체_현황_{광역}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭4: 전체 기수별 분야 변화 추이
# -----------------------------
with tab4:
    st.header("4️⃣ 전국 기수별 분야 변화 추이")
    st.caption("전국 전체 데이터를 기준으로 기수에 따른 분야별 조례 변화를 시계열로 보여줍니다")
    
    # 전국 기수×분야 피벗
    전국_pivot = df.pivot_table(
        index="지방의회_기수",
        columns="최종분야",
        aggfunc='size',
        fill_value=0
    )
    
    전국_row_sums = 전국_pivot.sum(axis=1)
    전국_비율 = 전국_pivot.div(전국_row_sums, axis=0) * 100
    
    # 표시용 데이터프레임 (건수와 비율)
    display_df = pd.DataFrame(index=전국_pivot.index)
    
    # 합계 컬럼을 맨 앞에 추가
    display_df['합계'] = [f"{int(전국_row_sums[idx])}건" for idx in 전국_pivot.index]
    
    for col in 전국_pivot.columns:
        display_df[col] = [
            f"{int(전국_pivot.loc[idx, col])}건 ({전국_비율.loc[idx, col]:.2f}%)"
            for idx in 전국_pivot.index
        ]
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # 라인 차트 (Y축: 조례 수)
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
    
    # CSV 다운로드
    download_df = 전국_pivot.copy()
    download_df['합계'] = 전국_row_sums
    download_csv(download_df, f"전국_기수별_분야변화_{datetime.now().strftime('%Y%m%d')}.csv")

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
    
    # 기초×분야 피벗 (광역+기초 조합으로 식별)
    기초_분야_pivot = df[~df["is_광역자체"]].pivot_table(
        index='기초_full',
        columns='최종분야',
        aggfunc='size',
        fill_value=0
    )
    
    기초_비율 = 기초_분야_pivot.div(기초_분야_pivot.sum(axis=1), axis=0) * 100
    
    # 집중도 계산 (표준편차)
    집중도 = 기초_비율.std(axis=1).sort_values(ascending=False)
    
    # 최대 집중 분야 찾기
    최대_분야 = []
    for 기초_full in 집중도.index:
        max_col = 기초_비율.loc[기초_full].idxmax()
        max_val = 기초_비율.loc[기초_full, max_col]
        최대_분야.append(f"{max_col} ({max_val:.1f}%)")
    
    집중도_df = pd.DataFrame({
        '기초자치단체': 집중도.index,
        '집중도(표준편차)': 집중도.values,
        '집중 분야': 최대_분야,
        '이조례수': 기초_분야_pivot.sum(axis=1).loc[집중도.index].values
    }).reset_index(drop=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("기초단체별 집중도 순위")
        st.dataframe(집중도_df.round(2), use_container_width=True, height=600, hide_index=True)
        download_csv(집중도_df, f"기초_분야집중도_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with col2:
        st.subheader("집중도 막대 차트 (Top 30)")
        top30_집중도 = 집중도_df.head(30)
        bar_chart = alt.Chart(top30_집중도).mark_bar().encode(
            x=alt.X('집중도(표준편차):Q', title='집중도 (표준편차)'),
            y=alt.Y('기초자치단체:N', sort='-x', title=''),
            color=alt.Color('집중도(표준편차):Q', scale=alt.Scale(scheme='oranges'), legend=None),
            tooltip=['기초자치단체', alt.Tooltip('집중도(표준편차):Q', format='.2f'), '집중 분야', '이조례수']
        ).properties(height=600)
        
        st.altair_chart(bar_chart, use_container_width=True)
    
    st.markdown("---")
    st.subheader("기초단체별 분야 비율 히트맵 (Top 50)")
    
    # Top 50만 히트맵 표시
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
    기초_조례수 = df[~df["is_광역자체"]].groupby(['광역', '기초']).size().reset_index(name='이조례수')
    기초_조례수 = 기초_조례수.sort_values('이조례수', ascending=False).reset_index(drop=True)
    기초_조례수['순위'] = range(1, len(기초_조례수) + 1)
    기초_조례수 = 기초_조례수[['순위', '광역', '기초', '이조례수']]
    
    # 2. 광역자치단체만 순위
    광역_조례수 = df[df["is_광역자체"]].groupby('광역').size().reset_index(name='이조례수')
    광역_조례수 = 광역_조례수.sort_values('이조례수', ascending=False).reset_index(drop=True)
    광역_조례수['순위'] = range(1, len(광역_조례수) + 1)
    광역_조례수 = 광역_조례수[['순위', '광역', '이조례수']]
    
    # 3. 전체 순위 (기초 + 광역)
    전체_조례수 = df.groupby(['광역', '기초']).size().reset_index(name='이조례수')
    전체_조례수['구분'] = 전체_조례수.apply(lambda x: '광역' if x['광역'] == x['기초'] else '기초', axis=1)
    전체_조례수 = 전체_조례수.sort_values('이조례수', ascending=False).reset_index(drop=True)
    전체_조례수['순위'] = range(1, len(전체_조례수) + 1)
    전체_조례수 = 전체_조례수[['순위', '구분', '광역', '기초', '이조례수']]
    
    # 탭으로 3개 순위 표시
    순위_tab1, 순위_tab2, 순위_tab3 = st.tabs(["기초자치단체 순위", "광역자치단체 순위", "전체 순위"])
    
    with 순위_tab1:
        st.subheader("🏆 기초자치단체 조례 수 순위")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Top 50**")
            st.dataframe(기초_조례수.head(50), use_container_width=True, height=600, hide_index=True)
        
        with col2:
            st.markdown("**Top 30 차트**")
            top30 = 기초_조례수.head(30)
            top30['기초_full'] = top30['광역'] + ' ' + top30['기초']
            
            bar_chart = alt.Chart(top30).mark_bar().encode(
                x=alt.X('이조례수:Q', title='총 조례 수'),
                y=alt.Y('기초_full:N', sort='-x', title=''),
                color=alt.Color('광역:N', title='광역'),
                tooltip=['순위', '광역', '기초', '이조례수']
            ).properties(height=600)
            
            st.altair_chart(bar_chart, use_container_width=True)
        
        st.markdown("---")
        st.subheader("전체 기초자치단체 순위")
        st.dataframe(기초_조례수, use_container_width=True, height=400, hide_index=True)
        download_csv(기초_조례수, f"기초단체_순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with 순위_tab2:
        st.subheader("🏆 광역자치단체 조례 수 순위")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**전체 순위**")
            st.dataframe(광역_조례수, use_container_width=True, height=600, hide_index=True)
        
        with col2:
            st.markdown("**순위 차트**")
            bar_chart = alt.Chart(광역_조례수).mark_bar().encode(
                x=alt.X('이조례수:Q', title='총 조례 수'),
                y=alt.Y('광역:N', sort='-x', title=''),
                color=alt.Color('이조례수:Q', scale=alt.Scale(scheme='blues'), legend=None),
                tooltip=['순위', '광역', '이조례수']
            ).properties(height=600)
            
            st.altair_chart(bar_chart, use_container_width=True)
        
        download_csv(광역_조례수, f"광역단체_순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with 순위_tab3:
        st.subheader("🏆 전체 조례 수 순위 (기초 + 광역)")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Top 50**")
            st.dataframe(전체_조례수.head(50), use_container_width=True, height=600, hide_index=True)
        
        with col2:
            st.markdown("**Top 30 차트**")
            top30 = 전체_조례수.head(30)
            top30['표시명'] = top30.apply(
                lambda x: f"{x['광역']}" if x['구분'] == '광역' else f"{x['광역']} {x['기초']}", 
                axis=1
            )
            
            bar_chart = alt.Chart(top30).mark_bar().encode(
                x=alt.X('이조례수:Q', title='총 조례 수'),
                y=alt.Y('표시명:N', sort='-x', title=''),
                color=alt.Color('구분:N', title='구분', scale=alt.Scale(domain=['광역', '기초'], range=['#e74c3c', '#3498db'])),
                tooltip=['순위', '구분', '광역', '기초', '이조례수']
            ).properties(height=600)
            
            st.altair_chart(bar_chart, use_container_width=True)
        
        st.markdown("---")
        st.subheader("전체 순위")
        st.dataframe(전체_조례수, use_container_width=True, height=400, hide_index=True)
        download_csv(전체_조례수, f"전체_순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    # 광역별 평균
    st.markdown("---")
    st.subheader("광역별 기초단체 평균 조례 수")
    광역_평균 = 기초_조례수.groupby('광역')['이조례수'].agg(['mean', 'count']).reset_index()
    광역_평균.columns = ['광역', '평균조례수', '기초단체수']
    광역_평균 = 광역_평균.sort_values('평균조례수', ascending=False).round(2)
    
    st.dataframe(광역_평균, use_container_width=True, hide_index=True)
    
    bar_chart2 = alt.Chart(광역_평균).mark_bar().encode(
        x=alt.X('평균조례수:Q', title='평균 조례 수'),
        y=alt.Y('광역:N', sort='-x', title=''),
        color=alt.Color('평균조례수:Q', scale=alt.Scale(scheme='teals'), legend=None),
        tooltip=['광역', alt.Tooltip('평균조례수:Q', format='.2f'), '기초단체수']
    ).properties(height=400)
    
    st.altair_chart(bar_chart2, use_container_width=True)

st.markdown("---")
st.caption("© 2025 지방자치단체 조례 통계 분석 대시보드")
