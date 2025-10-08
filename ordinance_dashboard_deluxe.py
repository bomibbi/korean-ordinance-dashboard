# -*- coding: utf-8 -*-
# ordinance_dashboard_deluxe_fixed_github.py
# GitHub / Streamlit Cloud 환경 전용
# 자동으로 data/korean_ordinance.xlsx 파일을 읽습니다.

import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="조례 통계 대시보드 (GitHub Fixed)", layout="wide")

# =====================================================
# ✅ 데이터 로드 (엑셀/CSV 자동 감지)
# =====================================================
@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    if path.endswith(".xlsx"):
        st.caption("엑셀 파일 감지됨 → pd.read_excel() 사용")
        return pd.read_excel(path, engine="openpyxl")
    else:
        last_err = None
        for enc in ["cp949", "utf-8-sig", "utf-8"]:
            try:
                df = pd.read_csv(path, encoding=enc)
                st.caption(f"CSV 파일 인코딩 감지됨: **{enc}**")
                return df
            except Exception as e:
                last_err = e
        raise last_err

# =====================================================
# ✅ 데이터 정규화
# =====================================================
def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["광역", "기초", "지방의회_기수", "최종분야"]:
        df[col] = df[col].astype(str).str.strip()
    df["광역자체"] = (df["기초"] == df["광역"])
    return df

ORDER_GISU = [f"지방의회 {i}기" for i in range(1, 10)]
ALIAS = {"강원특별자치도": ["강원도"], "제주특별자치도": ["제주도"]}

def region_names(gwangyeok: str):
    return [gwangyeok] + ALIAS.get(gwangyeok, [])

# =====================================================
# ✅ 표 생성 함수들
# =====================================================
def build_tab1_by_gisu(df, gisu):
    use = df[df["지방의회_기수"] == gisu]
    pivot = use.pivot_table(index="광역", columns="최종분야", aggfunc="size", fill_value=0)
    pivot["합계"] = pivot.sum(axis=1)
    return pivot.reset_index()

def build_tab2_by_region(df, gwangyeok):
    use = df[df["광역"].isin(region_names(gwangyeok))].copy()
    pivot = use.pivot_table(index="지방의회_기수", columns="최종분야", aggfunc="size", fill_value=0)
    pivot = pivot.reindex(ORDER_GISU, fill_value=0)
    pivot["합계"] = pivot.sum(axis=1)

    s = pd.to_numeric(pivot["합계"], errors="coerce")
    growth = s.pct_change() * 100
    avg_growth = float(growth.iloc[1:].mean()) if len(growth) > 1 else 0.0

    out = pivot.reset_index()
    out.loc[len(out)] = ["평균 증가율(%)"] + [None]*(out.shape[1]-2) + [avg_growth]
    return out, avg_growth

def build_tab3_gicho(df, gwangyeok):
    use = df[df["광역"].isin(region_names(gwangyeok))].copy()
    pivot = use.pivot_table(index="기초", columns="최종분야", aggfunc="size", fill_value=0)
    pivot["합계"] = pivot.sum(axis=1)
    return pivot.reset_index()

def build_tab4_national(df):
    pivot = df.pivot_table(index="지방의회_기수", columns="최종분야", aggfunc="size", fill_value=0)
    pivot = pivot.reset_index()
    pivot["_k"] = pivot["지방의회_기수"].str.extract("(\d+)").astype(float)
    pivot = pivot.sort_values("_k").drop(columns=["_k"])
    pivot["합계"] = pivot.drop(columns=["지방의회_기수"]).sum(axis=1)
    return pivot

# =====================================================
# ✅ Streamlit 레이아웃
# =====================================================
st.title("지방자치단체 조례 통계 대시보드 (GitHub Fixed)")
st.caption("자동으로 /data/korean_ordinance.xlsx 파일을 불러옵니다. (엑셀/CSV 모두 지원)")

# GitHub 환경에 맞게 경로 고정
path = "data/korean_ordinance.xlsx"
st.caption(f"📂 현재 데이터 경로: `{path}`")

# 데이터 로드
df_raw = load_data(path)
df = normalize(df_raw)

with st.sidebar:
    st.header("데이터 개요")
    st.write(f"- 전체 행 수: **{len(df):,}**")
    st.write(f"- 광역 수(고유): **{df['광역'].nunique()}**")
    st.write(f"- 기초 수(고유): **{df['기초'].nunique()}**")
    st.divider()
    st.info("✅ '기초 == 광역' 인 행은 광역자체 조례로 처리됩니다.")

# =====================================================
# ✅ 탭 구성
# =====================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "① 기수별 광역 분석",
    "② 광역별 기수 변화",
    "③ 기초자치단체 현황",
    "④ 전국 기수별 분야 변화"
])

with tab1:
    st.subheader("① 기수별 광역 분석")
    gisu = st.selectbox("지방의회 기수 선택", ORDER_GISU, index=0)
    t1 = build_tab1_by_gisu(df, gisu)
    st.dataframe(t1, use_container_width=True, hide_index=True)
    st.download_button("CSV 다운로드", t1.to_csv(index=False, encoding="utf-8-sig"), "기수별_광역분석.csv")

with tab2:
    st.subheader("② 광역별 기수 변화")
    gwang = st.selectbox("광역 선택", sorted(df["광역"].unique()), index=0)
    t2, avg = build_tab2_by_region(df, gwang)
    st.dataframe(t2, use_container_width=True, hide_index=True)
    st.success(f"평균 증가율(%) : {avg:.2f}")
    st.download_button("CSV 다운로드", t2.to_csv(index=False, encoding="utf-8-sig"), "광역별_기수변화.csv")

with tab3:
    st.subheader("③ 기초자치단체 현황")
    gwang2 = st.selectbox("광역 선택 (기초 기준)", sorted(df["광역"].unique()), index=0)
    t3 = build_tab3_gicho(df, gwang2)
    st.dataframe(t3, use_container_width=True, hide_index=True)
    st.download_button("CSV 다운로드", t3.to_csv(index=False, encoding="utf-8-sig"), "기초자치단체현황.csv")

with tab4:
    st.subheader("④ 전국 기수별 분야 변화")
    t4 = build_tab4_national(df)
    st.dataframe(t4, use_container_width=True, hide_index=True)
    st.download_button("CSV 다운로드", t4.to_csv(index=False, encoding="utf-8-sig"), "전국_기수별_분야변화.csv")
