"""
utils/pinecone_client.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【このファイルの役割】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EC商品の「梱包サイズ・重量の自動推定」を行うコアモジュールです。

以下の2つの外部サービスをラップしています。

① OpenAI API
    - Embeddings (text-embedding-3-small):
        商品名・カテゴリなどのテキストを 1536次元のベクトルに変換する。
        ベクトルが近い = 商品の特徴が似ている、という前提で類似検索に使う。
    - Chat Completions (gpt-4.1-mini):
        調べたい商品の情報（商品名・JANコード・メーカー・カテゴリ等）を指定し、
        梱包サイズ (cm) と梱包重量 (kg) を JSON 形式で推定させる。
        2通りの使い方がある:
        [RAGあり] 類似商品の実績サイズデータもプロンプトに含め、それを根拠に推定させる
        [RAGなし] 実績データなしで LLM の学習済み知識だけで推定させる（ベースライン）

② Pinecone (ベクトルDB)
    あらかじめ全商品の Embedding を格納しておき、
    クエリベクトルとのコサイン類似度でトップK件を高速に取り出す。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【処理の全体フロー（メイン入口: get_combined_estimate）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ユーザー入力（商品名・メーカー・カテゴリ等）
    │
    ▼
[1] build_query_text()
    入力フィールドをラベル付きテキストに整形
    例: "商品名: DD51 1000番台\nメーカー: KATO"
    │
    ▼
[2] embed_query()  ← OpenAI Embeddings API 呼び出し
    テキスト → 1536次元ベクトル
    │
    ▼
[3] search_similar()  ← Pinecone クエリ
    ベクトル類似検索でトップK件の類似商品を取得
    ・メーカー/カテゴリ/シリーズでメタデータフィルタをかけ精度向上
    ・ヒット件数が少なければフィルタを緩めてフォールバック
    │
    ├─────────────────────────────────────────┐
    ▼（並列実行）                              ▼（並列実行）
[4a] estimate_packaging()              [4b] estimate_without_rag()
    類似商品の実績データをプロンプトに渡す     商品情報だけで推定（実績データなし）
    ← OpenAI Chat API 呼び出し              ← OpenAI Chat API 呼び出し
    │                                        │
    └─────────────────┬───────────────────────┘
                        ▼
[5] 推奨判定（類似スコアに基づき RAG / LLM どちらを信頼するか決定）
                        │
                        ▼
                結果を返す（dict）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【公開関数一覧】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

build_query_text()        入力値をクエリ文字列に整形
embed_query()             テキストをベクトルに変換
search_similar()          Pinecone で類似商品を検索
estimate_packaging()      RAGあり: 類似商品実績データ + LLM で推定
estimate_without_rag()    RAGなし: LLM 単独で推定（ベースライン比較用）
get_combined_estimate()   上記を統合し、推奨判定付きで返す（メイン入口）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【修正履歴】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2026.4.14   search_similar() の返り値に size_type と package_* 列を追加
            estimate_packaging() のプロンプトに size_type の扱い方を追記
            (size_type="shipping" はそのまま参照、"package" は梱包材分10〜20%増で換算)
            estimate_without_rag() を新規追加 (RAGなし・LLMのみの推定)
            get_combined_estimate() を新規追加 (RAGあり・RAGなし両方を返し推奨を判定)
            推奨判定: 類似スコア≥0.85→RAG推奨、<0.70→LLM推奨、その間→RAG推奨
2026.4.16   カテゴリ2によるメタデータフィルタリングを追加
            推奨判定ロジックを改善:
            ・カテゴリフィルタ有効時は LLM閾値を 0.70→0.50 に緩和
            ・LLMは常に実績データなしのため、RAGにスコア≥0.40の類似商品があれば RAG を優先
            定数追加: RECOMMEND_LLM_THRESHOLD_FILTERED=0.50, MIN_SCORE_FOR_RAG=0.40
            category_2 が指定されている場合、同カテゴリ内だけで類似検索する
            フィルタ結果が MIN_FILTER_RESULTS 件未満の場合はフィルタなしにフォールバック
            (カテゴリに商品が少ない場合でも結果を返せるようにするため)
            search_similar() の返り値に filtered フラグを追加
            (フィルタが有効だったか否かをUIで確認できるようにするため)
2026.4.22   estimate_packaging() のプロンプト指示をスコア段階に応じて切り替えるよう変更
            score≥0.95: 最高スコア商品をそのまま採用（JANコード・商品名一致レベル）
            score 0.70〜0.95: 類似商品を参考にしつつ対象商品の特性で調整（形状・スケール考慮）
            score<0.70: 類似商品全体の傾向から総合推定
            TOP_K を 3 → 5 に変更（サイズ分布を広く取り推定精度を向上）
2026.4.18   コード重複を解消
            _OUTPUT_JSON_SCHEMA を定数として切り出し (RAGあり・なし共通のJSONスキーマ)
            _call_llm_for_estimate() を新規追加 (LLM呼び出し・レスポンスパース・dict返却を共通化)
            estimate_packaging() / estimate_without_rag() を _call_llm_for_estimate() を使うよう修正
            get_combined_estimate() で RAGあり・RAGなし推定を ThreadPoolExecutor で並列実行するよう変更
            (2つのLLM呼び出しが独立しているため、応答時間をほぼ半減できる)
            _to_float() の NaN チェックを math.isnan() を使う可読性の高い書き方に変更
            メーカーフィルタを追加し検索精度を向上
            search_similar() の返り値を bool → str に変更
            (適用フィルタ種別: "category+manufacturer" / "category" / "manufacturer" / "")
            フォールバック順: category+manufacturer → category → manufacturer → フィルタなし
            シリーズフィルタを追加
            フォールバック順: category+manufacturer+series → category+manufacturer → category → manufacturer → フィルタなし
"""

