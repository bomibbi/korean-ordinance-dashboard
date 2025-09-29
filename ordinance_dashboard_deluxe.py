# -*- coding: utf-8 -*-
# 지방자치단체 조례 교차분석 대시보드 (Deluxe v3.0)
# - 위임/자치 판별: <위임조례 후보 여부>만 사용
# - 기간 필터: <제개정일자>만 사용 (프리셋 '전체'이면 기간 필터 미적용)
# - '대표 연도'는 완전히 무시
# - 모드별 차트/피벗 + 공통 피벗 + CSV 다운로드
# - 데이터 점검 패널/필터 초기화 버튼 포함

import os, io, re
from datetime import datetime

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(page_title="조례 교차분석 대시보드", layout="wide")

# -----------------------------
# 경로 설정
# -----------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NAME = "korean_ordinance.xlsx"
DEFAULT_PATH = os.path.join(APP_DIR, DEFAULT_NAME)
PARQUET_PATH = os.path.join(APP_DIR, "data", "ordinances.parquet")
EXCEL_DATA_PATH = os.path.join(APP_DIR, "data", "korean_ordinance.xlsx")

@st.cache_data(show_spinner=True)
def read_excel_path(path: str) -> pd.DataFrame:
    return pd.read_excel(path)

@st.cache_data(show_spinner=True)
def read_excel_bytes(b: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(b))

@st.cache_data(show_spinner=True)
def read_parquet_path(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)

def load_data(file_uploader, path_input: str):
    if os.path.exists(PARQUET_PATH):
        return read_parquet_path(PARQUET_PATH), "data/ordinances.parquet"
    if os.path.exists(EXCEL_DATA_PATH):
        return read_excel_path(EXCEL_DATA_PATH), "data/korean_ordinance.xlsx"
    if file_uploader is not None:
        return read_excel_bytes(file_uploader.read()), f"업로드: {file_uploader.name}"
    if path_input and os.path.exists(path_input):
        return read_excel_path(path_input), f"경로: {path_input}"
    if os.path.exists(DEFAULT_PATH):
        return read_excel_path(DEFAULT_PATH), f"기본: {DEFAULT_PATH}"
    return None, None

# -----------------------------
# 헤더/도움말
# -----------------------------
st.title("지방자치단체 조례 교차분석 대시보드")
st.caption(
    "ℹ️ **사용법**: 왼쪽 **설정** 메뉴에서 **분석 모드**를 선택하고, "
    "**기본/비교 지역·분야·기수·기간·조례유형**을 조절하세요. "
    "기간은 **제개정일자** 기준으로 적용되며, **전체**를 선택하면 기간 제한이 없습니다. "
    "**차트**와 **피벗/교차표**는 현재 조건을 반영해 자동으로 갱신됩니다. "
    "**공통 피벗**은 아래 Expander에서 같은 형식으로 확인·다운로드할 수 있습니다."
)

with st.sidebar:
    st.header("데이터")
    up = st.file_uploader("엑셀 업로드(.xlsx)", type=["xlsx"])
    path = st.text_input("로컬 경로 입력", value=DEFAULT_PATH)

df, origin = load_data(up, path)
if df is None:
    st.warning("데이터 파일을 찾을 수 없습니다. 업로드하거나 경로를 입력하거나, 앱과 같은 폴더에 기본 파일명을 두세요.")
    st.stop()

