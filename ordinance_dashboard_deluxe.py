# -*- coding: utf-8 -*-
# 생성: 2025-10-08 (KST)
# 파일명: ordinance_dashboard_deluxe_fixed.py
#
# 목적
# - 원본 CSV(korean_ordinance.csv)를 기반으로 4개 탭을 제공합니다.
#   1) 기수별 광역 분석: [지방의회_x기] 선택 → (행=광역, 열=분야) + 합계
#   2) 광역별 기수 변화: [광역] 선택 → (행=지방의회 기수, 열=분야) + 합계 + 평균 증가율(%)
#   3) 기초자치단체 현황: [광역] 선택 → (행=기초(광역 자체 포함), 열=분야) + 합계
#   4) 전국 기수별 분야 변화: (행=지방의회 기수, 열=분야) + 합계
#
# 핵심 규칙
# - "광역 자체"는 (기초 == 광역) 로 식별합니다. (사용자 제공 '기초 공백 제거본' 전제)
# - 탭2(광역별 기수 변화)는 광역 자체 + 해당 광역 소속 모든 기초의 조례를 합산합니다.
# - 과거/대체 명칭(예: 강원도→강원특별자치도)을 alias 로 포함하여 누락 방지.
#
# 사용법
# - 같은 폴더에 korean_ordinance.csv 를 두고 실행하세요.
# - 인코딩은 cp949 → utf-8-sig → utf-8 순으로 자동 시도합니다.

import io
from typing import List, Tuple

import pandas as pd
import streamlit as st

st.set_page_config(page_title="조례 통계 분석 대시보드 (Fixed)", layout="wide")

# ==============================
# Utilities
# ==============================
@st.cache_data(show_spinner=False)
def load_csv_with_encodings(path: str) -> pd.DataFrame:
    last_err = None
    for enc in ["cp949", "utf-8-sig", "utf-8"]:
        try:
            df = pd.read_csv(path, encoding=enc)
            st.caption(f"데이터 인코딩: **{enc}**")
            return df
        except Exception as e:
            last_err = e
    raise last_err


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # 필수 컬럼 존재 확인
    required = ["번호", "광역", "기초", "자치법규명", "제개정일자", "지방의회_기수", "최종분야"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"필수 컬럼 누락: {missing}")
        st.stop()

    # 문자열 정리
    for col in ["광역", "기초", "지방의회_기수", "최종분야"]:
        df[col] = df[col].astype(str).str.strip()

    # 광역 자체 여부 (기초 == 광역)
    df["광역자체"] = (df["기초"] == df["광역"])

    # 기수 정렬 키
    def gisu_key(x: str) -> int:
        try:
            if x.startswith("지방의회") and x.endswith("기"):
                n = x.replace("지방의회", "").replace("기", "").strip()
                return int(n)
        except Exception:
            pass
        return 999
    df["_기수정렬"] = df["지방의회_기수"].map(gisu_key)

    return df


# 과거/대체 명칭 매핑 (필요시 확장)
ALIAS = {
    "강원특별자치도": ["강원도"],
    "제주특별자치도": ["제주도"],
    # "세종특별자치시": ["세종시"],  # 필요 시 사용
}


ORDER_GISU = [f"지방의회 {i}기" for i in range(1, 10)]


def region_names(gwangyeok: str) -> List[str]:
    return [gwangyeok] + ALIAS.get(gwangyeok, [])


def make_download(name: str, df: pd.DataFrame):
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label=f"CSV 다운로드: {name}",
        data=csv,
        file_name=f"{name}.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ==============================
# Builders (표 생성)
# ==============================
def build_tab1_by_gisu(df: pd.DataFrame, gisu: str) -> pd.DataFrame:
    # (행=광역, 열=분야) + 합계
    use = df[df["지방의회_기수"] == gisu]
    pivot = use.pivot_table(index="광역", columns="최종분야", aggfunc="size", fill_value=0)
    pivot["합계"] = pivot.sum(axis=1)
    out = pivot.reset_index().sort_values("광역")
    return out


def build_tab2_by_region(df: pd.DataFrame, gwangyeok: str) -> Tuple[pd.DataFrame, float]:
    # 선택 광역 + alias 포함 필터 → 기수×분야 + 합계 + 평균증가율
    use = df[df["광역"].isin(region_names(gwangyeok))].copy()
    pivot = use.pivot_table(index="지방의회_기수", columns="최종분야", aggfunc="size", fill_value=0)
    pivot = pivot.reindex(ORDER_GISU, fill_value=0)
    pivot["합계"] = pivot.sum(axis=1)

    # 평균 증가율(%)
    s = pd.to_numeric(pivot["합계"], errors="coerce")
    growth = s.pct_change() * 100
    avg_growth = float(growth.iloc[1:].mean()) if len(growth) > 1 else 0.0

    out = pivot.reset_index()
    out.loc[len(out)] = ["평균 증가율(%)"] + [None]*(out.shape[1]-2) + [avg_growth]
    return out, avg_growth