import json
import math
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
from openai import OpenAI
from pinecone import Pinecone

import config
from config import (
    OPENAI_CHAT_MODEL,
    PINECONE_INDEX_NAME,
)

# ── 定数 ─────────────────────────────────────────────────────────────────────
#
# 【推奨判定の閾値について】
#
# Pinecone の類似スコア（コサイン類似度）は 0〜1 の値を取る。
# スコアが高いほど「見つかった類似商品」が対象商品に近く、実績データを信頼できる。
#
#  スコア範囲                       判定
#  ─────────────────────────────────────────────────────────
#  score < MIN_SCORE_FOR_RAG        → LLM推奨（類似商品が遠すぎて参考にならない）
#  MIN_SCORE_FOR_RAG ≤ score < llm_threshold
#                                   → RAG推奨（LLMは実績データを持たないので RAG の方がまし）
#  llm_threshold ≤ score < RECOMMEND_RAG_THRESHOLD
#                                   → RAG推奨（中程度、実績参考）
#  score ≥ RECOMMEND_RAG_THRESHOLD  → RAG強く推奨（高精度マッチ）
#
# ※ カテゴリフィルタが有効な場合、同カテゴリ内でのヒットのため
#    llm_threshold を 0.70 → 0.50 に緩める（同カテゴリ内なら低スコアでも参考になりやすい）。

# 類似スコアがこれ以上 → RAG を強く推奨（実績データの信頼性が高い）
RECOMMEND_RAG_THRESHOLD = 0.85

# 類似スコアがこれ未満（フィルタなし時）→ LLM を推奨
RECOMMEND_LLM_THRESHOLD = 0.70

# 類似スコアがこれ未満（カテゴリフィルタあり時）→ LLM を推奨（同カテゴリ内なので閾値を緩める）
RECOMMEND_LLM_THRESHOLD_FILTERED = 0.50

# 類似スコアがこれ未満 → RAG の根拠として弱すぎるため LLM を推奨
MIN_SCORE_FOR_RAG = 0.40

# カテゴリフィルタ有効時に最低限確保したい検索ヒット件数。
# ヒット数がこれを下回る場合はフィルタを緩めて再検索する（カテゴリに商品が少ない場合の救済）。
MIN_FILTER_RESULTS = 3


# ── 初期化（アプリ起動時に1回だけ実行） ───────────────────────────────────────
#
# @st.cache_resource を付けることで、Streamlit アプリの全セッションで
# クライアントオブジェクトが使い回される。毎リクエストで new OpenAI() が
# 呼ばれるのを防ぎ、接続コストと API キーの再読み込みを抑える。

