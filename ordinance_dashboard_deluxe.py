# -*- coding: utf-8 -*-
# 지방자치단체 조례 통계 분석 대시보드

import os
import io
from datetime import datetime

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(page_title="조례 통계 분석", layout="wide")

# -----------------------------
# 데이터 로드
# -----------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(APP_DIR, "korean_ordinance.xlsx")

@st.cache_data(show_spinner=True)
def load_excel(path):
    return pd.read_excel(path)

@st.cache_data(show_spinner=True)
def load_excel_bytes(b):
    return pd.read_excel(io.BytesIO(b))

# -----------------------------
# 헤더
# -----------------------------
st.title("📊 지방자치단체 조례 통계 분석 대시보드")
st.markdown("---")

# 사이드바 - 데이터 업로드
with st.sidebar:
    st.header("데이터 업로드")
    uploaded = st.file_uploader("엑셀 파일 선택 (.xlsx)", type=["xlsx"])
    
    if uploaded:
        df = load_excel_bytes(uploaded.read())
        st.success(f"✅ {uploaded.name} 로드 완료")
    elif os.path.exists(DEFAULT_PATH):
        df = load_excel(DEFAULT_PATH)
        st.info(f"📁 기본 파일 사용 중")
    else:
        st.error("⚠️ 파일을 업로드해주세요")
        st.stop()
    
    st.markdown("---")
    st.markdown("### 📈 데이터 요약")
    st.metric("총 조례 수", f"{len(df):,}")

# 컬럼명 확인 및 정규화
required_cols = ["광역", "기초", "최종분야", "지방의회_기수"]
# 실제 엑셀의 컬럼명에 맞춰 매핑 (필요시 수정)
col_mapping = {
    "광역자치단체명": "광역",
    "기초자치단체명": "기초", 
    "최종 분야": "최종분야",
    "지방의회 기수": "지방의회_기수"
}
df = df.rename(columns=col_mapping)

# 필수 컬럼 체크
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"필수 컬럼이 없습니다: {', '.join(missing)}")
    st.write("현재 컬럼:", df.columns.tolist())
    st.stop()

# 데이터 정제
df = df.dropna(subset=required_cols)
df["지방의회_기수"] = df["지방의회_기수"].astype(str).str.replace("기", "").astype(int)

# -----------------------------
# 유틸리티 함수
# -----------------------------
@st.cache_data
def get_unique_values(dataframe, column):
    return sorted(dataframe[column].dropna().unique().tolist())

광역_list = get_unique_values(df, "광역")
분야_list = get_unique_values(df, "최종분야")
기수_list = sorted(df["지방의회_기수"].unique().tolist())

with st.sidebar:
    st.metric("광역자치단체", len(광역_list))
    st.metric("기초자치단체", df["기초"].nunique())
    st.metric("조례 분야", len(분야_list))
    st.metric("지방의회 기수", f"{min(기수_list)}기~{max(기수_list)}기")

def create_percentage_table(data, index_cols, value_col, columns_col):
    """비율(%) 테이블 생성"""
    pivot = data.pivot_table(
        index=index_cols, 
        columns=columns_col, 
        values=value_col,
        aggfunc='size',
        fill_value=0
    )
    
    # 비율 계산
    row_sums = pivot.sum(axis=1)
    pivot_pct = pivot.div(row_sums, axis=0) * 100
    
    # 합계 열 추가
    pivot_pct['합계(건)'] = row_sums
    
    return pivot_pct

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
    "2️⃣ 광역별 기수 변화", 
    "3️⃣ 기초자치단체 현황",
    "4️⃣ 기수별 분야 변화 추이",
    "5️⃣ 광역 분야 집중도",
    "6️⃣ 기초단체 활성도"
])