# -----------------------------
# 기본 컬럼 점검/정규화
# -----------------------------
required = ["광역", "기초", "최종분야", "지방의회_기수"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error(f"필수 컬럼 없음: {', '.join(missing)}")
    st.stop()

# 제개정일자만 날짜형으로 정규화 (대표 연도는 사용하지 않음)
if "제개정일자" in df.columns:
    df["제개정일자"] = pd.to_datetime(df["제개정일자"], errors="coerce")

# -----------------------------
# 위임/자치 판별: <위임조례 후보 여부>만 사용
# -----------------------------
def _norm(s: str) -> str:
    return re.sub(r"[\u00A0\u2000-\u200B\s\(\)\[\]\{\}_\-]+", "", str(s)).lower()

def detect_deleg_col(columns):
    preferred = "위임조례 후보 여부"
    if preferred in columns:
        return preferred
    norm_map = {c: _norm(c) for c in columns}
    # 보조 탐지(파일마다 이름이 조금 다를 때)
    for key in ["위임조례후보여부", "위임조례후보", "위임여부", "정부위임여부", "위임조례"]:
        for c, n in norm_map.items():
            if key in n:
                return c
    return None

def parse_delegation(series: pd.Series) -> pd.Series:
    # bool이면 그대로
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    # 숫자(0/1)
    num = pd.to_numeric(series, errors="ignore")
    flag = pd.Series(False, index=series.index)
    if pd.api.types.is_numeric_dtype(num):
        flag = num != 0
    else:
        s = series.astype(str)
        s = s.str.replace(r"[\u00A0\u2000-\u200B]", "", regex=True).str.strip().str.lower()
        true_tokens  = {"true","t","y","yes","1","1.0","위임","예","o","true."}
        false_tokens = {"false","f","n","no","0","0.0","자치","아니오","x","false."}
        flag = s.isin(true_tokens)
        # false 토큰은 굳이 다시 지정할 필요X (기본 False)
    return flag.fillna(False)

deleg_col = detect_deleg_col(df.columns)
if not deleg_col:
    st.error("위임 판별 컬럼 '<위임조례 후보 여부>'를 찾을 수 없습니다.")
    st.stop()

df["_위임여부"] = parse_delegation(df[deleg_col])
df["조례유형"] = np.where(df["_위임여부"], "위임조례", "자치조례")

# -----------------------------
# 유틸
# -----------------------------
def uniq_vals(col):
    vals = df[col].dropna().unique().tolist() if col in df.columns else []
    try: return sorted(vals)
    except: return vals

def as_grouped(series_df, key_col, label):
    if series_df is None or series_df.empty:
        return pd.DataFrame({key_col:[], "건수":[], "그룹":[]})
    g = series_df.groupby(key_col).size().reset_index(name="건수")
    g["그룹"] = label
    return g

def add_ratio(frame, by_cols):
    if frame is None or frame.empty: return frame
    total = frame.groupby(by_cols)["건수"].transform("sum")
    frame["비율(%)"] = np.where(total>0, frame["건수"]/total*100, 0.0)
    return frame

def grouped_bar(dfA, dfB, x, title, color_key="그룹"):
    data = pd.concat([dfA, dfB], ignore_index=True) if dfB is not None else dfA
    if data is None or data.empty:
        st.info("표시할 데이터가 없습니다."); return
    y = "비율(%)" if "비율(%)" in data.columns else "건수"
    enc = {"x": alt.X(x, sort='-y', title=None), "y": alt.Y(y, title=None), "tooltip": list(data.columns)}
    if color_key in data.columns:
        enc["color"] = alt.Color(color_key, title=None)
    ch = alt.Chart(data).mark_bar().encode(**enc).properties(title=title, height=420)
    st.altair_chart(ch, use_container_width=True)

def heatmap(df_, x, y, color, title):
    if df_ is None or df_.empty:
        st.info("표시할 데이터가 없습니다."); return
    ch = alt.Chart(df_).mark_rect().encode(
        x=alt.X(x, title=None), y=alt.Y(y, title=None),
        color=alt.Color(color, title=None), tooltip=list(df_.columns)
    ).properties(title=title, height=420)
    st.altair_chart(ch, use_container_width=True)

def make_filename(prefix, mode, as_ratio, type_choice):
    today = datetime.now().strftime("%Y%m%d")
    typ = {"전체":"all","위임조례만":"deleg","자치조례만":"self"}[type_choice]
    return f"{prefix}_{mode.replace('×','x')}_{'ratio' if as_ratio else 'count'}_{typ}_{today}.csv"

# -----------------------------
# 사이드바(설정)
# -----------------------------
with st.sidebar:
    st.header("설정")

    # 필터 초기화
    if st.button("🔄 필터 초기화"):
        st.session_state.clear()
        st.rerun()                # 최신 버전에서의 재실행

    mode = st.radio(
        "분석 모드",
        ["총괄 현황","지역×분야","지역×기수","기수×분야","광역×기초","광역×분야×기수","위임조례 전용"],
        index=0
    )

    st.subheader("지역 선택")
    provs = ["전체"] + uniq_vals("광역")
    base_prov = st.selectbox("기본 지역(광역)", options=provs, index=0)
    base_city_opts = ["전체"]
    if base_prov != "전체":
        base_city_opts += sorted(df.loc[df["광역"]==base_prov,"기초"].dropna().unique().tolist())
    base_city = st.selectbox("기본 지역(기초)", options=base_city_opts, index=0)

    compare_on = st.checkbox("비교 지역 사용", value=False)
    comp_prov = comp_city = "전체"
    if compare_on:
        comp_prov = st.selectbox("비교 지역(광역)", options=provs, index=0)
        comp_city_opts = ["전체"]
        if comp_prov != "전체":
            comp_city_opts += sorted(df.loc[df["광역"]==comp_prov,"기초"].dropna().unique().tolist())
        comp_city = st.selectbox("비교 지역(기초)", options=comp_city_opts, index=0)

    st.subheader("필터")
    fields_all = uniq_vals("최종분야")
    terms_all  = uniq_vals("지방의회_기수")
    fields_sel = st.multiselect("분야", options=fields_all, default=fields_all)
    terms_sel  = st.multiselect("기수", options=terms_all,  default=terms_all)

    st.subheader("기간 (제개정일자 기준)")
    # 프리셋 계산: 제개정일자만 사용
    if "제개정일자" in df.columns and df["제개정일자"].notna().any():
        dmin = df["제개정일자"].min()
        dmax = df["제개정일자"].max()
    else:
        dmin = dmax = None

    preset = st.radio("프리셋", ["전체","최근 10년","최근 5년"], horizontal=True)
    if dmin is None or dmax is None or preset == "전체":
        date_range = (None, None)
    else:
        if preset == "최근 10년":
            date_range = (dmax - pd.DateOffset(years=10) + pd.DateOffset(days=1), dmax)
        else:
            date_range = (dmax - pd.DateOffset(years=5) + pd.DateOffset(days=1), dmax)

    st.subheader("보기 옵션")
    as_ratio = st.toggle("비율(%) 보기", value=True)
    topn = st.slider("Top N", 5, 50, 20, 5)

    st.subheader("조례유형")
    type_choice = st.radio("대상", ["전체", "위임조례만", "자치조례만"], horizontal=True)

    with st.expander("데이터 점검(선택)", expanded=False):
        st.write(f"사용 컬럼(위임 판별): `{deleg_col}`")
        st.write("원본 값 분포:", df[deleg_col].value_counts(dropna=False).head(20))
        st.write("파싱 결과(True=위임):", df["_위임여부"].value_counts(dropna=False))
        st.write("유형 분포(전체):", df["조례유형"].value_counts(dropna=False))

# -----------------------------
# 글로벌 필터 (기간=제개정일자만, 대표 연도 무시)
# -----------------------------
mask = pd.Series(True, index=df.index)

# 기간
if date_range[0] is not None and date_range[1] is not None and "제개정일자" in df.columns:
    dt = df["제개정일자"]
    mask &= dt.between(date_range[0], date_range[1])  # '전체'는 미적용

# 분야/기수
if len(fields_sel) > 0:
    mask &= df["최종분야"].isin(fields_sel)
if len(terms_sel) > 0:
    mask &= df["지방의회_기수"].isin(terms_sel)

# 조례유형
if type_choice == "위임조례만":
    mask &= (df["조례유형"] == "위임조례")
elif type_choice == "자치조례만":
    mask &= (df["조례유형"] == "자치조례")

def region_mask(prov, city):
    m = pd.Series(True, index=df.index)
    if prov != "전체": m &= (df["광역"]==prov)
    if city != "전체": m &= (df["기초"]==city)
    return m

base_mask = region_mask(base_prov, base_city)
comp_mask = region_mask(comp_prov, comp_city) if compare_on else None

base_df = df[mask & base_mask].copy()
comp_df = df[mask & comp_mask].copy() if compare_on else None
all_df  = df[mask].copy()

# -----------------------------
# 상단 요약
# -----------------------------
c1,c2,c3,c4 = st.columns(4)
c1.metric("전체(현재 조건)", f"{len(all_df):,}")
c2.metric("기본 지역", f"{len(base_df):,}")
c3.metric("비교 지역", f"{len(comp_df):,}" if comp_df is not None else "-")
c4.metric("유형(위임/자치)", f"{int(df['_위임여부'].sum()):,} / {int((~df['_위임여부']).sum()):,}")

if len(all_df) == 0:
    st.info("현재 필터 조합에 해당하는 데이터가 0건입니다. 좌측 **필터 초기화**를 눌러 기본값으로 되돌려 보세요.")
st.divider()

# -----------------------------
# (1) 차트
# -----------------------------
st.subheader("차트")

if mode == "총괄 현황":
    st.markdown("**광역별 총 조례 수 (현재 조건)**")
    g = all_df.groupby("광역").size().reset_index(name="건수").sort_values("건수", ascending=False).head(topn)
    if as_ratio and not g.empty:
        tot = g["건수"].sum()
        g["비율(%)"] = (g["건수"]/tot*100) if tot>0 else 0.0
    g["그룹"] = "전체"
    grouped_bar(g, None, "광역", "광역별 분포(비율/건수)")
    st.caption("선택한 조건에서 광역 단위의 상대/절대 규모를 비교합니다.")

    st.markdown("**선택 광역 내부: 기초별 총 조례 수**")
    if base_prov != "전체":
        h = all_df[all_df["광역"]==base_prov].groupby("기초").size().reset_index(name="건수").sort_values("건수", ascending=False).head(topn)
        if as_ratio and not h.empty:
            tot_h = h["건수"].sum()
            h["비율(%)"] = (h["건수"]/tot_h*100) if tot_h>0 else 0.0
        h["그룹"] = "전체"
        grouped_bar(h, None, "기초", f"{base_prov} 기초별 분포(비율/건수)")
        st.caption("선택 광역 내부의 기초 자치단체 분포입니다.")
    else:
        st.info("좌측에서 광역을 선택하면 하위 기초 분포가 표시됩니다.")

elif mode == "지역×분야":
    st.markdown("**분야 분포 비교 (기본 지역 vs 비교 지역)**")
    a = as_grouped(base_df, "최종분야", "기본 지역").sort_values("건수", ascending=False).head(topn)
    b = as_grouped(comp_df, "최종분야", "비교 지역").sort_values("건수", ascending=False).head(topn) if compare_on else None
    if as_ratio:
        if not a.empty: a = add_ratio(a, ["그룹"])
        if b is not None and not b.empty: b = add_ratio(b, ["그룹"])
    grouped_bar(a, b, "최종분야", "분야별 분포(비율/건수)")
    st.caption("두 지역의 분야 분포를 한 그래프에서 나란히 비교합니다.")

elif mode == "지역×기수":
    st.markdown("**기수 분포 비교 (기본 지역 vs 비교 지역)**")
    a = as_grouped(base_df, "지방의회_기수", "기본 지역")
    b = as_grouped(comp_df, "지방의회_기수", "비교 지역") if compare_on else None
    if as_ratio:
        if not a.empty: a = add_ratio(a, ["그룹"])
        if b is not None and not b.empty: b = add_ratio(b, ["그룹"])
    grouped_bar(a, b, "지방의회_기수", "기수별 분포(비율/건수)")
    st.caption("각 지역의 기수별 조례 비중 또는 건수를 비교합니다.")

elif mode == "기수×분야":
    st.markdown("**기수 × 분야 히트맵**")
    g = all_df.groupby(["지방의회_기수","최종분야"]).size().reset_index(name="건수")
    if as_ratio and not g.empty:
        g["총합"] = g.groupby("지방의회_기수")["건수"].transform("sum")
        g["비율(%)"] = np.where(g["총합"]>0, g["건수"]/g["총합"]*100, 0.0)
        heatmap(g, "지방의회_기수", "최종분야", "비율(%)", "기수별 분야 비율")
    else:
        heatmap(g, "지방의회_기수", "최종분야", "건수", "기수별 분야 건수")
    st.caption("각 기수에서 어떤 분야가 상대적으로 많았는지 색으로 표시합니다.")

elif mode == "광역×기초":
    st.markdown("**광역 × 기초 히트맵**")
    g = all_df.groupby(["광역","기초"]).size().reset_index(name="건수").sort_values("건수", ascending=False).head(topn*5)
    if as_ratio and not g.empty:
        g["총합"] = g.groupby("광역")["건수"].transform("sum")
        g["비율(%)"] = np.where(g["총합"]>0, g["건수"]/g["총합"]*100, 0.0)
        heatmap(g, "기초", "광역", "비율(%)", "광역별 기초 비율(Top)")
    else:
        heatmap(g, "기초", "광역", "건수", "광역별 기초 건수(Top)")
    st.caption("광역-기초 조합의 상대/절대 규모를 비교합니다.")

elif mode == "광역×분야×기수":
    st.markdown("**광역 × 분야 × 기수 히트맵** (Top 분야만)")
    g = all_df.groupby(["광역","최종분야","지방의회_기수"]).size().reset_index(name="건수")
    top_fields = g.groupby("최종분야")["건수"].sum().sort_values(ascending=False).head(topn).index.tolist()
    g = g[g["최종분야"].isin(top_fields)]
    if as_ratio and not g.empty:
        g["총합"] = g.groupby(["광역","지방의회_기수"])["건수"].transform("sum")
        g["비율(%)"] = np.where(g["총합"]>0, g["건수"]/g["총합"]*100, 0.0)
        heatmap(g, "지방의회_기수", "최종분야", "비율(%)", f"기수 대비 분야 비율 (Top {topn})")
    else:
        heatmap(g, "지방의회_기수", "최종분야", "건수", f"기수 대비 분야 건수 (Top {topn})")
    st.caption("기수별 분야 구성 변화를 확인합니다.")

elif mode == "위임조례 전용":
    st.markdown("**위임/자치 조례 전용 분석** — 사이드바의 ‘조례유형’에서 위임/자치를 선택해 보세요.")
    col1, col2 = st.columns(2)
    with col1:
        a = as_grouped(base_df, "최종분야", "기본 지역").sort_values("건수", ascending=False).head(topn)
        b = as_grouped(comp_df, "최종분야", "비교 지역").sort_values("건수", ascending=False).head(topn) if compare_on else None
        if as_ratio:
            if not a.empty: a = add_ratio(a, ["그룹"])
            if b is not None and not b.empty: b = add_ratio(b, ["그룹"])
        grouped_bar(a, b, "최종분야", "분야별 분포(위임/자치 선택 반영)")
    with col2:
        a2 = as_grouped(base_df, "지방의회_기수", "기본 지역")
        b2 = as_grouped(comp_df, "지방의회_기수", "비교 지역") if compare_on else None
        if as_ratio:
            if not a2.empty: a2 = add_ratio(a2, ["그룹"])
            if b2 is not None and not b2.empty: b2 = add_ratio(b2, ["그룹"])
        grouped_bar(a2, b2, "지방의회_기수", "기수별 분포(위임/자치 선택 반영)")
    st.caption("왼쪽 ‘조례유형’ 필터에서 위임조례 또는 자치조례만으로 좁혀 볼 수 있습니다.")

st.divider()

# -----------------------------
# (2) 피벗 / 교차표 (모드 연동)
# -----------------------------
st.subheader("피벗 / 교차표 (모드 연동)")

def pivot_download_button(pv: pd.DataFrame, default_name: str):
    if pv is None or pv.empty:
        st.info("표시할 데이터가 없습니다."); return
    st.dataframe(pv, use_container_width=True)
    st.download_button(
        "피벗(CSV) 다운로드",
        data=pv.to_csv().encode("utf-8-sig"),
        file_name=default_name,
        mime="text/csv"
    )

pv = None
if mode == "총괄 현황":
    pv = all_df.groupby("광역").size().to_frame("건수").sort_values("건수", ascending=False)
    if as_ratio and not pv.empty:
        pv["비율(%)"] = (pv["건수"]/pv["건수"].sum()*100)
    fn = make_filename("pivot", mode, as_ratio, type_choice)

elif mode == "지역×분야":
    mat = pd.crosstab(index=[all_df["광역"], all_df["기초"]], columns=all_df["최종분야"]).fillna(0).astype(int)
    if as_ratio and not mat.empty:
        row_sum = mat.sum(axis=1)
        mat = mat.div(row_sum.replace(0, np.nan), axis=0).fillna(0)*100
    row_order = mat.sum(axis=1).sort_values(ascending=False).head(topn*5).index
    col_order = mat.sum(axis=0).sort_values(ascending=False).index
    pv = mat.loc[row_order, col_order]
    fn = make_filename("pivot", mode, as_ratio, type_choice)

elif mode == "지역×기수":
    mat = pd.crosstab(index=[all_df["광역"], all_df["기초"]], columns=all_df["지방의회_기수"]).fillna(0).astype(int)
    if as_ratio and not mat.empty:
        row_sum = mat.sum(axis=1)
        mat = mat.div(row_sum.replace(0, np.nan), axis=0).fillna(0)*100
    row_order = mat.sum(axis=1).sort_values(ascending=False).head(topn*5).index
    pv = mat.loc[row_order]
    fn = make_filename("pivot", mode, as_ratio, type_choice)

elif mode == "기수×분야":
    mat = pd.crosstab(index=all_df["지방의회_기수"], columns=all_df["최종분야"]).fillna(0).astype(int)
    if as_ratio and not mat.empty:
        row_sum = mat.sum(axis=1)
        mat = mat.div(row_sum.replace(0, np.nan), axis=0).fillna(0)*100
    row_order = mat.sum(axis=1).sort_values(ascending=False).index
    col_order = mat.sum(axis=0).sort_values(ascending=False).index
    pv = mat.loc[row_order, col_order]
    fn = make_filename("pivot", mode, as_ratio, type_choice)

elif mode == "광역×기초":
    pv = all_df.groupby(["광역","기초"]).size().to_frame("건수").sort_values("건수", ascending=False)
    if as_ratio and not pv.empty:
        by_prov_sum = pv.groupby(level=0)["건수"].transform("sum")
        pv["비율(%)"] = np.where(by_prov_sum>0, pv["건수"]/by_prov_sum*100, 0.0)
    pv = pv.head(topn*5)
    fn = make_filename("pivot", mode, as_ratio, type_choice)

elif mode == "광역×분야×기수":
    mat = all_df.groupby(["광역","최종분야","지방의회_기수"]).size().reset_index(name="건수")
    top_fields = mat.groupby("최종분야")["건수"].sum().sort_values(ascending=False).head(topn).index.tolist()
    sub = mat[mat["최종분야"].isin(top_fields)]
    pivot_src = sub.groupby(["광역","최종분야"])["건수"].sum().unstack(fill_value=0)
    if as_ratio and not pivot_src.empty:
        row_sum = pivot_src.sum(axis=1)
        pivot_src = pivot_src.div(row_sum.replace(0, np.nan), axis=0).fillna(0)*100
    row_order = pivot_src.sum(axis=1).sort_values(ascending=False).head(topn*3).index
    col_order = pivot_src.sum(axis=0).sort_values(ascending=False).index
    pv = pivot_src.loc[row_order, col_order]
    fn = make_filename("pivot", mode, as_ratio, type_choice)

elif mode == "위임조례 전용":
    mat = pd.crosstab(index=[all_df["광역"], all_df["기초"]], columns=all_df["최종분야"]).fillna(0).astype(int)
    if as_ratio and not mat.empty:
        row_sum = mat.sum(axis=1)
        mat = mat.div(row_sum.replace(0, np.nan), axis=0).fillna(0)*100
    row_order = mat.sum(axis=1).sort_values(ascending=False).head(topn*5).index
    col_order = mat.sum(axis=0).sort_values(ascending=False).index
    pv = mat.loc[row_order, col_order]
    fn = make_filename("pivot", mode, as_ratio, type_choice)

pivot_download_button(pv, default_name=fn)

# -----------------------------
# (3) 공통 피벗
# -----------------------------
with st.expander("공통 피벗 (항상 동일 형식: index=(광역,기초) × columns=지방의회_기수)", expanded=False):
    if not all_df.empty:
        common = pd.crosstab(index=[all_df["광역"], all_df["기초"]],
                             columns=all_df["지방의회_기수"]).fillna(0).astype(int)
        top_idx = common.sum(axis=1).sort_values(ascending=False).head(topn*5).index
        st.dataframe(common.loc[top_idx], use_container_width=True)
        st.download_button(
            "공통 피벗(CSV) 다운로드",
            data=common.loc[top_idx].to_csv().encode("utf-8-sig"),
            file_name=make_filename("pivot_common", mode, as_ratio, type_choice),
            mime="text/csv"
        )
    else:
        st.info("현재 조건에 해당하는 데이터가 없습니다.")

st.divider()

# -----------------------------
# (4) 현재 조건의 조례 목록 (상위 500건)
# -----------------------------
st.subheader("현재 조건의 조례 목록(상위 500건)")
show_cols = [c for c in ["자치법규명","제개정일자","지방의회_기수","최종분야","조례유형","소관부서","광역","기초"] if c in df.columns]
if not all_df.empty and show_cols:
    sort_keys = [c for c in ["제개정일자","지방의회_기수"] if c in all_df.columns]
    cur = all_df.sort_values(by=sort_keys, ascending=False, na_position="last")
    st.dataframe(cur[show_cols].head(500), use_container_width=True)
    st.download_button(
        "현재 조건 CSV 다운로드",
        data=cur[show_cols].to_csv(index=False).encode("utf-8-sig"),
        file_name=make_filename("filtered_list", mode, as_ratio, type_choice),
        mime="text/csv"
    )
else:
    st.info("표시할 항목이 없습니다. 필터를 조정해 주세요.")