@st.cache_resource
def get_openai_client() -> OpenAI:
    """OpenAI クライアントを返す。API キーは st.secrets から取得。"""
    return OpenAI(api_key=st.secrets["openai"]["api_key"])

@st.cache_resource
def get_pinecone_index():
    """Pinecone Index オブジェクトを返す。接続は起動時に1回だけ確立される。"""
    pc = Pinecone(api_key=st.secrets["pinecone"]["api_key"])
    return pc.Index(PINECONE_INDEX_NAME)

# ── Embedding ────────────────────────────────────────────────────────────────
#
# 「意味的に似たテキスト = ベクトルが近い」という性質を利用して類似検索を行う。
# OpenAI の text-embedding-3-small は 1536次元のベクトルを返す。
# このベクトルを Pinecone に渡すと、事前に登録済みの全商品ベクトルと
# コサイン類似度を計算し、最も近い商品をトップK件返してくれる。

def embed_query(text: str) -> list[float]:
    """
    テキストを text-embedding-3-small で埋め込み、ベクトルを返す。

    Parameters
    ----------
    text : str
        埋め込み対象のテキスト（build_query_text() で生成したラベル付き文字列）。

    Returns
    -------
    list[float]
        1536 次元の浮動小数点数リスト。Pinecone のクエリベクトルとして使う。
    """
    client = get_openai_client()
    # OpenAI Embeddings API を呼び出してテキストをベクトルに変換する
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    # response.data はリスト形式。単一テキストなので [0] 番目だけ取り出す
    return response.data[0].embedding


# ── 検索クエリ文字列の組み立て ───────────────────────────────────────────────
#
# Pinecone に登録済みの商品ベクトルは、CSV の search_text 列から作られている。
# クエリ側も同じラベル・同じフォーマットで文字列を組み立てることで、
# 登録データとクエリのベクトル空間が揃い、類似度計算が正確になる。
# （フォーマットが違うと「同じ商品」でも類似スコアが下がる）

def build_query_text(
    product_name_ja: str = "",
    series: str = "",
    manufacturer: str = "",
    category_2: str = "",
    category_3: str = "",
) -> str:
    """
    入力フィールドの値から、埋め込み用クエリ文字列を組み立てる。
    hobby_rag.csv の search_text と同じフォーマット・同じラベルを使うこと。
    空欄フィールドはスキップ。

    JANコードは数字の羅列で意味を持たず類似検索のノイズになるため含めない。
    RAGなし推定では LLM に直接渡す（estimate_without_rag() の target_product を参照）。

    例:
        product_name_ja="DD51 1000番台 JR仕様", series="Nゲージ", manufacturer="KATO",
        category_2="Model Trains", category_3="Electric Locomotive"
        →
        商品名: DD51 1000番台 JR仕様
        シリーズ: Nゲージ
        メーカー: KATO
        カテゴリ2: Model Trains
        カテゴリ3: Electric Locomotive
    """
    lines = []
    # 入力された項目だけをラベル付きで追加。空欄はスキップして余分なラベルを入れない
    if product_name_ja.strip():
        lines.append(f"商品名: {product_name_ja.strip()}")
    if series.strip():
        lines.append(f"シリーズ: {series.strip()}")
    if manufacturer.strip():
        lines.append(f"メーカー: {manufacturer.strip()}")
    if category_2.strip():
        lines.append(f"カテゴリ2: {category_2.strip()}")
    if category_3.strip():
        lines.append(f"カテゴリ3: {category_3.strip()}")
    return "\n".join(lines)


# ── 類似検索 ─────────────────────────────────────────────────────────────────
#
# 【メタデータフィルタの使い方】
#
# Pinecone はベクトル類似度だけでなく、メタデータ（カテゴリ・メーカー等）での
# 絞り込みを同時に行える。例えば「KATOのNゲージ」に絞って検索すれば、
# 全商品から探すより精度が上がる。
#
# ただし、フィルタが厳しすぎるとヒット件数が極端に減る可能性があるため、
# 以下の順でフィルタを緩めながら MIN_FILTER_RESULTS 件以上になるまで再試行する。
#
#   category+manufacturer+series（最も絞り込み）
#     → category+manufacturer
#     → category のみ
#     → manufacturer のみ
#     → フィルタなし（最終フォールバック）