# -----------------------------
# 탭1: 기수별 광역 조례 분야 분석
# -----------------------------
with tab1:
    st.header("1️⃣ 기수별 광역자치단체 조례 분야 분석")
    st.caption("각 기수별로 17개 광역자치단체의 조례 분야 비율을 보여줍니다")
    
    for 기수 in 기수_list:
        with st.expander(f"📊 {기수}기 분석", expanded=(기수==기수_list[-1])):
            기수_df = df[df["지방의회_기수"] == 기수]
            
            if len(기수_df) == 0:
                st.warning(f"{기수}기 데이터가 없습니다")
                continue
            
            # 피벗 테이블 생성
            pivot = 기수_df.pivot_table(
                index="광역",
                columns="최종분야",
                aggfunc='size',
                fill_value=0
            )
            
            # 비율 계산
            row_sums = pivot.sum(axis=1)
            pivot_pct = pivot.div(row_sums, axis=0) * 100
            pivot_pct['합계(건)'] = row_sums.astype(int)
            
            # 17개 평균 행 추가
            avg_row = pivot.mean(axis=0)
            avg_pct = (avg_row / avg_row.sum() * 100) if avg_row.sum() > 0 else avg_row * 0
            avg_pct['합계(건)'] = int(row_sums.mean())
            pivot_pct.loc['17개 평균'] = avg_pct
            
            # 소수점 정리
            display_df = pivot_pct.round(2)
            
            # 표시
            st.dataframe(display_df, use_container_width=True, height=600)
            
            # 히트맵
            heatmap_data = pivot_pct.drop(columns=['합계(건)']).drop(index='17개 평균')
            if not heatmap_data.empty:
                chart_data = heatmap_data.reset_index().melt(id_vars='광역', var_name='분야', value_name='비율')
                
                chart = alt.Chart(chart_data).mark_rect().encode(
                    x=alt.X('분야:N', title=''),
                    y=alt.Y('광역:N', title=''),
                    color=alt.Color('비율:Q', scale=alt.Scale(scheme='blues'), title='비율(%)'),
                    tooltip=['광역', '분야', alt.Tooltip('비율:Q', format='.2f')]
                ).properties(
                    title=f'{기수}기 광역별 분야 비율 히트맵',
                    height=400
                )
                
                st.altair_chart(chart, use_container_width=True)
            
            # CSV 다운로드
            download_csv(display_df, f"기수별_광역분석_{기수}기_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭2: 광역별 기수당 조례 분야 변화
# -----------------------------
with tab2:
    st.header("2️⃣ 광역자치단체별 기수당 조례 분야 변화")
    st.caption("각 광역자치단체별로 기수에 따른 분야 비율 및 증가율을 보여줍니다")
    
    for 광역 in 광역_list:
        with st.expander(f"📊 {광역} 분석"):
            광역_df = df[df["광역"] == 광역]
            
            # 피벗 테이블
            pivot = 광역_df.pivot_table(
                index="지방의회_기수",
                columns="최종분야",
                aggfunc='size',
                fill_value=0
            )
            
            # 비율 계산
            row_sums = pivot.sum(axis=1)
            pivot_pct = pivot.div(row_sums, axis=0) * 100
            
            # 증가율 계산
            pivot_growth = pivot_pct.diff()
            
            # 결합 테이블 (비율 / 증가율)
            result_rows = []
            for 기수 in pivot_pct.index:
                row_data = {'기수': f'{기수}기'}
                for 분야 in pivot_pct.columns:
                    비율 = pivot_pct.loc[기수, 분야]
                    증가율 = pivot_growth.loc[기수, 분야] if 기수 != pivot_pct.index[0] else 0
                    row_data[분야] = f"{비율:.2f}% ({증가율:+.2f}%p)" if 기수 != pivot_pct.index[0] else f"{비율:.2f}%"
                row_data['합계(건)'] = int(row_sums.loc[기수])
                row_data['평균증가율'] = f"{pivot_growth.loc[기수].mean():+.2f}%p" if 기수 != pivot_pct.index[0] else "-"
                result_rows.append(row_data)
            
            result_df = pd.DataFrame(result_rows).set_index('기수')
            
            st.dataframe(result_df, use_container_width=True, height=400)
            
            # 라인 차트
            chart_data = pivot_pct.reset_index().melt(id_vars='지방의회_기수', var_name='분야', value_name='비율')
            
            line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('지방의회_기수:O', title='지방의회 기수'),
                y=alt.Y('비율:Q', title='비율(%)'),
                color=alt.Color('분야:N', title='분야'),
                tooltip=['지방의회_기수', '분야', alt.Tooltip('비율:Q', format='.2f')]
            ).properties(
                title=f'{광역} 기수별 분야 비율 변화',
                height=400
            )
            
            st.altair_chart(line_chart, use_container_width=True)
            
            download_csv(result_df, f"광역별_기수변화_{광역}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭3: 광역 내 기초자치단체 조례 현황
# -----------------------------
with tab3:
    st.header("3️⃣ 광역 내 기초자치단체 조례 현황")
    st.caption("각 광역자치단체 내 기초단체별 조례 분야 비율을 보여줍니다")
    
    # 전국 226개 기초 평균 계산
    전국_기초_pivot = df.pivot_table(
        index="기초",
        columns="최종분야",
        aggfunc='size',
        fill_value=0
    )
    전국_기초_비율 = 전국_기초_pivot.div(전국_기초_pivot.sum(axis=1), axis=0) * 100
    전국_평균 = 전국_기초_비율.mean(axis=0)
    
    for 광역 in 광역_list:
        with st.expander(f"📊 {광역} 분석"):
            광역_df = df[df["광역"] == 광역]
            
            # 광역 자체 데이터
            광역_분야 = 광역_df.groupby("최종분야").size()
            광역_합계 = 광역_분야.sum()
            광역_비율 = (광역_분야 / 광역_합계 * 100) if 광역_합계 > 0 else 광역_분야 * 0
            
            # 기초 데이터
            기초_pivot = 광역_df.pivot_table(
                index="기초",
                columns="최종분야",
                aggfunc='size',
                fill_value=0
            )
            
            기초_row_sums = 기초_pivot.sum(axis=1)
            기초_비율 = 기초_pivot.div(기초_row_sums, axis=0) * 100
            기초_비율['합계(건)'] = 기초_row_sums.astype(int)
            
            # 광역 행 추가
            광역_row = 광역_비율.to_dict()
            광역_row['합계(건)'] = int(광역_합계)
            기초_비율.loc[f'[{광역}]'] = 광역_row
            
            # 226개 평균 행 추가
            평균_row = 전국_평균.to_dict()
            평균_row['합계(건)'] = int(전국_기초_pivot.sum(axis=1).mean())
            기초_비율.loc['226개 평균'] = 평균_row
            
            display_df = 기초_비율.round(2)
            
            st.dataframe(display_df, use_container_width=True, height=600)
            
            # 히트맵
            heatmap_data = 기초_비율.drop(columns=['합계(건)']).drop(index=['226개 평균', f'[{광역}]'])
            if not heatmap_data.empty:
                chart_data = heatmap_data.reset_index().melt(id_vars='기초', var_name='분야', value_name='비율')
                
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
            
            download_csv(display_df, f"기초단체_현황_{광역}_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭4: 전체 기수별 분야 변화 추이
# -----------------------------
with tab4:
    st.header("4️⃣ 전국 기수별 분야 변화 추이")
    st.caption("전국 전체 데이터를 기준으로 기수에 따른 분야별 조례 비율 변화를 시계열로 보여줍니다")
    
    # 전국 기수×분야 피벗
    전국_pivot = df.pivot_table(
        index="지방의회_기수",
        columns="최종분야",
        aggfunc='size',
        fill_value=0
    )
    
    전국_row_sums = 전국_pivot.sum(axis=1)
    전국_비율 = 전국_pivot.div(전국_row_sums, axis=0) * 100
    전국_비율['합계(건)'] = 전국_row_sums.astype(int)
    
    st.dataframe(전국_비율.round(2), use_container_width=True, height=400)
    
    # 라인 차트
    chart_data = 전국_비율.drop(columns=['합계(건)']).reset_index().melt(
        id_vars='지방의회_기수', 
        var_name='분야', 
        value_name='비율'
    )
    
    line_chart = alt.Chart(chart_data).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X('지방의회_기수:O', title='지방의회 기수'),
        y=alt.Y('비율:Q', title='비율(%)'),
        color=alt.Color('분야:N', title='분야'),
        tooltip=['지방의회_기수', '분야', alt.Tooltip('비율:Q', format='.2f')]
    ).properties(
        title='전국 기수별 분야 비율 변화 추이',
        height=500
    )
    
    st.altair_chart(line_chart, use_container_width=True)
    
    download_csv(전국_비율, f"전국_기수별_분야변화_{datetime.now().strftime('%Y%m%d')}.csv")

# -----------------------------
# 탭5: 광역 간 분야 집중도 비교
# -----------------------------
with tab5:
    st.header("5️⃣ 광역자치단체 간 분야 집중도 비교")
    st.caption("각 광역이 특정 분야에 얼마나 집중하는지 비교합니다 (집중도 = 표준편차)")
    
    # 광역×분야 피벗
    광역_분야_pivot = df.pivot_table(
        index="광역",
        columns="최종분야",
        aggfunc='size',
        fill_value=0
    )
    
    광역_비율 = 광역_분야_pivot.div(광역_분야_pivot.sum(axis=1), axis=0) * 100
    
    # 집중도 계산 (표준편차)
    집중도 = 광역_비율.std(axis=1).sort_values(ascending=False)
    집중도_df = pd.DataFrame({
        '광역': 집중도.index,
        '집중도(표준편차)': 집중도.values,
        '총조례수': 광역_분야_pivot.sum(axis=1).loc[집중도.index].values
    }).reset_index(drop=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("광역별 집중도 순위")
        st.dataframe(집중도_df.round(2), use_container_width=True, height=600)
        download_csv(집중도_df, f"광역_분야집중도_{datetime.now().strftime('%Y%m%d')}.csv")
    
    with col2:
        st.subheader("집중도 막대 차트")
        bar_chart = alt.Chart(집중도_df).mark_bar().encode(
            x=alt.X('집중도(표준편차):Q', title='집중도 (표준편차)'),
            y=alt.Y('광역:N', sort='-x', title=''),
            color=alt.Color('집중도(표준편차):Q', scale=alt.Scale(scheme='oranges'), legend=None),
            tooltip=['광역', alt.Tooltip('집중도(표준편차):Q', format='.2f'), '총조례수']
        ).properties(height=600)
        
        st.altair_chart(bar_chart, use_container_width=True)
    
    st.markdown("---")
    st.subheader("광역별 분야 비율 히트맵")
    
    heatmap_data = 광역_비율.reset_index().melt(id_vars='광역', var_name='분야', value_name='비율')
    
    heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('분야:N', title=''),
        y=alt.Y('광역:N', title='', sort=집중도.index.tolist()),
        color=alt.Color('비율:Q', scale=alt.Scale(scheme='viridis'), title='비율(%)'),
        tooltip=['광역', '분야', alt.Tooltip('비율:Q', format='.2f')]
    ).properties(
        title='광역별 분야 비율 전체 비교',
        height=500
    )
    
    st.altair_chart(heatmap, use_container_width=True)

# -----------------------------
# 탭6: 기초자치단체 조례 활성도 순위
# -----------------------------
with tab6:
    st.header("6️⃣ 기초자치단체 조례 활성도 순위")
    st.caption("전국 기초자치단체의 총 조례 수 기준 순위입니다")
    
    # 기초단체별 총 조례 수
    기초_조례수 = df.groupby(['광역', '기초']).size().reset_index(name='총조례수')
    기초_조례수 = 기초_조례수.sort_values('총조례수', ascending=False).reset_index(drop=True)
    기초_조례수['순위'] = range(1, len(기초_조례수) + 1)
    기초_조례수 = 기초_조례수[['순위', '광역', '기초', '총조례수']]
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🏆 Top 50 활성 기초단체")
        st.dataframe(기초_조례수.head(50), use_container_width=True, height=600)
    
    with col2:
        st.subheader("📊 Top 30 막대 차트")
        top30 = 기초_조례수.head(30)
        top30['기초_full'] = top30['광역'] + ' ' + top30['기초']
        
        bar_chart = alt.Chart(top30).mark_bar().encode(
            x=alt.X('총조례수:Q', title='총 조례 수'),
            y=alt.Y('기초_full:N', sort='-x', title=''),
            color=alt.Color('광역:N', title='광역'),
            tooltip=['순위', '광역', '기초', '총조례수']
        ).properties(height=600)
        
        st.altair_chart(bar_chart, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📋 전체 기초자치단체 순위")
    st.dataframe(기초_조례수, use_container_width=True, height=400)
    download_csv(기초_조례수, f"기초단체_활성도순위_{datetime.now().strftime('%Y%m%d')}.csv")
    
    # 광역별 평균
    st.markdown("---")
    st.subheader("광역별 기초단체 평균 조례 수")
    광역_평균 = 기초_조례수.groupby('광역')['총조례수'].agg(['mean', 'count']).reset_index()
    광역_평균.columns = ['광역', '평균조례수', '기초단체수']
    광역_평균 = 광역_평균.sort_values('평균조례수', ascending=False).round(2)
    
    st.dataframe(광역_평균, use_container_width=True)
    
    bar_chart2 = alt.Chart(광역_평균).mark_bar().encode(
        x=alt.X('평균조례수:Q', title='평균 조례 수'),
        y=alt.Y('광역:N', sort='-x', title=''),
        color=alt.Color('평균조례수:Q', scale=alt.Scale(scheme='teals'), legend=None),
        tooltip=['광역', alt.Tooltip('평균조례수:Q', format='.2f'), '기초단체수']
    ).properties(height=400)
    
    st.altair_chart(bar_chart2, use_container_width=True)

st.markdown("---")
st.caption("© 2025 지방자치단체 조례 통계 분석 대시보드")
