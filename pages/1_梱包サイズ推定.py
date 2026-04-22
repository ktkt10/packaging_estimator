"""
1_梱包サイズ推定.py
過去の梱包実績データ（Pinecone）を使って類似商品を検索し、
RAGあり・RAGなし両方の梱包サイズ推定結果を表示するページ
"""

import sys
import os

import pandas as pd
import streamlit as st

# プロジェクトルートをパスに追加
for _p in [os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from utils.auth import require_login, logout
from utils.pinecone_client import get_combined_estimate
from config import MANUFACTURERS, CATEGORY_2_OPTIONS, CATEGORY_3_OPTIONS, MANUFACTURER_CATEGORY_MAP, SERIES_MAP

st.set_page_config(page_title="梱包サイズ推定", page_icon="📦", layout="wide")
require_login()


# ── 表示ヘルパー ──────────────────────────────────────────────────────────────

def _fmt(val) -> str:
    """数値を文字列に変換する。None の場合は "—" を返す。"""
    return str(val) if val is not None else "—"


def _show_metrics(result: dict):
    """推定結果をmarkdownテーブルで表示する。"""
    st.markdown(
        f"| 縦 (cm) | 横 (cm) | 高さ (cm) | 重量 (kg) | 信頼度 (%) |\n"
        f"|:---:|:---:|:---:|:---:|:---:|\n"
        f"| **{_fmt(result.get('shipping_length'))}** "
        f"| **{_fmt(result.get('shipping_width'))}** "
        f"| **{_fmt(result.get('shipping_height'))}** "
        f"| **{_fmt(result.get('shipping_weight'))}** "
        f"| **{_fmt(result.get('confidence'))}** |"
    )

with st.sidebar:
    st.write(f"👤 {st.session_state.get('username', '')}")
    if st.button("ログアウト"):
        logout()
        st.switch_page("Home.py")

# ── セッション状態の初期化 ─────────────────────────────────────────────────────
if "ps_combined" not in st.session_state:
    st.session_state.ps_combined = None
if "ps_error" not in st.session_state:
    st.session_state.ps_error    = None

# ── メイン ────────────────────────────────────────────────────────────────────

st.header("📦 梱包サイズ推定")
st.caption("過去の梱包実績データをもとに類似商品を検索し、RAGあり・RAGなし両方の推定結果を表示します")
st.markdown("---")

# ── 入力フォーム ──────────────────────────────────────────────────────────────
st.info("📝 3項目以上を入力してください  \n入力項目が多いほど検索精度が上がります")

col1, col2 = st.columns(2)

with col1:
    jan_input = st.text_input(
        "JANコード",
        placeholder="例: 4950344603138",
        key="ps_jan",
    )
    product_name_ja_input = st.text_input(
        "商品名（日本語）",
        placeholder="例: グラマン F-14A トムキャット ブラックナイツ",
        key="ps_product_name_ja",
    )
    manufacturer_input = st.selectbox(
        "メーカー",
        options=["", "不明"] + MANUFACTURERS[1:],
        key="ps_manufacturer",
    )

with col2:
    # メーカー選択済み（「不明」含む）のときカテゴリ・シリーズを有効化
    mfr_selected = manufacturer_input.strip() != ""
    cat_enabled  = mfr_selected

    if mfr_selected and manufacturer_input in MANUFACTURER_CATEGORY_MAP:
        available_categories = [""] + MANUFACTURER_CATEGORY_MAP[manufacturer_input]
    else:
        available_categories = CATEGORY_2_OPTIONS

    category_2_input = st.selectbox(
        "カテゴリ",
        options=available_categories,
        key="ps_category_2",
        disabled=not cat_enabled,
        help=None if cat_enabled else "先にメーカーを選択してください",
    )
    category_3_input = st.selectbox(
        "サブカテゴリ",
        options=CATEGORY_3_OPTIONS.get(category_2_input, [""]),
        key="ps_category_3",
        disabled=not cat_enabled,
        help=None if cat_enabled else "先にメーカーを選択してください",
    )

    # メーカー＋カテゴリが確定したらシリーズを選択肢で表示
    available_series = [""]
    if mfr_selected and category_2_input.strip():
        available_series = [""] + SERIES_MAP.get(manufacturer_input, {}).get(category_2_input, [])

    series_enabled = cat_enabled and category_2_input.strip() != ""
    series_input = st.selectbox(
        "シリーズ",
        options=available_series,
        key="ps_series",
        disabled=not series_enabled,
        help=None if series_enabled else "先にカテゴリを選択してください",
    )

# ── 検索ボタン ────────────────────────────────────────────────────────────────
search_clicked = st.button("🔍 梱包サイズを調べる", type="primary")

if search_clicked:
    filled_count = sum(bool(v.strip()) for v in [
        jan_input,
        product_name_ja_input,
        "" if manufacturer_input == "不明" else manufacturer_input,
        category_2_input,
        category_3_input,
        series_input,
    ])
    if filled_count < 3:
        st.session_state.ps_error    = "JANコード・商品名・メーカー・カテゴリ・サブカテゴリ・シリーズのうち3項目以上を入力してください。"
        st.session_state.ps_combined = None
    else:
        st.session_state.ps_error = None
        with st.spinner("類似商品を検索中・AIが推定中..."):
            try:
                # 「不明」はフィルタ・クエリに使わないため空文字に正規化
                mfr_for_search = "" if manufacturer_input == "不明" else manufacturer_input
                combined = get_combined_estimate(
                    product_name_ja=product_name_ja_input,
                    series=series_input,
                    manufacturer=mfr_for_search,
                    category_2=category_2_input,
                    category_3=category_3_input,
                    jan=jan_input,
                )
                st.session_state.ps_combined = combined
            except Exception as e:
                st.session_state.ps_error    = f"エラーが発生しました: {e}"
                st.session_state.ps_combined = None

# エラー表示
if st.session_state.ps_error:
    st.error(st.session_state.ps_error)

# ── 結果表示 ──────────────────────────────────────────────────────────────────
if st.session_state.ps_combined is not None:
    combined         = st.session_state.ps_combined
    rag              = combined["rag"]
    llm              = combined["llm"]
    similar_items    = combined["similar_items"]
    top_score        = combined["top_score"]
    filtered         = combined.get("filtered", False)
    recommended      = combined["recommended"]
    recommend_reason = combined["recommend_reason"]

    st.markdown("---")

    # ── フィルタ状態の表示 ────────────────────────────────────────────────────
    if filtered == "category+manufacturer+series":
        st.caption(f"🔍 カテゴリ「{category_2_input}」× メーカー「{manufacturer_input}」× シリーズ「{series_input}」でフィルタ検索しました")
    elif filtered == "category+manufacturer":
        if series_input.strip():
            st.caption(f"⚠️ シリーズ「{series_input}」の件数が少ないため、カテゴリ「{category_2_input}」× メーカー「{manufacturer_input}」で検索しました")
        else:
            st.caption(f"🔍 カテゴリ「{category_2_input}」× メーカー「{manufacturer_input}」でフィルタ検索しました")
    elif filtered == "category":
        if manufacturer_input.strip():
            st.caption(f"⚠️ カテゴリ「{category_2_input}」× メーカー「{manufacturer_input}」の件数が少ないため、カテゴリのみで検索しました")
        else:
            st.caption(f"🔍 カテゴリ「{category_2_input}」内でフィルタ検索しました")
    elif filtered == "manufacturer":
        st.caption(f"⚠️ カテゴリフィルタの件数が少ないため、メーカー「{manufacturer_input}」のみで検索しました")
    elif category_2_input.strip() or manufacturer_input.strip():
        st.caption("⚠️ 指定条件の件数が少ないため、全カテゴリ・全メーカーから検索しました")

    # ── 推奨バナー ────────────────────────────────────────────────────────────
    if recommended == "rag":
        st.success(f"★ **RAGあり推定を推奨** — {recommend_reason}")
    else:
        st.warning(f"★ **LLMのみ推定を推奨** — {recommend_reason}")

    # ── RAGあり・RAGなし 比較表示 ─────────────────────────────────────────────
    st.subheader("📐 推定梱包サイズ")

    col_rag, col_llm = st.columns(2)

    with col_rag:
        if recommended == "rag":
            st.markdown(
                '#### 📊 RAGあり（実績データ参照）&nbsp;'
                '<span style="background:#28a745;color:white;padding:2px 10px;'
                'border-radius:12px;font-size:0.8em;font-weight:bold;">★ 推奨</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown("#### 📊 RAGあり（実績データ参照）")
        _show_metrics(rag)
        st.caption(f"類似スコア（最高）: {top_score:.3f}")
        reason = rag.get("reason", "")
        if reason:
            st.info(f"💡 {reason}")

    with col_llm:
        if recommended == "llm":
            st.markdown(
                '#### 🤖 LLMのみ（AI知識）&nbsp;'
                '<span style="background:#28a745;color:white;padding:2px 10px;'
                'border-radius:12px;font-size:0.8em;font-weight:bold;">★ 推奨</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown("#### 🤖 LLMのみ（AI知識）")
        _show_metrics(llm)
        st.caption("類似スコア: なし（実績データ不使用）")
        reason = llm.get("reason", "")
        if reason:
            st.info(f"💡 {reason}")

    st.caption("※ いずれもAIによる参考値です。実際の梱包時にご確認ください。")

    # ── 類似商品一覧 ──────────────────────────────────────────────────────────
    st.markdown("---")
    if not similar_items:
        st.warning("類似商品が見つかりませんでした。")
    else:
        st.subheader(f"🔎 参考にした類似商品 ({len(similar_items)} 件)")