def _run_query(vector: list[float], top_k: int, pinecone_filter: dict | None) -> list:
    """Pinecone にクエリを1回投げてマッチリストを返す内部ヘルパー。"""
    index = get_pinecone_index()
    kwargs = dict(vector=vector, top_k=top_k, include_metadata=True)
    if pinecone_filter:
        # フィルタが指定された場合のみ filter パラメータを追加する
        kwargs["filter"] = pinecone_filter
    return index.query(**kwargs).matches


def _matches_to_dicts(matches: list) -> list[dict]:
    """
    Pinecone のマッチオブジェクトリストを、アプリで扱いやすい辞書リストに変換する。

    size_type の値によって参照すべきサイズカラムが異なる点に注意:
    "shipping" → shipping_* カラムが発送実績サイズ（そのまま参考にできる）
    "package"  → package_* カラムが製品パッケージサイズ（梱包材を足して10〜20%増で換算が必要）
    """
    results = []
    for match in matches:
        meta = match.metadata or {}
        results.append({
            "jan":             meta.get("jan", ""),
            "product_name_ja": meta.get("product_name_ja", ""),
            "series":          meta.get("series", ""),
            "manufacturer":    meta.get("manufacturer", ""),
            "category_2":      meta.get("category_2", ""),
            "category_3":      meta.get("category_3", ""),
            # size_type: "shipping"（発送実績）or "package"（製品パッケージ）
            "size_type":       meta.get("size_type", "shipping"),
            # 発送実績サイズ（size_type="shipping" の商品で有効）
            "shipping_length": _to_float(meta.get("shipping_length")),
            "shipping_width":  _to_float(meta.get("shipping_width")),
            "shipping_height": _to_float(meta.get("shipping_height")),
            "shipping_weight": _to_float(meta.get("shipping_weight")),
            # 製品パッケージサイズ（size_type="package" の商品で有効）
            "package_length":  _to_float(meta.get("package_length")),
            "package_width":   _to_float(meta.get("package_width")),
            "package_height":  _to_float(meta.get("package_height")),
            "package_weight":  _to_float(meta.get("package_weight")),
            # Pinecone が返したコサイン類似スコア（0〜1）
            "score":           match.score,
        })
    return results


def search_similar(
    product_name_ja: str = "",
    series: str = "",
    manufacturer: str = "",
    category_2: str = "",
    category_3: str = "",
    top_k: int = config.TOP_K,
) -> tuple[list[dict], str]:
    """
    Pinecone で類似商品を検索し、結果リストを返す。

    manufacturer / category_2 / series が指定された場合はメタデータフィルタ検索を行う。
    件数不足時のフォールバック順:
    category+manufacturer+series → category+manufacturer → category → manufacturer → フィルタなし

    JANコードはベクトル化せず類似検索には使わない（数字の羅列は意味を持たずノイズになるため）。

    Returns
    -------
    tuple[list[dict], str]
        - list[dict]: 各要素は類似商品の情報
        - str: 実際に適用されたフィルタ種別
            "category+manufacturer+series" / "category+manufacturer" / "category" / "manufacturer" / ""
    """
    # クエリ文字列を組み立てる。何も入力されていなければ検索不要
    query_text = build_query_text(product_name_ja, series, manufacturer, category_2, category_3)
    if not query_text:
        return [], ""

    # クエリテキストをベクトルに変換（OpenAI Embeddings API 呼び出し）
    vector = embed_query(query_text)
    c2 = category_2.strip()
    mf = manufacturer.strip()
    sr = series.strip()

    # フォールバック順に試すフィルタ候補を組み立てる（厳しい順に並べる）
    candidates: list[tuple[str, dict | None]] = []
    if c2 and mf and sr:
        # 最も絞り込み: カテゴリ + メーカー + シリーズが全て一致する商品に限定
        candidates.append(("category+manufacturer+series", {"$and": [
            {"category_2":   {"$eq": c2}},
            {"manufacturer": {"$eq": mf}},
            {"series":       {"$eq": sr}},
        ]}))
    if c2 and mf:
        # カテゴリ + メーカーが一致する商品に限定
        candidates.append(("category+manufacturer", {"$and": [
            {"category_2":   {"$eq": c2}},
            {"manufacturer": {"$eq": mf}},
        ]}))
    if c2:
        # カテゴリのみで絞り込み
        candidates.append(("category", {"category_2": {"$eq": c2}}))
    if mf:
        # メーカーのみで絞り込み
        candidates.append(("manufacturer", {"manufacturer": {"$eq": mf}}))
    # フィルタなし（最終フォールバック。必ず何らかの結果が返る）
    candidates.append(("", None))

    # 上から順に試して、MIN_FILTER_RESULTS 件以上得られたフィルタを採用する
    for filter_label, pinecone_filter in candidates:
        matches = _run_query(vector, top_k, pinecone_filter)
        if len(matches) >= MIN_FILTER_RESULTS or filter_label == "":
            return _matches_to_dicts(matches), filter_label

    return [], ""


