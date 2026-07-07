# -*- coding: utf-8 -*-
"""
次世代型 モール別AI対策＆SEO最適化ツール Pro
================================================
改善ポイント（原版からの差分）
- Amazonタイトル生成を追加（原版は欠落）
- 箇条書きテーマを事前定義（原版は「テーマ名」が丸投げ）
- Rufus想定Q&Aを構造化出力に含める
- 楽天キャッチコピーの127文字ハード上限を可視化
- SEOキーワード展開戦略をSystem Instructionに明記
- モデル名を現行推奨に更新（gemini-2.5-pro を既定に）
- JSON解析失敗時のリトライ＆コードフェンス除去
- 文字数バッジを全項目に付与、AIに自己申告目標も出させて検証
- 入力必須項目のバリデーション強化
- トーン選択を System Instruction 本文にマッピング
"""

import streamlit as st
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import List
import json
import re
import time

# =========================================================================
# ページ設定
# =========================================================================
st.set_page_config(
    page_title="次世代型 モール別AI対策＆SEO最適化ツール Pro",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================================
# 定数：文字数目標（AI生成結果を検証するための基準）
# =========================================================================
AMAZON_TITLE_TARGET = (50, 75)       # Amazon 2026仕様変更：75文字ハード上限
AMAZON_TITLE_HARD_MAX = 75
AMAZON_BULLET_TARGET = (80, 120)     # テーマラベル【】部分を除いた本文の目安
AMAZON_DESC_TARGET = (500, 800)
AMAZON_HIGHLIGHT_KW_TARGET = (7, 15)  # 商品のハイライト：カンマ区切りキーワード数
RAKUTEN_CATCH_TARGET = (60, 120)
RAKUTEN_CATCH_HARD_MAX = 127         # スマホ表示ハード上限（超過で見切れ）
RAKUTEN_TEXT_TARGET = (300, 600)

# 推奨モデル（現行）
AVAILABLE_MODELS = [
    "gemini-2.5-pro",        # 品質最優先（推奨）
    "gemini-2.5-flash",      # 速度・コスト重視
    "gemini-2.0-flash",      # 互換用
    "gemini-1.5-pro",        # レガシー
    "gemini-1.5-flash",      # レガシー
]

# Amazon箇条書きの推奨テーマ枠（5本を必ずここから選ばせる）
AMAZON_BULLET_THEMES = [
    "主要ベネフィット",
    "独自技術・素材",
    "使用シーン・対象者",
    "品質・安全性・保証",
    "使い方・お手入れ",
    "サイズ・スペック",
    "安全上の注意（誠実開示）",
]

# トーン → 実装ルール
TONE_MAPPING = {
    "誠実・信頼（推奨・SEO効果高）": (
        "語尾は『〜設計しています』『〜の理由は』『〜という構造です』など根拠提示型。"
        "断定は事実ベースのみ。感情的な煽り表現は使わない。"
    ),
    "情熱的・売込重視": (
        "語尾は『〜を叶えます』『〜のお悩みに』『〜を実感』など感情喚起型。"
        "ただし薬機法・景表法違反は絶対に避ける。"
    ),
    "簡潔・ロジカル": (
        "体言止めと事実の列挙を多用。装飾語を排し、数値・仕様中心に構成。"
    ),
}

# =========================================================================
# CSS
# =========================================================================
def _inject_custom_style():
    st.markdown(
        """
    <style>
      html, body, [data-testid="stAppViewContainer"] { background-color: #f8fafc; }
      [data-testid="stSidebar"] { background-color: #0f172a !important; }
      [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] .stMarkdown p,
      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #ffffff !important; font-weight: 600 !important;
      }
      [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea,
      [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1e293b !important; color: #ffffff !important;
        border: 1px solid #334155 !important;
      }
      [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] span { color: #ffffff !important; }
      textarea { color: #0f172a !important; background-color: #f8fafc !important; border: 1px solid #cbd5e1 !important; }
      div.stButton > button:first-child {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important; border: none !important; border-radius: 8px !important;
        font-weight: bold !important; height: 3.2em !important; width: 100% !important;
      }
      div.stButton > button:hover { transform: scale(1.01); }
      .count-badge { display:inline-block; padding:4px 10px; border-radius:6px;
                     font-size:0.75rem; font-weight:bold; margin-bottom:6px; margin-right:6px; }
      .badge-ok { background-color:#dcfce7; color:#166534; }
      .badge-warn { background-color:#fef3c7; color:#92400e; }
      .badge-ng { background-color:#fee2e2; color:#991b1b; }
      .ai-box { background-color:#f0f9ff; border-left:4px solid #0284c7;
                padding:15px; border-radius:4px; margin-bottom:15px; }
      .theme-tag { display:inline-block; background:#1e293b; color:#fff;
                   padding:2px 8px; border-radius:4px; font-size:0.75rem; margin-right:6px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

# =========================================================================
# Pydanticスキーマ（構造化出力・強化版）
# =========================================================================
class ProductProfile(BaseModel):
    selected_type: str = Field(description="商品タイプ。次から1つ: 機能重視 / デザイン重視 / コスパ重視 / 総合")
    type_reason: str = Field(description="そのタイプと判定した根拠を60〜100文字で。")
    extracted_usp: str = Field(description="他社と差別化できる独自の強み・専門情報を100〜150文字で整理。")
    target_persona: str = Field(description="主要ターゲット像（年齢層・状況・購入動機）を1〜2文で。")
    key_seo_keywords: List[str] = Field(description="展開する検索キーワード（共起語含む）を5〜10個。")

class NegativeReviewAnalysis(BaseModel):
    identified_pain_point: str = Field(description="レビューから抽出した最大の不安・不満点を1文で。")
    pain_point_severity: str = Field(description="深刻度: 高 / 中 / 低")
    pattern_a_text: str = Field(description="パターンA（利点強調）。ネガに直接触れず利点で覆う文章。80〜120文字。")
    pattern_b_text: str = Field(description="パターンB（誠実開示）。仕様上の注意点や向かない用途を先に開示する文章。80〜120文字。")
    pattern_c_text: str = Field(description="パターンC（メリット変換）。デメリットに見える特徴を長所に裏返す文章。80〜120文字。")
    recommended_pattern: str = Field(description="推奨するパターン記号。A / B / C のいずれか1文字。")
    ai_recommendation: str = Field(description="推奨理由。E-E-A-T・薬機法・CVRの観点で100〜150文字。")

class AmazonBullet(BaseModel):
    theme: str = Field(description="箇条書きのテーマ。次から1つ選択: 主要ベネフィット / 独自技術・素材 / 使用シーン・対象者 / 品質・安全性・保証 / 使い方・お手入れ / サイズ・スペック / 安全上の注意（誠実開示）")
    body: str = Field(description="本文。日本語80〜120文字（【テーマ】ラベル部分は含めない）。具体的な数値・素材・対象を織り込む。")

class AmazonOutput(BaseModel):
    title: str = Field(description="Amazon商品名。50〜75文字（絶対上限75文字：Amazon 2026年仕様）。構成順序: ブランド → 主要KW → 主要スペック（サイズ/素材/容量） → 用途/対象。半角記号や『｜』で区切ってもよいがすべて75文字以内に収める。価格・送料・セール・☆等の装飾記号は禁止。")
    product_highlights: str = Field(description="商品のハイライト（Amazon 2026年新項目・SEOに影響）。カンマ区切りのキーワード列。7〜15個。1キーワードあたり2〜10文字の日本語名詞句または英数字。含めるべき優先キーワード: (1)主要検索KW (2)素材・成分 (3)対象ユーザー (4)使用シーン (5)差別化スペック (6)サイズ/容量。ブランド名は含めない。重複・全角スペース・改行禁止。例: 『介護用クッション,体圧分散,低反発ウレタン,通気メッシュ,洗える,滑り止め,高齢者,車椅子対応,腰当て,姿勢サポート』")
    bullet_1: AmazonBullet
    bullet_2: AmazonBullet
    bullet_3: AmazonBullet
    bullet_4: AmazonBullet
    bullet_5: AmazonBullet
    description: str = Field(description="Amazon商品説明文。500〜800文字。段落を3〜5個に分け、具体数値・素材・対象・シーン・お手入れを網羅。")
    rufus_qa_pairs: List[str] = Field(description="想定Q&A。『Q: 質問文 / A: 回答文』形式の文字列を5個。対象年齢・洗濯可否・サイズ選び・耐荷重・お手入れなど、購入検討時の頻出質問を優先。")

class RakutenOutput(BaseModel):
    catchcopy: str = Field(description="キャッチコピー。60〜120文字（絶対上限127文字）。狙いSEOキーワードを自然に2〜4個織り込む。")
    desc_text: str = Field(description="スマホ用テキスト説明文。300〜600文字。改行を活用し、HTMLタグは含めない。")
    desc_html: str = Field(description="スマホ・PC用HTML説明文。<h3>見出しを3〜5個、<ul><li>箇条書き、<strong>要所強調のみ。<style>や<script>、インラインCSS、外部リソース参照は含めない。")
    search_keywords_field: str = Field(description="楽天RMSの検索キーワード欄用。半角スペース区切りで10〜30個のキーワードを列挙。重複禁止。")

class EcomUpdateSchema(BaseModel):
    product_profile: ProductProfile
    negative_review_analysis: NegativeReviewAnalysis
    amazon_output: AmazonOutput
    rakuten_output: RakutenOutput

# =========================================================================
# System Instruction（大幅強化）
# =========================================================================
def build_system_instruction(tone_rule: str) -> str:
    return f"""
あなたは日本の主要ECモール（Amazon・楽天市場）のアルゴリズム、購買心理、法規制（薬機法・景表法）を熟知した超一流のECマーケティングコンサルタント兼コピーライターです。

# 【絶対厳守】出力形式
- 出力は必ず指定されたJSONスキーマに完全準拠すること。
- 文字数の指定はすべて「日本語全角＝1文字、半角英数記号＝1文字」でカウントする。
- 文字数の下限・上限を守れない場合は言い回しを削るか補って必ず範囲内に収める。

# 【思考プロセス】※内部で必ず順に実行してから出力
1. 商品タイプ判定（機能／デザイン／コスパ／総合）と判定理由
2. ターゲットペルソナの特定（年齢層・状況・購入動機）
3. USP抽出（自社入力を最優先、無ければ既存文から一次情報を抽出）
4. SEOキーワード展開（入力KWから共起語・関連語を5〜10個作成）
5. ペインポイント抽出＆深刻度判定
6. ネガティブ変換3パターン生成（A利点強調 / B誠実開示 / Cメリット変換）
7. E-E-A-T・薬機法・CVRの観点で推奨パターンを決定
8. Amazon成果物生成（タイトル75字以内→商品ハイライトKW→箇条書き5本→説明文→Q&A）
9. 楽天成果物生成（キャッチ→テキスト→HTML→検索KW欄）

# 【Amazon箇条書き5本のテーマ選定ルール】
- 5本は次のテーマ枠から重複なく5つ選ぶ:
  「主要ベネフィット」「独自技術・素材」「使用シーン・対象者」
  「品質・安全性・保証」「使い方・お手入れ」「サイズ・スペック」「安全上の注意（誠実開示）」
- 推奨パターンがBの場合は「安全上の注意（誠実開示）」を1本必ず含める。
- 各本文は【テーマラベル】＋本文の形式で出力するのではなく、
  theme と body を分けて構造化出力すること（UI側で結合する）。

# 【文字数の厳格ルール】
- Amazon タイトル: 50〜75文字（★絶対上限75文字：Amazon 2026年仕様変更。76文字以上は違反）
- Amazon 商品ハイライト（product_highlights）: カンマ区切りキーワード7〜15個、全体で1〜200文字以内
- Amazon 各箇条書き本文: 80〜120文字
- Amazon 説明文: 500〜800文字
- Amazon Rufus Q&A: 各50〜120文字を5個
- 楽天 キャッチコピー: 60〜120文字（絶対上限127）
- 楽天 テキスト説明: 300〜600文字
- 楽天 HTML説明: 見出し・箇条書きを活用し、実質テキスト量400〜800文字

# 【Amazon 商品名（title）詳細ルール】
- 75文字ハード上限を1文字でも超えたら不合格。生成後に必ず自分で文字数を数え、超過時は削って再構成する。
- 推奨構成: 「ブランド名 主要検索KW 素材/サイズ/容量 用途/対象」の順で情報を凝縮。
- 半角スペースまたは「｜」で情報ブロックを区切ってよい。
- 装飾記号（★☆♪【】※）や絵文字は使用しない。半角スペース以外の空白禁止。
- 主要検索KWは可能な限り前方（先頭〜30文字以内）に配置する。

# 【Amazon 商品ハイライト（product_highlights）詳細ルール】
- Amazon 2026年アップデートで検索アルゴリズムに直接影響する項目。SEO最重要。
- 出力形式: カンマ区切りの単一文字列。半角カンマ「,」で区切り、カンマ前後にスペースを入れない。
- 各キーワード: 2〜10文字の日本語名詞句または英数字。文にしない。助詞不要。
- 個数: 7個以上15個以下。
- 含めるべきカテゴリー（順不同、可能な範囲でカバー）:
  (1)主要検索KW  (2)素材・成分  (3)対象ユーザー（例: 高齢者/女性/子ども）
  (4)使用シーン（例: 車椅子対応/オフィス用）  (5)差別化スペック（例: 洗える/滑り止め）
  (6)サイズ・容量  (7)機能特性（例: 通気性/軽量）
- 禁止事項:
  ・ブランド名／店舗名を含めない
  ・キーワードの重複禁止（表記ゆれも避ける）
  ・全角スペース／改行／絵文字／記号（!?★☆等）禁止
  ・「最高」「日本一」「絶対」等の景表法違反表現禁止
  ・薬機法違反の効果効能表現禁止

# 【法律・規約コンプライアンス（違反ゼロ）】
- 薬機法: 治る/防ぐ/効く/改善する/予防する 等の医療的効果効能表現は絶対禁止。
  必ず「構造・仕様・機能」ベースに言い換える。
  （例: 「腰痛が治る」→「体圧を分散する立体X型構造」）
- 景表法: 「絶対」「最高」「日本一」「世界一」「No.1」など客観的根拠のない最上級表現は禁止。
- Amazon規約: 価格・送料・セール・ストア名・URL・☆等の装飾記号の乱用は禁止。
- 楽天規約: 客観的根拠のない最上級表現、他店比較、誇大表現は禁止。

# 【Rufus / 楽天AI 最適化】
- 自然文Q&A（「対象年齢は？」「洗濯できますか？」「〇歳の子どもでも使える？」）に
  AIクローラーが即答を抽出できるよう、【数値】【素材】【対象】【シーン】【手入れ】【対応外】を
  地の文にロジカルに埋め込むこと。
- 肯否は明確に。「〜できます」「〜には対応していません」の断定形を使う。
- Amazon の rufus_qa_pairs には「Q: 質問文 / A: 回答文」形式で5個生成。

# 【SEOキーワード展開ルール】
- 入力された狙いキーワードは、Amazonタイトル冒頭、楽天キャッチコピー、
  楽天 search_keywords_field に必ず反映。
- 共起語・関連語は箇条書き・説明文に自然に分散配置。
- 同一KWの過度な繰り返し（3回以上）は禁止。

# 【トーン適用ルール】
{tone_rule}
"""

# =========================================================================
# ヘルパー関数
# =========================================================================
def _strip_code_fences(text: str) -> str:
    """AIレスポンスの前後についた ```json などのフェンスを除去。"""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def _safe_json_loads(text: str) -> dict:
    """堅牢なJSON解析。Geminiが生成する制御文字混入・末尾切れなどに対応。

    段階的に緩めていく：
    1. strict=False で制御文字（生改行等）を許容
    2. 危険な制御文字を除去して再試行
    3. 末尾が切れている場合は最終の '}' までを切り出して再試行
    """
    # 1st: strict=False（生改行OK）
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        pass
    # 2nd: 制御文字（Tab/改行以外のC0）を除去
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    try:
        return json.loads(cleaned, strict=False)
    except json.JSONDecodeError:
        pass
    # 3rd: 末尾切れ対策（最終 '}' までで切り取り）
    last_brace = cleaned.rfind("}")
    if last_brace > 0:
        try:
            return json.loads(cleaned[: last_brace + 1], strict=False)
        except json.JSONDecodeError as e:
            raise e
    raise json.JSONDecodeError("有効なJSON構造が見つかりません", text, 0)

def _call_gemini_api(api_key: str, model_name: str, user_prompt: str,
                     system_instruction: str, temperature: float = 0.7,
                     max_retries: int = 2,
                     thinking_budget: int = 1024) -> dict:
    """Gemini API を呼び出す。

    Gemini 2.5 Pro は既定で「思考モード」が有効で、思考が出力トークン予算を大量に消費する。
    - thinking_budget を明示することで、思考は残しつつ本文出力の余裕を確保する
    - max_output_tokens は思考＋本文の合計上限のため十分大きくする
    - 診断のため usage_metadata と finish_reason を戻り値に含める
    """
    last_err = None
    last_raw = ""
    last_usage = None
    last_finish_reason = None

    for attempt in range(max_retries + 1):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction,
            )

            gen_config = {
                "response_mime_type": "application/json",
                "response_schema": EcomUpdateSchema,
                "temperature": temperature,
                "top_p": 0.95,
                "max_output_tokens": 32768,  # 思考トークン+本文の合計。Gemini 2.5系は思考が数千を消費するため大きめに
            }
            # Gemini 2.5系のみ thinking_budget を試みに設定（SDK未対応版のためのフォールバック付き）
            supports_thinking = "2.5" in model_name
            if supports_thinking:
                gen_config["thinking_config"] = {"thinking_budget": thinking_budget}

            try:
                response = model.generate_content(user_prompt, generation_config=gen_config)
            except Exception as gen_err:
                # SDKが thinking_config を認識しない場合は除去して再試行
                msg = str(gen_err).lower()
                if "thinking" in msg or "unknown field" in msg or "unexpected keyword" in msg:
                    gen_config.pop("thinking_config", None)
                    response = model.generate_content(user_prompt, generation_config=gen_config)
                else:
                    raise

            # 診断情報を取得（例外は握りつぶす）
            try:
                um = response.usage_metadata
                last_usage = {
                    "prompt_tokens": getattr(um, "prompt_token_count", None),
                    "output_tokens": getattr(um, "candidates_token_count", None),
                    "thoughts_tokens": getattr(um, "thoughts_token_count", None),
                    "total_tokens": getattr(um, "total_token_count", None),
                }
            except Exception:
                pass
            try:
                last_finish_reason = str(response.candidates[0].finish_reason)
            except Exception:
                pass

            raw = _strip_code_fences(response.text)
            last_raw = raw
            result = _safe_json_loads(raw)
            # 診断メタ情報を結果に付加
            result["_meta"] = {
                "usage": last_usage,
                "finish_reason": last_finish_reason,
                "model": model_name,
                "thinking_budget": thinking_budget if supports_thinking else None,
            }
            return result

        except json.JSONDecodeError as e:
            pos = getattr(e, "pos", 0) or 0
            snippet_start = max(0, pos - 60)
            snippet_end = min(len(last_raw), pos + 60)
            snippet = last_raw[snippet_start:snippet_end].replace("\n", "\\n")
            last_err = (f"JSON解析エラー: {e}\n"
                        f"周辺文字列: ...{snippet}...")
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        if attempt < max_retries:
            time.sleep(1.2)

    return {
        "error": last_err or "不明なエラー",
        "raw": last_raw[:2000] if last_raw else "",
        "_meta": {"usage": last_usage, "finish_reason": last_finish_reason, "model": model_name},
    }

def _char_badge(text: str, target: tuple, hard_max: int = None) -> str:
    """文字数バッジのHTMLを返す。目標範囲内=OK、範囲外=WARN、ハード超過=NG。"""
    n = len(text or "")
    lo, hi = target
    if hard_max and n > hard_max:
        cls, label = "badge-ng", f"{n}文字 / 上限{hard_max}超過"
    elif lo <= n <= hi:
        cls, label = "badge-ok", f"{n}文字（目標 {lo}〜{hi}）"
    else:
        cls, label = "badge-warn", f"{n}文字（目標 {lo}〜{hi}）"
    return f'<span class="count-badge {cls}">{label}</span>'

def _char_badge_count(items: list, target: tuple) -> str:
    """個数（例：キーワード数）を検証するバッジ。目標範囲内=OK、範囲外=WARN。"""
    n = len(items or [])
    lo, hi = target
    if lo <= n <= hi:
        cls, label = "badge-ok", f"{n}個（目標 {lo}〜{hi}個）"
    else:
        cls, label = "badge-warn", f"{n}個（目標 {lo}〜{hi}個）"
    return f'<span class="count-badge {cls}">{label}</span>'

def _build_user_prompt(genre: str, tone: str, seo_kw: str,
                       base: str, usp: str, spec: str, review: str) -> str:
    return f"""
【商品情報】
- ジャンル: {genre}
- 文章トーン: {tone}
- 狙いSEOキーワード: {seo_kw if seo_kw else "（未入力：文脈から自動抽出してください）"}

【入力データ】
1. 現在の商品説明・箇条書き:
{base}

2. 自社の強み・USP:
{usp if usp else "（未入力：既存文から他社と差別化できる一次情報を抽出してください）"}

3. スペック・仕様・サイズ等:
{spec}

4. カスタマーレビュー・顧客の悩み:
{review}

【指示】
上記データを元に、システム指示に沿ってJSON出力を生成してください。
文字数ルールと法律コンプライアンスを最優先で遵守してください。
"""

# =========================================================================
# 出力レンダリング
# =========================================================================
def render_profile_and_reviews(res: dict):
    st.header("🧠 AI分析 ＆ ネガティブレビュー対策")
    col1, col2 = st.columns([1, 1.3], gap="medium")

    with col1:
        st.subheader("📋 商品プロファイリング")
        p = res["product_profile"]
        st.markdown(f"**商品タイプ**：`{p['selected_type']}`")
        st.markdown(f"**判定理由**：{p['type_reason']}")
        st.markdown(f"**抽出USP**：{p['extracted_usp']}")
        st.markdown(f"**ターゲット像**：{p['target_persona']}")
        st.markdown("**展開SEOキーワード**：")
        st.write("　".join([f"`{kw}`" for kw in p.get("key_seo_keywords", [])]))

    with col2:
        st.subheader("💡 ネガティブ変換 3パターン")
        n = res["negative_review_analysis"]
        st.markdown(
            f"<div class='ai-box'>"
            f"<strong>🔎 最大の不安・不満点：</strong>{n['identified_pain_point']}<br>"
            f"<strong>⚠️ 深刻度：</strong>{n['pain_point_severity']}<br>"
            f"<strong>🤖 推奨パターン：</strong>{n['recommended_pattern']}<br>"
            f"<strong>💬 推奨理由：</strong>{n['ai_recommendation']}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.text_area("パターンA（利点強調）", value=n["pattern_a_text"], height=90, key="pat_a")
        st.text_area("パターンB（誠実開示：Google SEO推奨）", value=n["pattern_b_text"], height=90, key="pat_b")
        st.text_area("パターンC（メリット変換）", value=n["pattern_c_text"], height=90, key="pat_c")
        st.caption("※必要に応じてコピーし、各モールの説明文へ手動統合してください。")

def render_amazon_tab(res: dict):
    a = res["amazon_output"]
    st.subheader("📤 Amazon 最適化テキスト")
    st.caption("価格・送料表現ゼロ、Rufusが引用しやすい構造を採用。2026年仕様（タイトル75字・商品ハイライト対応）。")

    # タイトル（75文字ハード上限）
    st.markdown("##### 商品名（タイトル）※75文字ハード上限")
    st.markdown(
        _char_badge(a["title"], AMAZON_TITLE_TARGET, hard_max=AMAZON_TITLE_HARD_MAX),
        unsafe_allow_html=True,
    )
    st.text_area("Amazonタイトル", value=a["title"], height=80,
                 key="amz_title", label_visibility="collapsed")
    if len(a["title"]) > AMAZON_TITLE_HARD_MAX:
        st.error(f"⚠️ タイトルが75文字を超えています（現在 {len(a['title'])} 文字）。再生成または手動で削ってください。")

    # 商品のハイライト（2026新仕様・SEOに影響）
    st.markdown("##### 🆕 商品のハイライト（カンマ区切りキーワード）")
    st.caption("Amazon 2026年アップデートで検索SEOに直接影響。カンマ区切りキーワードで、素材・対象・シーン・スペックを網羅。")
    highlights = a.get("product_highlights", "")
    kw_list = [k.strip() for k in highlights.split(",") if k.strip()]
    st.markdown(
        _char_badge_count(kw_list, AMAZON_HIGHLIGHT_KW_TARGET),
        unsafe_allow_html=True,
    )
    st.text_area("Amazon商品ハイライト", value=highlights, height=90,
                 key="amz_highlights", label_visibility="collapsed")
    # 個別キーワードを視認しやすく列挙
    if kw_list:
        st.markdown(" ".join([f'<span class="theme-tag">{kw}</span>' for kw in kw_list]),
                    unsafe_allow_html=True)

    # 箇条書き
    st.markdown("##### 箇条書き（5本）")
    for i in range(1, 6):
        b = a[f"bullet_{i}"]
        theme = b.get("theme", "")
        body = b.get("body", "")
        st.markdown(
            f'<span class="theme-tag">テーマ: {theme}</span>'
            f'{_char_badge(body, AMAZON_BULLET_TARGET)}',
            unsafe_allow_html=True,
        )
        st.text_area(f"bullet_{i}", value=body, height=90,
                     key=f"amz_b_{i}", label_visibility="collapsed")

    # 商品説明
    st.markdown("##### 商品説明文")
    st.markdown(_char_badge(a["description"], AMAZON_DESC_TARGET), unsafe_allow_html=True)
    st.text_area("Amazon説明文", value=a["description"], height=220,
                 key="amz_desc", label_visibility="collapsed")

    # Rufus Q&A
    st.markdown("##### Rufus想定Q&A（5個）")
    st.caption("Rufusが自然文の質問に対して抽出しやすいQ&Aペア。")
    qa_list = a.get("rufus_qa_pairs", [])
    for i, qa in enumerate(qa_list, 1):
        st.text_area(f"Q&A {i}", value=qa, height=70,
                     key=f"amz_qa_{i}", label_visibility="collapsed")

def render_rakuten_tab(res: dict):
    r = res["rakuten_output"]
    st.subheader("📤 楽天市場 最適化テキスト")
    st.caption("スマホCVR最適化 & 楽天AI検索対策。")

    st.markdown("##### キャッチコピー")
    st.markdown(
        _char_badge(r["catchcopy"], RAKUTEN_CATCH_TARGET, hard_max=RAKUTEN_CATCH_HARD_MAX),
        unsafe_allow_html=True,
    )
    st.text_area("楽天キャッチ", value=r["catchcopy"], height=80,
                 key="rak_catch", label_visibility="collapsed")

    st.markdown("##### 商品説明文（テキスト版）")
    st.markdown(_char_badge(r["desc_text"], RAKUTEN_TEXT_TARGET), unsafe_allow_html=True)
    st.text_area("楽天テキスト", value=r["desc_text"], height=180,
                 key="rak_text", label_visibility="collapsed")

    st.markdown("##### 商品説明文（HTML版）")
    st.text_area("楽天HTML", value=r["desc_html"], height=260,
                 key="rak_html", label_visibility="collapsed")

    with st.expander("👁️ HTMLプレビュー"):
        st.markdown(r["desc_html"], unsafe_allow_html=True)

    st.markdown("##### 検索キーワード欄（RMS入稿用）")
    st.text_area("楽天KW欄", value=r["search_keywords_field"], height=80,
                 key="rak_kw", label_visibility="collapsed")

# =========================================================================
# メイン
# =========================================================================
def main():
    _inject_custom_style()
    st.title("🛡️ 次世代型 モール別AI対策＆SEO最適化ツール Pro")
    st.caption("Amazon Rufus / 楽天AI / E-E-A-T / 薬機法検閲を統合。構造化出力＆リトライ機構で高精度化。")

    # ---- サイドバー ----
    with st.sidebar:
        st.header("🔑 接続設定")
        api_key = st.text_input("Gemini APIキー", type="password", placeholder="AIキーを入力")
        model_name = st.selectbox(
            "使用AIモデル（品質重視は Pro を推奨）",
            AVAILABLE_MODELS,
            index=0,
        )
        temperature = st.slider("Temperature（0.3〜0.5推奨）", 0.0, 1.0, 0.5, 0.05)
        thinking_budget = st.slider(
            "思考予算 Thinking Budget（Gemini 2.5系のみ）",
            min_value=0, max_value=8192, value=1024, step=256,
            help=(
                "Gemini 2.5系は既定で大量の思考トークンを消費し、本文出力が短くなる原因になります。"
                "1024程度に抑えると本文の生成量が回復します。"
                "0にすると思考を最小化しますが、複雑な推論品質は下がります。"
            ),
        )

        st.divider()
        st.header("🎨 リライト基本設定")
        genre = st.selectbox(
            "商品ジャンル",
            ["一般雑貨", "季節行事（ハロウィン等）", "推し活・ホビー",
             "介護・看護", "ベビー", "ペット", "スポーツ", "園芸", "その他"],
        )
        tone = st.radio("文章のトーン", list(TONE_MAPPING.keys()))

    # ---- 入力エリア ----
    st.subheader("📥 元情報の入力")
    col_in1, col_in2 = st.columns(2, gap="medium")
    with col_in1:
        c_base = st.text_area("1. 現在の商品説明・箇条書き（必須）", height=140,
                              placeholder="既存の商品ページ文章を貼り付けてください。")
        c_usp = st.text_area("2. 自社独自の強み・こだわり・専門情報（任意）", height=110,
                             placeholder="工場直接仕入れ、独自の検品体制、素材規格など。空欄ならAIが自動抽出します。")
    with col_in2:
        c_spec = st.text_area("3. 補足スペック・仕様・サイズ等（必須）", height=140,
                              placeholder="サイズ、重量、素材、耐荷重、付属品などの正確な数値（Rufus対策に直結）。")
        c_review = st.text_area("4. カスタマーレビュー・顧客の悩み（必須）", height=110,
                                placeholder="ネガティブなレビューや、購入者が迷いやすいポイントを貼り付けてください。")
        c_seo = st.text_input("5. 狙いたいSEOキーワード（任意）",
                              placeholder="例：介護用クッション, 洗える, 通気性")

    st.markdown("---")

    # ---- 実行ボタン ----
    run = st.button("🔥 全モール共通・超高精度AIリライトを実行")
    if run:
        errs = []
        if not api_key:
            errs.append("Gemini APIキーを入力してください。")
        if not c_base:
            errs.append("「1. 現在の商品説明」は必須です。")
        if not c_spec:
            errs.append("「3. スペック・仕様」は必須です。")
        if not c_review:
            errs.append("「4. カスタマーレビュー」は必須です。")

        if errs:
            for e in errs:
                st.error(e)
        else:
            with st.spinner("プロのECコンサルタントAIが思考中...（規約・薬機法・E-E-A-T・AI検索対策を同時実行）"):
                sys_inst = build_system_instruction(TONE_MAPPING[tone])
                user_prompt = _build_user_prompt(genre, tone, c_seo, c_base, c_usp, c_spec, c_review)
                res = _call_gemini_api(
                    api_key, model_name, user_prompt, sys_inst,
                    temperature=temperature,
                    thinking_budget=thinking_budget,
                )

                if "error" in res:
                    st.error(f"APIエラー：{res['error']}")
                    st.info("モデル名を切り替える／temperature を下げる／入力を短くする、などをお試しください。")
                    if res.get("raw"):
                        with st.expander("🔍 AIの生レスポンス（先頭2000文字・デバッグ用）"):
                            st.code(res["raw"], language="json")
                else:
                    st.session_state["ecom_result"] = res
                    st.success("生成が完了しました。下部で結果を確認してください。")

                    # 診断情報：短い出力になっていないかここで即警告
                    meta = res.get("_meta", {})
                    usage = meta.get("usage") or {}
                    fr = meta.get("finish_reason") or ""
                    thoughts = usage.get("thoughts_tokens") or 0
                    output = usage.get("output_tokens") or 0
                    if "MAX_TOKENS" in fr:
                        st.warning(
                            "⚠️ 出力が最大トークン数に達して切り詰められました。"
                            "サイドバーの『思考予算』を下げるか、モデルを Flash 系に切り替えてください。"
                        )
                    elif thoughts and output and thoughts > output * 3:
                        st.warning(
                            f"⚠️ 思考トークンが本文の3倍以上を消費しています "
                            f"(思考 {thoughts} / 本文 {output})。"
                            "サイドバーの『思考予算』を下げると本文が長くなります。"
                        )

    # ---- 結果表示 ----
    if "ecom_result" in st.session_state:
        res = st.session_state["ecom_result"]
        render_profile_and_reviews(res)
        st.markdown("---")
        tab_amz, tab_rak = st.tabs(
            ["🛒 Amazon成果物（Rufus・規約対策）", "🔴 楽天成果物（楽天AI・スマホHTML）"]
        )
        with tab_amz:
            render_amazon_tab(res)
        with tab_rak:
            render_rakuten_tab(res)

        st.divider()

        # 診断パネル
        meta = res.get("_meta") or {}
        usage = meta.get("usage") or {}
        if usage:
            with st.expander("📊 生成の診断情報（トークン使用量・終了理由）"):
                cols = st.columns(4)
                cols[0].metric("入力トークン", usage.get("prompt_tokens") or "N/A")
                cols[1].metric("本文出力", usage.get("output_tokens") or "N/A")
                cols[2].metric("思考消費", usage.get("thoughts_tokens") or "N/A")
                cols[3].metric("合計", usage.get("total_tokens") or "N/A")
                st.caption(
                    f"モデル: {meta.get('model', 'N/A')}　"
                    f"終了理由: {meta.get('finish_reason', 'N/A')}　"
                    f"思考予算: {meta.get('thinking_budget', 'N/A')}"
                )
                st.caption("『本文出力』が2000未満の場合、思考予算を下げると本文が長くなります。")

        with st.expander("🧾 生JSON（デバッグ用）"):
            st.json(res)


if __name__ == "__main__":
    main()