def build_tab3_gicho(df: pd.DataFrame, gwangyeok: str) -> pd.DataFrame:
    # 같은 광역(별칭 포함)의 모든 행을 사용
    use = df[df["광역"].isin(region_names(gwangyeok))].copy()
    # (행=기초, 열=분야) + 합계  → 기초에는 (기초==광역)인 '광역 자체' 행도 포함됨
    pivot = use.pivot_table(index="기초", columns="최종분야", aggfunc="size", fill_value=0)
    pivot["합계"] = pivot.sum(axis=1)
    out = pivot.reset_index().sort_values("기초")
    return out


def build_tab4_national(df: pd.DataFrame) -> pd.DataFrame:
    # 전국 단위: (행=지방의회_기수, 열=분야) + 합계
    pivot = df.pivot_table(index="지방의회_기수", columns="최종분야", aggfunc="size", fill_value=0)
    # 정렬
    pivot = pivot.reset_index()
    def gisu_key(x: str) -> int:
        try:
            if str(x).startswith("지방의회") and str(x).endswith("기"):
                return int(str(x).replace("지방의회", "").replace("기", "").strip())
        except Exception:
            pass
        return 999
    pivot["_k"] = pivot["지방의회_기수"].map(gisu_key)
    pivot = pivot.sort_values("_k").drop(columns=["_k"])
    # 합계
    pivot["합계"] = pivot.drop(columns=["지방의회_기수"]).sum(axis=1)
    return pivot


# ==============================
# App Layout
# ==============================
st.title("지방자치단체 조례 통계 대시보드 (Fixed)")
st.caption("• 광역 자체 = (기초 == 광역) 규칙 적용 • 탭2는 광역 자체 + 소속 모든 기초 합산 • 평균 증가율 정상 계산")

with st.sidebar:
    st.header("데이터 로드")
    path = st.text_input("CSV 경로", value="korean_ordinance.csv")
    df_raw = load_csv_with_encodings(path)
    df = normalize(df_raw)
    st.write(f"- 행 수: **{len(df):,}**")
    st.write(f"- 광역 수(고유): **{df['광역'].nunique()}**")
    st.write(f"- 기초 수(고유): **{df['기초'].nunique()}**")
    st.divider()
    st.subheader("도움말")
    st.markdown("""
- **광역 자체 여부**는 (기초 == 광역)으로 판별합니다.
- **탭2**는 광역 이름과 과거명칭(예: 강원도)을 함께 포함해 누락을 방지합니다.
- 평균 증가율은 기수별 합계의 `pct_change()` 평균(1기 제외)입니다.
    """)

tab1, tab2, tab3, tab4 = st.tabs(["① 기수별 광역 분석", "② 광역별 기수 변화", "③ 기초자치단체 현황", "④ 전국 기수별 분야 변화"])

with tab1:
    st.subheader("① 기수별 광역 분석")
    gisu = st.selectbox("지방의회 기수 선택", ORDER_GISU, index=0)
    t1 = build_tab1_by_gisu(df, gisu)
    st.dataframe(t1, use_container_width=True, hide_index=True)
    make_download(f"기수별_광역분석_{gisu}", t1)

with tab2:
    st.subheader("② 광역별 기수 변화")
    gwang = st.selectbox("광역 선택", sorted(df["광역"].unique()), index=0)
    t2, avg = build_tab2_by_region(df, gwang)
    st.dataframe(t2, use_container_width=True, hide_index=True)
    st.info(f"**평균 증가율(%)**: {avg:.2f}")
    make_download(f"광역별_기수변화_{gwang}", t2)

with tab3:
    st.subheader("③ 기초자치단체 현황")
    gwang2 = st.selectbox("광역 선택(기초 표)", sorted(df["광역"].unique()), index=0, key="tab3")
    t3 = build_tab3_gicho(df, gwang2)
    st.dataframe(t3, use_container_width=True, hide_index=True)
    make_download(f"기초자치단체현황_{gwang2}", t3)

with tab4:
    st.subheader("④ 전국 기수별 분야 변화")
    t4 = build_tab4_national(df)
    st.dataframe(t4, use_container_width=True, hide_index=True)
    make_download("전국_기수별_분야변화", t4)