# ── LLM呼び出し共通ヘルパー ──────────────────────────────────────────────────
#
# estimate_packaging()（RAGあり）と estimate_without_rag()（RAGなし）は
# どちらも同じ流れで LLM を呼び出す:
#   1. system / user メッセージを組み立てる
#   2. OpenAI Chat API を呼び出す
#   3. JSON レスポンスをパースして dict を返す
#
# この共通部分を _call_llm_for_estimate() に切り出すことで重複を排除している。

# LLM に「この形式で JSON を返して」と指示するためのスキーマ定義（RAGあり・なし共通）
_OUTPUT_JSON_SCHEMA = {
    "shipping_length": "number | null  # 推定梱包 縦 (cm)",
    "shipping_width":  "number | null  # 推定梱包 横 (cm)",
    "shipping_height": "number | null  # 推定梱包 高さ (cm)",
    "shipping_weight": "number | null  # 推定梱包重量 (kg)",
    "confidence":      "integer 0-100  # 推定の信頼度",
    "reason":          "string         # 推定根拠の説明（日本語）",
}


def _call_llm_for_estimate(system_content: str, prompt_payload: dict) -> dict:
    """
    LLMを呼び出して梱包サイズ推定結果を返す共通ヘルパー。

    Parameters
    ----------
    system_content : str
        システムプロンプト（LLM の役割を定義する）。
    prompt_payload : dict
        ユーザーターンに渡すペイロード（JSON化して送信）。
        類似商品データや推定指示が含まれる。

    Returns
    -------
    dict : {
        "shipping_length": float | None,
        "shipping_width":  float | None,
        "shipping_height": float | None,
        "shipping_weight": float | None,
        "confidence":      int | None,
        "reason":          str,
    }
    """
    client = get_openai_client()

    # OpenAI Chat Completions API を呼び出す
    # temperature=0.2: 低めにして推定結果の安定性を高める（0に近いほど同じ入力→同じ出力）
    # max_tokens=500: JSON レスポンスは短いので制限を設けてコストを抑える
    response = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_content},
            # ペイロード（類似商品データ・指示）を JSON 文字列としてユーザーターンに渡す
            {"role": "user",   "content": json.dumps(prompt_payload, ensure_ascii=False)},
        ],
        temperature=0.2,
        max_tokens=500,
    )

    # LLM の返答テキストを取り出す（空文字列の場合も安全に処理）
    text   = (response.choices[0].message.content or "").strip()
    # テキストから JSON をパース（コードブロックが含まれていても対応）
    parsed = _safe_parse_json(text)

    # 数値フィールドは型変換して返す（LLM が文字列や null で返すケースに対応）
    return {
        "shipping_length": _to_float(parsed.get("shipping_length")),
        "shipping_width":  _to_float(parsed.get("shipping_width")),
        "shipping_height": _to_float(parsed.get("shipping_height")),
        "shipping_weight": _to_float(parsed.get("shipping_weight")),
        "confidence":      _to_int(parsed.get("confidence")),
        "reason":          str(parsed.get("reason", "")),
    }


# ── LLMによる梱包サイズ推定（RAGあり） ───────────────────────────────────────
#
# 「RAGあり推定」= Pinecone で取得した類似商品の実績サイズデータをプロンプトに埋め込み、
# そのデータを根拠として LLM に推定させる手法。
# LLM 単体ではなく実績データを参照するため、精度が高くなりやすい。

def estimate_packaging(
    similar_items: list[dict],
    product_name_ja: str = "",
    series: str = "",
    manufacturer: str = "",
    category_2: str = "",
    category_3: str = "",
) -> dict:
    """
    類似商品の実績データをLLMに渡し、梱包サイズ・重量を推定する（RAGあり）。

    similar_items が空の場合は推定不可として None を返す。

    Returns
    -------
    dict : _call_llm_for_estimate() と同じ構造
    """
    # 類似商品が見つからなかった場合は LLM を呼ばずに即返却
    if not similar_items:
        return {
            "shipping_length": None,
            "shipping_width":  None,
            "shipping_height": None,
            "shipping_weight": None,
            "confidence":      None,
            "reason":          "類似データが見つからなかったため推定できませんでした。",
        }

    # 最高類似スコアを取得（推定指示の切り替えに使う）
    top_score = similar_items[0].get("score", 0) if similar_items else 0

    # スコアに応じた推定指示を選択
    # ・スコアが高いほど最高スコア商品を直接信頼してよい
    # ・スコアが低いほど類似商品全体の傾向から総合的に推定する
    # 0.95以上: JANコードや商品名が一致に近い高精度マッチ → そのまま採用
    # 0.70〜0.95: 同カテゴリの別商品レベル → ベースにして微調整
    # 0.70未満: 遠い類似 → 全体傾向から推定
    if top_score >= 0.95:
        score_instruction = (
            "最も similarity_score が高い商品のサイズをそのまま採用してください。"
            "他の類似商品と値が異なっても変更しないでください。"
        )
    elif top_score >= 0.70:
        score_instruction = (
            "類似商品を参考にしつつ、対象商品の商品名・スケール・タイプを考慮して推定してください。"
            "類似商品と形状・スケールが異なると判断した場合は、類似商品の値に引きずられず"
            "対象商品に適したサイズに調整してください。"
        )
    else:
        score_instruction = (
            "類似スコアが低めです。類似商品全体の傾向・平均から総合的に推定してください。"
            "個々の商品に引きずられず、カテゴリの典型的なサイズを重視してください。"
        )

    # LLM に渡すペイロードを組み立てる
    prompt_payload = {
        # 推定対象の商品情報
        "user_query": {
            "product_name_ja": product_name_ja,
            "series":          series,
            "manufacturer":    manufacturer,
            "category_2":      category_2,
            "category_3":      category_3,
        },
        # Pinecone から取得した類似商品の実績データ一覧
        "similar_items": [
            {
                "jan":              item.get("jan", ""),
                "product_name_ja":  item.get("product_name_ja", ""),
                "series":           item.get("series", ""),
                "manufacturer":     item.get("manufacturer", ""),
                "category_2":       item.get("category_2", ""),
                "category_3":       item.get("category_3", ""),
                "size_type":        item.get("size_type", "shipping"),
                "shipping_length":  item.get("shipping_length"),
                "shipping_width":   item.get("shipping_width"),
                "shipping_height":  item.get("shipping_height"),
                "shipping_weight":  item.get("shipping_weight"),
                "package_length":   item.get("package_length"),
                "package_width":    item.get("package_width"),
                "package_height":   item.get("package_height"),
                "package_weight":   item.get("package_weight"),
                # similarity_score が高いほど対象商品に近い商品
                "similarity_score": round(item.get("score", 0), 3),
            }
            for item in similar_items
        ],
        # LLM への推定指示（日本語でルールを明示する）
        "instructions": [
            "あなたはEC商品の梱包サイズ推定アシスタントです。",
            "与えられた類似商品データだけを根拠にして、対象商品の発送時の梱包サイズ(cm)と梱包重量(kg)を推定してください。",
            "shipping_length / shipping_width / shipping_height の単位はcm、shipping_weight の単位はkgです。",
            "size_type が 'shipping' の商品は発送実績サイズなのでそのまま参考にしてください。",
            "size_type が 'package' の商品は製品パッケージサイズです。梱包材・外箱を考慮して10〜20%大きめに換算して参考にしてください。",
            score_instruction,
            "返答はJSONのみで返してください。余分なテキストは不要です。",
        ],
        # 出力 JSON の形式を LLM に伝える
        "output_json_schema": _OUTPUT_JSON_SCHEMA,
    }

    return _call_llm_for_estimate(
        system_content="あなたはEC物流の専門家です。類似商品の梱包実績データをもとに、新商品の梱包サイズを推定します。",
        prompt_payload=prompt_payload,
    )


# ── LLMによる梱包サイズ推定（RAGなし） ───────────────────────────────────────
#
# 「RAGなし推定」= 実績データを一切使わず、LLM が学習済み知識だけで推定するベースライン。
# RAGあり推定と比較することで「実績データを使う効果」を定量的に評価できる。
# 一般的に、実績データのない LLM は不確実性が高く confidence も低めになる。

def estimate_without_rag(
    product_name_ja: str = "",
    series: str = "",
    manufacturer: str = "",
    category_2: str = "",
    category_3: str = "",
    jan: str = "",
) -> dict:
    """
    類似商品データを使わず、LLMの学習済み知識だけで梱包サイズを推定する（RAGなし）。
    RAGありと比較するためのベースライン。

    Returns
    -------
    dict : _call_llm_for_estimate() と同じ構造
    """
    # 実績データは渡さず、商品情報だけをペイロードに入れる
    prompt_payload = {
        "target_product": {
            "jan":             jan,
            "product_name_ja": product_name_ja,
            "series":          series,
            "manufacturer":    manufacturer,
            "category_2":      category_2,
            "category_3":      category_3,
        },
        "instructions": [
            "あなたはEC商品の梱包サイズ推定アシスタントです。",
            "商品情報だけを頼りに、発送時の梱包サイズ(cm)と梱包重量(kg)を推定してください。",
            "shipping_length / shipping_width / shipping_height の単位はcm、shipping_weight の単位はkgです。",
            "過小見積もりは避け、保守的に推定してください。",
            "返答はJSONのみで返してください。余分なテキストは不要です。",
        ],
        "output_json_schema": _OUTPUT_JSON_SCHEMA,
    }

    return _call_llm_for_estimate(
        system_content="あなたはEC物流の専門家です。商品情報から梱包サイズを推定します。",
        prompt_payload=prompt_payload,
    )


# ── RAGあり・RAGなし統合推定 ─────────────────────────────────────────────────
#
# このファイルのメイン入口。UI からはこの関数だけ呼べばよい。
# 類似検索 → 並列 LLM 呼び出し → 推奨判定 の全工程をまとめて実行する。

def get_combined_estimate(
    product_name_ja: str = "",
    series: str = "",
    manufacturer: str = "",
    category_2: str = "",
    category_3: str = "",
    jan: str = "",
) -> dict:
    """
    RAGあり推定と RAGなし推定の両方を実行し、推奨を判定して返す。

    Returns
    -------
    dict : {
        "similar_items":    list[dict],  # Pinecone 検索結果
        "top_score":        float,       # 最高類似スコア
        "filtered":         str,         # 適用されたフィルタ種別 ("category+manufacturer" / "category" / "manufacturer" / "")
        "rag":              dict,        # RAGあり推定結果
        "llm":              dict,        # RAGなし推定結果
        "recommended":      str,         # "rag" or "llm"
        "recommend_reason": str,         # 推奨理由
    }
    """
    # ── [1] 類似検索（Pinecone） ───────────────────────────────────────────────
    # JANコードは類似検索に使わない（数字の羅列はベクトル空間でノイズになるため）
    # config.TOP_K を毎回参照することで、config.py 変更時に再起動不要で反映される
    similar_items, filtered = search_similar(
        product_name_ja=product_name_ja,
        series=series,
        manufacturer=manufacturer,
        category_2=category_2,
        category_3=category_3,
        top_k=config.TOP_K,
    )
    # 類似商品がなければ top_score=0 として以降の処理を続ける
    top_score = similar_items[0]["score"] if similar_items else 0.0

    # ── [2] RAGあり・RAGなし推定を並列実行（OpenAI Chat API × 2回） ───────────
    # 2つの LLM 呼び出しは互いに独立しているため ThreadPoolExecutor で同時実行する。
    # 直列実行と比べて応答時間をほぼ半減できる。
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_rag = executor.submit(
            estimate_packaging,
            similar_items=similar_items,
            product_name_ja=product_name_ja,
            series=series,
            manufacturer=manufacturer,
            category_2=category_2,
            category_3=category_3,
        )
        future_llm = executor.submit(
            estimate_without_rag,
            product_name_ja=product_name_ja,
            series=series,
            manufacturer=manufacturer,
            category_2=category_2,
            category_3=category_3,
            jan=jan,
        )
        # 両方の結果が揃うまで待機
        rag = future_rag.result()
        llm = future_llm.result()

    # ── [3] 推奨判定 ───────────────────────────────────────────────────────────
    # カテゴリフィルタ有効時は同カテゴリ内ヒットなので LLM 閾値を緩める
    llm_threshold = RECOMMEND_LLM_THRESHOLD_FILTERED if filtered else RECOMMEND_LLM_THRESHOLD

    if not similar_items or top_score < MIN_SCORE_FOR_RAG:
        # 類似商品がゼロ、またはスコアが低すぎて実績データが参考にならない
        recommended      = "llm"
        recommend_reason = (
            "類似商品が見つからなかったため、LLMのみ推定を表示しています。"
            if not similar_items else
            f"類似スコア {top_score:.3f} が低すぎるため、実績データの参考度が低いとみなしLLMのみ推定を推奨します。"
        )
    elif top_score >= RECOMMEND_RAG_THRESHOLD:
        # 高精度マッチ: 実績データを強く信頼できる
        recommended      = "rag"
        recommend_reason = f"類似スコア {top_score:.3f} が高く、実績データの信頼性が高いためRAGあり推定を推奨します。"
    elif top_score >= llm_threshold:
        # 中程度のスコア: LLM より実績データの方が根拠があるため RAG を推奨
        recommended      = "rag"
        recommend_reason = (
            f"同カテゴリ内で類似スコア {top_score:.3f} の商品が見つかりました。"
            f"LLMは実績データを持たないため、RAGあり推定を推奨します。"
            if filtered else
            f"類似スコア {top_score:.3f} は中程度です。実績データを参考にしたRAGあり推定を推奨します。"
        )
    else:
        # MIN_SCORE_FOR_RAG ≤ score < llm_threshold
        # スコアはやや低いが、LLM は実績データを一切持たないため RAG の方が根拠がある
        recommended      = "rag"
        recommend_reason = (
            f"類似スコア {top_score:.3f} はやや低いですが、LLMは実績データを持ちません。"
            f"実績データを参照したRAGあり推定を推奨します（参考程度にご確認ください）。"
        )

    return {
        "similar_items":    similar_items,
        "top_score":        top_score,
        "filtered":         filtered,
        "rag":              rag,
        "llm":              llm,
        "recommended":      recommended,
        "recommend_reason": recommend_reason,
    }


# ── ユーティリティ ────────────────────────────────────────────────────────────
#
# Pinecone のメタデータや LLM の返答は文字列・None・NaN が混在するため、
# 型変換を安全に行うヘルパーをまとめている。

def _to_float(value) -> float | None:
    """
    文字列・int・None を float に変換する。変換失敗時・NaN 時は None を返す。
    Pinecone メタデータは文字列で入ることがあるため必ずこの関数を通す。
    """
    if value is None:
        return None
    try:
        result = float(value)
        # float("nan") は変換自体は成功するが数値として使えないため None に変換
        return None if math.isnan(result) else result
    except (ValueError, TypeError):
        return None


def _to_int(value) -> int | None:
    """
    文字列・float・None を int に変換する。変換失敗時は None を返す。
    LLM が confidence を "85" のような文字列で返す場合に対応。
    """
    if value is None:
        return None
    try:
        # float 経由にすることで "85.0" のような文字列も正しく変換できる
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _safe_parse_json(text: str) -> dict:
    """
    LLM の返答テキストから JSON を抽出してパースする。

    LLM が「```json\n{...}\n```」のようにコードブロックを付けて返した場合でも、
    { ... } の部分だけを切り出して再試行することで対応する。
    パースに失敗した場合は空の dict を返す（呼び出し元で None チェック不要にするため）。
    """
    try:
        # 通常ケース: テキスト全体がそのまま JSON の場合
        return json.loads(text)
    except json.JSONDecodeError:
        # LLM がコードブロックや余分なテキストを付けた場合: { } の範囲だけ切り出して再試行
        start = text.find("{")
        end   = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    # パース不能な場合は空 dict を返す（呼び出し元では .get() で安全にアクセスできる）
    return {}
