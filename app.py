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

# 2段階生成用の分割スキーマ（1回あたりのフィールド数を減らして構造化失敗を防ぐ）
class AnalysisSchema(BaseModel):
    """Stage 1: 分析フェーズのみ"""
    product_profile: ProductProfile
    negative_review_analysis: NegativeReviewAnalysis

class ContentSchema(BaseModel):
    """Stage 2: 成果物生成のみ（分析結果を文脈として受け取る）"""
    amazon_output: AmazonOutput
    rakuten_output: RakutenOutput

# =========================================================================
# フラットスキーマ（全フィールド str のみ・ネスト/List なし）
# Geminiの構造化出力はList[str]やネストクラスでフィールド欠落が発生しやすいため、
# フラット構造で確実に生成させ、パース後に元のネスト構造に組み直す。
# =========================================================================
class AnalysisSchemaFlat(BaseModel):
    # product_profile
    selected_type: str = Field(description="商品タイプ: 機能重視 / デザイン重視 / コスパ重視 / 総合 のいずれか")
    type_reason: str = Field(description="判定理由。1〜2文で簡潔に。")
    extracted_usp: str = Field(description="独自の強み・専門情報。2〜3文で。")
    target_persona: str = Field(description="主要ターゲット像（年齢・状況・購入動機）。1〜2文で。")
    key_seo_keywords_csv: str = Field(description="展開SEOキーワードをカンマ区切りで（例: 介護用クッション,体圧分散,通気性）")
    # negative_review_analysis
    identified_pain_point: str = Field(description="最大の不安・不満点。1文で。")
    pain_point_severity: str = Field(description="深刻度: 高 / 中 / 低 のいずれか")
    pattern_a_text: str = Field(description="パターンA（利点強調）の文章。")
    pattern_b_text: str = Field(description="パターンB（誠実開示）の文章。")
    pattern_c_text: str = Field(description="パターンC（メリット変換）の文章。")
    recommended_pattern: str = Field(description="推奨パターン: A / B / C のいずれか1文字")
    ai_recommendation: str = Field(description="推奨理由。2〜3文で。")

class ContentSchemaFlat(BaseModel):
    # Amazon
    amz_title: str = Field(description="Amazon商品名。50〜75文字絶対厳守。ブランド→主要KW→スペック→用途")
    amz_product_highlights: str = Field(description="商品ハイライト。カンマ区切りキーワード7〜15個。【重複禁止ルール厳守】amz_titleに含まれるキーワードは絶対に含めない。商品名で使わなかった検索語（同義語・関連語・別カテゴリ語）だけを配置し、両フィールドで検索カバレッジを最大化する。例: 介護用クッション,体圧分散,低反発ウレタン,通気メッシュ,洗える")
    amz_bullet_1_theme: str = Field(description="箇条書き1テーマ: 主要ベネフィット/独自技術・素材/使用シーン・対象者/品質・安全性・保証/使い方・お手入れ/サイズ・スペック/安全上の注意 のいずれか")
    amz_bullet_1_body: str = Field(description="箇条書き1本文80〜120文字")
    amz_bullet_2_theme: str = Field(description="箇条書き2テーマ（1と重複禁止）")
    amz_bullet_2_body: str = Field(description="箇条書き2本文80〜120文字")
    amz_bullet_3_theme: str = Field(description="箇条書き3テーマ")
    amz_bullet_3_body: str = Field(description="箇条書き3本文80〜120文字")
    amz_bullet_4_theme: str = Field(description="箇条書き4テーマ")
    amz_bullet_4_body: str = Field(description="箇条書き4本文80〜120文字")
    amz_bullet_5_theme: str = Field(description="箇条書き5テーマ")
    amz_bullet_5_body: str = Field(description="箇条書き5本文80〜120文字")
    amz_description: str = Field(description="Amazon商品説明文500〜800文字")
    amz_qa_1: str = Field(description="Rufus想定Q&A 1個目。『Q: 質問 / A: 回答』形式")
    amz_qa_2: str = Field(description="Rufus想定Q&A 2個目")
    amz_qa_3: str = Field(description="Rufus想定Q&A 3個目")
    amz_qa_4: str = Field(description="Rufus想定Q&A 4個目")
    amz_qa_5: str = Field(description="Rufus想定Q&A 5個目")
    # 楽天
    rak_catchcopy: str = Field(description="楽天キャッチコピー60〜120文字（絶対上限127）")
    rak_desc_text: str = Field(description="楽天テキスト説明300〜600文字")
    rak_desc_html: str = Field(description="楽天HTML説明。h3見出し3〜5個、ulリスト活用、strong強調は要所のみ")
    rak_search_kw: str = Field(description="楽天検索キーワード欄。半角スペース区切り10〜30個")

def _unflatten_analysis(flat: dict) -> dict:
    """フラットな分析結果を元のネスト構造に組み直す。"""
    kw_csv = flat.get("key_seo_keywords_csv", "") or ""
    kws = [k.strip() for k in kw_csv.split(",") if k.strip()]
    return {
        "product_profile": {
            "selected_type": flat.get("selected_type", ""),
            "type_reason": flat.get("type_reason", ""),
            "extracted_usp": flat.get("extracted_usp", ""),
            "target_persona": flat.get("target_persona", ""),
            "key_seo_keywords": kws,
        },
        "negative_review_analysis": {
            "identified_pain_point": flat.get("identified_pain_point", ""),
            "pain_point_severity": flat.get("pain_point_severity", ""),
            "pattern_a_text": flat.get("pattern_a_text", ""),
            "pattern_b_text": flat.get("pattern_b_text", ""),
            "pattern_c_text": flat.get("pattern_c_text", ""),
            "recommended_pattern": flat.get("recommended_pattern", ""),
            "ai_recommendation": flat.get("ai_recommendation", ""),
        },
    }

def _unflatten_content(flat: dict) -> dict:
    """フラットな成果物を元のネスト構造に組み直す。"""
    qa_pairs = [flat.get(f"amz_qa_{i}", "") for i in range(1, 6)]
    qa_pairs = [q for q in qa_pairs if q]
    amazon = {
        "title": flat.get("amz_title", ""),
        "product_highlights": flat.get("amz_product_highlights", ""),
        "description": flat.get("amz_description", ""),
        "rufus_qa_pairs": qa_pairs,
    }
    for i in range(1, 6):
        amazon[f"bullet_{i}"] = {
            "theme": flat.get(f"amz_bullet_{i}_theme", ""),
            "body": flat.get(f"amz_bullet_{i}_body", ""),
        }
    rakuten = {
        "catchcopy": flat.get("rak_catchcopy", ""),
        "desc_text": flat.get("rak_desc_text", ""),
        "desc_html": flat.get("rak_desc_html", ""),
        "search_keywords_field": flat.get("rak_search_kw", ""),
    }
    return {"amazon_output": amazon, "rakuten_output": rakuten}

# =========================================================================
# System Instruction（大幅強化）
# =========================================================================
def build_system_instruction(tone_rule: str) -> str:
    return f"""
あなたは日本の主要ECモール（Amazon・楽天市場）のアルゴリズム、購買心理、法規制（薬機法・景表法）を熟知した超一流のECマーケティングコンサルタント兼コピーライターです。

# 【絶対厳守】出力形式
- 出力は必ず**呼び出しごとに指定されたJSONスキーマ**に完全準拠すること。
- 文字数の指定はすべて「日本語全角＝1文字、半角英数記号＝1文字」でカウントする。
- 文字数指定は目安であり、多少の逸脱は許容する。文字数の調整コメント・編集記録・タイムスタンプなどのメタ情報は絶対に出力しないこと。
- 【最重要】スキーマに定義された全フィールドを空文字にせず必ず埋めること。
- 【最重要】スキーマは常に**フラットな一階層構造**である。ネストされたオブジェクト（`{{"product_profile": {{...}}}}` のような入れ子）は絶対に作らない。全フィールドはトップレベルに配置すること。
- 【最重要】出力にMarkdownコードフェンス（```json や ``` の三連バッククォート）は絶対に含めない。純粋な JSON のみを返す。
- 【最重要】ある1つのフィールド値の中に、他のフィールドや別のJSONオブジェクトを文字列として詰め込むことは禁止。各フィールドは自身の担当内容だけを埋めること。
- 【最重要】文字列値の中に以下の装飾・パディング文字を絶対に含めないこと。
  検出された場合、そのフィールドは無効として扱う：
  ・ゼロ幅スペース（U+200B）、ゼロ幅ノーブレークスペース（U+FEFF）
  ・ゼロ幅ジョイナ（U+200C, U+200D）
  ・行区切り（U+2028）、段落区切り（U+2029）
  ・フォームフィード（\\f）、垂直タブ（\\v）
  ・3個以上の連続改行（\\n\\n\\n以上）
- 【最重要】文字数の下限・上限は「目安」であり、実質的な内容を書き切ったら
  それ以上の文字数のために文章を水増しせず、その時点でフィールドを完成させて次のフィールドへ移ること。
  内容が短くても構わない。長さを稼ぐための無意味な繰り返し・記号列は禁止。
- 【重要】JSON文字列値内の改行は\\nでエスケープし、ダブルクォートは\\"でエスケープすること。

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

# 【★最重要 Amazon 商品名(amz_title)と商品ハイライト(amz_product_highlights)の重複禁止ルール】
- 商品名と商品ハイライトは Amazon 検索アルゴリズムでそれぞれ独立してインデックスされるため、
  両者で同じキーワードを使うことはSEO上「インデックス枠の無駄遣い」となり、
  検索カバレッジを大きく損なう最大のアンチパターンである。
- ルール: 商品名で使ったキーワードは商品ハイライトに絶対に含めない。逆も同様。
- 具体例:
  ・NG: 商品名「ぬいポーチ 15cm 2体収納 PUレザー」 かつ ハイライト「ぬいポーチ,15cm,2体収納,PUレザー」
    → 完全重複でSEO無効
  ・OK: 商品名「ぬいポーチ 15cm 2体収納 PUレザー」 かつ ハイライト「痛バッグ,ぬい活,ディスプレイケース,自立,見せる収納」
    → 補完関係で検索カバレッジ最大化
- 生成手順（厳守）:
  Step1. amz_title を先に確定させる（主要検索KWをここに配置）
  Step2. amz_title の各キーワードをリストアップし記憶する
  Step3. amz_product_highlights には Step2 のリストに**含まれないキーワードだけ**を配置する
         （同義語・関連語・別カテゴリの検索語・別の使用シーン語などで補完する）
- 表記ゆれも重複扱いとする（例: 商品名に「15cm」 ハイライトに「15センチ」も禁止）。

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

def _sanitize_ai_padding(text: str) -> str:
    """Geminiが挿入する装飾パディング（ゼロ幅スペース・過剰改行・フォームフィード）を除去。

    Gemini 2.5 系はスキーマの min-length 制約を満たそうとして、実質内容の後に
    以下のパターンを大量に挿入することがある：
    - \\u200B (ゼロ幅スペース)、\\u200C, \\u200D, \\uFEFF (BOM)
    - \\u2028, \\u2029 (行区切り・段落区切り)
    - \\f (フォームフィード / 改ページ)
    - 3個以上の連続改行

    これらは全て「AIが埋めるべき情報を持たなかった証拠」であり、実質内容ではない。
    """
    if not isinstance(text, str):
        return text
    # ゼロ幅・不可視文字を全除去
    text = re.sub(r"[\u200B\u200C\u200D\uFEFF\u2028\u2029]", "", text)
    # フォームフィード・垂直タブを除去
    text = text.replace("\f", "").replace("\v", "")
    # 3個以上の連続改行を2個に圧縮
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 末尾の空白・改行を除去
    return text.strip()

def _sanitize_response_dict(d: dict) -> dict:
    """レスポンス辞書内の全文字列値をサニタイズ。ネストしたdict/listにも対応。"""
    if isinstance(d, dict):
        return {k: _sanitize_response_dict(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_sanitize_response_dict(x) for x in d]
    if isinstance(d, str):
        return _sanitize_ai_padding(d)
    return d

def _safe_json_loads(text: str) -> dict:
    """堅牢なJSON解析。Geminiが生成する制御文字混入・末尾切れ・未閉鎖構造などに対応。

    段階的に緩めていく：
    1. strict=False で制御文字（生改行等）を許容
    2. 危険な制御文字を除去して再試行
    3. 末尾が切れている場合は最終の '}' までを切り出して再試行
    4. 未閉鎖の文字列・括弧を自動修復して再試行
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
        except json.JSONDecodeError:
            pass
    # 4th: 未閉鎖の文字列・括弧を自動修復
    repaired = _try_json_repair(cleaned)
    if repaired is not None:
        return repaired
    raise json.JSONDecodeError("有効なJSON構造が見つかりません", text, 0)

def _try_json_repair(text: str):
    """末尾切れ・不完全なJSONを修復して解析を試みる。

    AIが応答途中で切断された場合、以下のパターンが発生する：
    - 文字列値の途中で切断 → 閉じ " が不足
    - オブジェクトの途中で切断 → 閉じ }, ] が不足
    - 末尾に不要なカンマ → JSON構文違反

    これらを検出して自動補完する。
    """
    if not text or "{" not in text:
        return None

    # 最初の { から開始
    start = text.find("{")
    text = text[start:]

    # 文字列内/構造レベルを追跡しながら括弧を数える
    in_string = False
    escape = False
    stack = []  # 開いた括弧のスタック

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            expected = "{" if ch == "}" else "["
            if stack and stack[-1] == expected:
                stack.pop()

    # 修復開始
    # (a) 未閉鎖の文字列を閉じる
    if in_string:
        # エスケープ途中で切れている場合は末尾の \ を除去
        text = text.rstrip("\\")
        text += '"'

    # (b) 末尾の不要カンマ・空白を除去（文字列外で）
    text = re.sub(r",\s*$", "", text.rstrip())

    # (c) 開いたままの括弧を逆順で閉じる
    closer = {"{": "}", "[": "]"}
    for opener in reversed(stack):
        text += closer[opener]

    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        return None

def _extract_buried_json(text: str) -> dict:
    """フィールド値内に埋め込まれたJSON（Markdownコードフェンス付き）を救出する。

    Gemini 2.5 系はフラットスキーマ指定を無視して、旧来のネスト構造JSONを
    1フィールドの値の中に文字列として詰め込んでしまう挙動が確認されている。
    ゼロ幅スペースや大量の改行でパディングされていることが多いため、
    それらを除去してから ```json ... ``` を抽出する。
    """
    if not isinstance(text, str) or "{" not in text:
        return None
    # ゼロ幅文字・制御文字・BOMを除去
    cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff\u2028\u2029]", "", text)
    # Markdownコードフェンス内のJSONを探す
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if m:
        candidate = m.group(1)
    else:
        # フェンス無しでも {} で囲まれた大きなブロックを探す
        # 最初の { から最後の } まで
        first = cleaned.find("{")
        last = cleaned.rfind("}")
        if first < 0 or last <= first:
            return None
        candidate = cleaned[first: last + 1]
    try:
        return json.loads(candidate, strict=False)
    except json.JSONDecodeError:
        # 制御文字（生改行等）を除いて再試行
        cleaned2 = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", candidate)
        try:
            return json.loads(cleaned2, strict=False)
        except json.JSONDecodeError:
            return None

def _try_recover_from_buried_json(flat_response: dict) -> dict:
    """フラット出力の各フィールド値を走査し、埋め込みJSONを検出したら返す。"""
    if not isinstance(flat_response, dict):
        return None
    # 長そうな文字列フィールドを優先的に探す
    candidates = sorted(
        [(k, v) for k, v in flat_response.items()
         if isinstance(v, str) and len(v) > 500],
        key=lambda x: -len(x[1]),
    )
    for key, val in candidates:
        buried = _extract_buried_json(val)
        if buried and isinstance(buried, dict):
            # 期待するトップレベルキーが含まれているか
            if "product_profile" in buried or "amazon_output" in buried:
                return buried
    return None

def _call_gemini_api(api_key: str, model_name: str, user_prompt: str,
                     system_instruction: str, temperature: float = 0.7,
                     max_retries: int = 2,
                     thinking_budget: int = 1024,
                     response_schema=EcomUpdateSchema) -> dict:
    """Gemini API を呼び出す。

    Gemini 2.5 Pro は既定で「思考モード」が有効で、思考が出力トークン予算を大量に消費する。
    - thinking_budget を明示することで、思考は残しつつ本文出力の余裕を確保する
    - max_output_tokens は思考＋本文の合計上限のため十分大きくする
    - 診断のため usage_metadata と finish_reason を戻り値に含める
    - response_schema を切り替えることで、フェーズ別の小さなスキーマで安定生成できる
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
                "response_schema": response_schema,
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
            # Geminiが挿入する装飾パディング（ゼロ幅スペース等）を全文字列値から除去
            result = _sanitize_response_dict(result)
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
            head_snippet = last_raw[snippet_start:snippet_end].replace("\n", "\\n")
            # 応答の末尾も表示（切断されているかを診断するため）
            tail_snippet = last_raw[-200:].replace("\n", "\\n") if len(last_raw) > 200 else ""
            last_err = (
                f"JSON解析エラー: {e}\n"
                f"周辺文字列: ...{head_snippet}...\n"
                f"応答末尾200文字: ...{tail_snippet}\n"
                f"応答全長: {len(last_raw)}文字, finish_reason: {last_finish_reason}"
            )
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        if attempt < max_retries:
            time.sleep(1.2)

    return {
        "error": last_err or "不明なエラー",
        "raw": last_raw[:2000] if last_raw else "",
        "_meta": {"usage": last_usage, "finish_reason": last_finish_reason, "model": model_name},
    }

def _call_gemini_two_stage(api_key: str, model_name: str,
                            system_instruction: str,
                            genre: str, tone: str, seo_kw: str,
                            base: str, usp: str, spec: str, review: str,
                            temperature: float = 0.5,
                            thinking_budget: int = 2048,
                            progress_cb=None) -> dict:
    """2段階生成: 分析→成果物 に分けてフラットスキーマで確実に生成する。

    Geminiの構造化出力はList[str]やネストクラスでフィールド欠落が起きやすいため、
    各段とも全フィールドをstrに平坦化したスキーマで呼び出す。
    パース後に元のネスト構造へ組み直して返す。
    """
    # ---- Stage 1: 分析（フラット12フィールド） ----
    if progress_cb:
        progress_cb("Stage 1/2: 商品プロファイリング＆レビュー分析中...")

    stage1_prompt = f"""
【商品情報】
- ジャンル: {genre}
- 文章トーン: {tone}
- 狙いSEOキーワード: {seo_kw if seo_kw else "（未入力：文脈から自動抽出）"}

【入力データ】
1. 現在の商品説明: {base}
2. 自社の強み・USP: {usp if usp else "（未入力：既存文から抽出）"}
3. スペック・仕様: {spec}
4. カスタマーレビュー: {review}

【指示】
以下の**JSON出力例**と同じ構造で、12フィールドすべてをトップレベルに埋めたJSONを返してください。
Markdownコードフェンス禁止・ネスト構造禁止・メタコメント禁止。
各フィールドは実質的な内容だけを書くこと（「調整しました」等の作業コメントを含めない）。

【重要】文字数の目安に到達しなくても、実質的な内容を書き切ったらその時点で
そのフィールドを完成させ、次のフィールドの生成に必ず進むこと。
長さを稼ぐための無意味な繰り返しや、ゼロ幅スペース・改行の水増しは絶対に禁止。
短くても内容がある方が、水増しした長文より遥かに価値がある。

【JSON出力例（この構造を厳密に守る。内容は実際の商品に合わせて書き換える）】
{{
  "selected_type": "総合",
  "type_reason": "機能性とデザイン性が両立しており、特定要素に偏らないバランスの良さから総合タイプと判定しました。",
  "extracted_usp": "他社にない独自の素材と製法により、耐久性と美観を高次元で両立している点が最大の差別化ポイントです。",
  "target_persona": "30代の女性で、日常使いのアイテムに品質と見た目の両方を求める層。SNSで情報収集する傾向がある。",
  "key_seo_keywords_csv": "主要キーワード1,主要キーワード2,関連語1,関連語2,関連語3,シーン語1,シーン語2",
  "identified_pain_point": "耐久性への不安と、写真と実物の色味の差異を心配する声が最も多い。",
  "pain_point_severity": "中",
  "pattern_a_text": "厳格な品質検査を経てお届け。素材本来の色合いを写真忠実に再現しており、実物との差はほぼありません。",
  "pattern_b_text": "モニター環境により多少の色味の差が出る可能性があります。気になる場合は30日以内であれば返品を承ります。",
  "pattern_c_text": "微細な色ムラは天然素材ならではの表情で、二つとして同じものがない一点物としてお楽しみいただけます。",
  "recommended_pattern": "B",
  "ai_recommendation": "誠実開示によって購入後のミスマッチを防ぎ、信頼獲得と長期的なブランド価値向上に繋がるパターンBを推奨します。"
}}

上記の**構造**を厳密に守り、内容は入力された商品情報に基づいて書き起こしてください。
生成順序: 1→2→3→...→12 と順に全フィールドを埋めきってから応答を終了すること。
"""
    stage1 = _call_gemini_api(
        api_key, model_name, stage1_prompt, system_instruction,
        temperature=temperature, thinking_budget=thinking_budget,
        response_schema=AnalysisSchemaFlat,
    )
    if "error" in stage1:
        return {"error": f"[Stage1エラー] {stage1['error']}",
                "raw": stage1.get("raw", ""),
                "_meta": stage1.get("_meta", {})}

    # ---- Stage 1 の欠落フィールド検証と自動リトライ ----
    stage1_required = [
        "selected_type", "type_reason", "extracted_usp", "target_persona",
        "key_seo_keywords_csv", "identified_pain_point", "pain_point_severity",
        "pattern_a_text", "pattern_b_text", "pattern_c_text",
        "recommended_pattern", "ai_recommendation",
    ]
    stage1_empty = [k for k in stage1_required if not stage1.get(k)]

    if stage1_empty and len(stage1_empty) > 2:
        # 大量に欠落している場合は自動リトライ
        if progress_cb:
            progress_cb(f"Stage 1 で {len(stage1_empty)} フィールド欠落を検出。強化プロンプトで自動リトライ中...")

        # 既に埋まったフィールドを提示し、欠落分だけを明示的に要求するプロンプトを作成
        already_filled = {k: stage1.get(k, "") for k in stage1_required if stage1.get(k)}
        empty_list = "\n".join([f"- {k}" for k in stage1_empty])
        retry_prompt = f"""
【リトライ要求】
前回の呼び出しで以下フィールドが未生成でした。既生成フィールドはそのまま維持し、
未生成フィールドを含めた12フィールド全てを埋めた完全なJSONを再度返してください。

【既に生成済みのフィールド】
{json.dumps(already_filled, ensure_ascii=False, indent=2)}

【今回必ず埋めるべき未生成フィールド】
{empty_list}

【元の入力データ】
- ジャンル: {genre}
- 現在の商品説明: {base[:500]}
- 自社USP: {usp[:300] if usp else "（未入力）"}
- スペック: {spec[:300]}
- レビュー: {review[:500]}
- 狙いSEOキーワード: {seo_kw if seo_kw else "（文脈から抽出）"}

Markdownコードフェンス禁止、メタコメント禁止、改行パディング禁止、ネスト構造禁止。
12フィールドすべてトップレベルに配置したJSONのみを返してください。
"""
        stage1_retry = _call_gemini_api(
            api_key, model_name, retry_prompt, system_instruction,
            temperature=temperature, thinking_budget=thinking_budget,
            response_schema=AnalysisSchemaFlat,
        )
        if "error" not in stage1_retry:
            # 欠落分を埋める（リトライ側で得られた値を優先）
            for k in stage1_empty:
                v = stage1_retry.get(k)
                if v:
                    stage1[k] = v
            stage1_empty_after = [k for k in stage1_required if not stage1.get(k)]
            if progress_cb:
                if stage1_empty_after:
                    progress_cb(f"リトライ後もなお {len(stage1_empty_after)} フィールド欠落。処理を継続します...")
                else:
                    progress_cb("✅ リトライで全フィールド生成完了")

    # ---- 埋め込みJSON救出を試行 ----
    # AI がフラットスキーマを無視して type_reason などにネスト JSON を詰め込む挙動への対処。
    # 埋め込みJSONに全4ブロックが含まれていれば、Stage 2をスキップして即返す。
    buried = _try_recover_from_buried_json(stage1)
    if buried:
        pp_b = buried.get("product_profile")
        nra_b = buried.get("negative_review_analysis")
        amz_b = buried.get("amazon_output")
        rak_b = buried.get("rakuten_output")

        # key_seo_keywords が str の場合は List に変換
        if pp_b and isinstance(pp_b.get("key_seo_keywords"), str):
            pp_b["key_seo_keywords"] = [
                k.strip() for k in pp_b["key_seo_keywords"].split(",") if k.strip()
            ]

        # 全4ブロックが揃っていれば Stage 2 をスキップして即返す
        if pp_b and nra_b and amz_b and rak_b:
            if progress_cb:
                progress_cb("✅ 埋め込みJSONを検出。Stage 2をスキップして復元しました。")
            m1 = stage1.get("_meta", {}) or {}
            return {
                "product_profile": pp_b,
                "negative_review_analysis": nra_b,
                "amazon_output": amz_b,
                "rakuten_output": rak_b,
                "_meta": {
                    "usage": m1.get("usage"),
                    "finish_reason": f"stage1={m1.get('finish_reason', 'N/A')} (recovered from buried JSON)",
                    "model": model_name,
                    "thinking_budget": thinking_budget,
                    "recovered": True,
                },
                "_raw_stage1": {k: v for k, v in stage1.items() if not k.startswith("_")},
                "_buried_json_full": buried,
            }
        # 部分的にでも救出できたら、それを Stage 1 の結果として採用
        pp = pp_b or _unflatten_analysis(stage1)["product_profile"]
        nra = nra_b or _unflatten_analysis(stage1)["negative_review_analysis"]
    else:
        # 通常のフラット→ネスト変換
        stage1_nested = _unflatten_analysis(stage1)
        pp = stage1_nested["product_profile"]
        nra = stage1_nested["negative_review_analysis"]

    # ---- Stage 2: 成果物（フラット22フィールド） ----
    if progress_cb:
        progress_cb("Stage 2/2: Amazon＆楽天テキスト生成中...")

    recommended = str(nra.get("recommended_pattern", "b")).lower()
    recommended_text = nra.get(f"pattern_{recommended}_text", "")

    stage2_prompt = f"""
【商品情報】
- ジャンル: {genre}
- 文章トーン: {tone}
- 狙いSEOキーワード: {seo_kw if seo_kw else "（Stage1のkey_seo_keywordsを活用）"}

【入力データ】
1. 現在の商品説明: {base}
2. 自社の強み・USP: {usp if usp else "（未入力）"}
3. スペック・仕様: {spec}
4. カスタマーレビュー: {review}

【Stage1で確定済みの分析結果（前提として使用）】
- 商品タイプ: {pp.get('selected_type', '')}
- 抽出USP: {pp.get('extracted_usp', '')}
- ターゲット像: {pp.get('target_persona', '')}
- 展開SEOキーワード: {', '.join(pp.get('key_seo_keywords', []) or [])}
- 最大の不安点: {nra.get('identified_pain_point', '')}
- 推奨パターン: {nra.get('recommended_pattern', '')}
- 推奨パターン本文: {recommended_text}

【指示】
以下22フィールドを全て埋めた JSON を出力してください。1フィールドも省略・空文字禁止。

# Amazon系
1. amz_title: 商品名（50〜75文字、絶対上限75文字）
2. amz_product_highlights: 商品ハイライト（カンマ区切り7〜15個）
   ★★★ 最重要ルール ★★★
   amz_title に既に含まれているキーワードは絶対に含めないこと。
   両フィールドの検索カバレッジを最大化するため、商品名で使わなかった
   別カテゴリの検索語（同義語・関連語・別シーン語・別ペルソナ語など）だけを配置する。
   生成手順: (1)先にamz_titleを完成させる → (2)titleの各語をリストアップ →
   (3)そのリストに含まれない語だけでhighlightsを組み立てる。
   例: title「iikuru ぬいポーチ 15cm 2体収納 PUレザー ショルダーバッグ」
       → highlightsで使ってよい語: 痛バッグ, ぬい活, ディスプレイケース, 自立, 見せる収納, ポケモンfit対応 等
       → highlightsで禁止の語: ぬいポーチ, 15cm, 2体収納, PUレザー, ショルダーバッグ（全てtitleに既出）
3-12. amz_bullet_1_theme, amz_bullet_1_body, ..., amz_bullet_5_theme, amz_bullet_5_body:
     箇条書き5本のテーマと本文。テーマは重複禁止。本文は各80〜120文字。
13. amz_description: 商品説明文（500〜800文字）
14-18. amz_qa_1〜5: Rufus想定Q&A。『Q: 質問 / A: 回答』形式

# 楽天系
19. rak_catchcopy: キャッチコピー（60〜120文字、絶対上限127）
20. rak_desc_text: テキスト説明文（300〜600文字）
21. rak_desc_html: HTML説明文（h3見出し3〜5個、ulリスト、strong強調）
22. rak_search_kw: 検索キーワード欄（半角スペース区切り10〜30個）

推奨パターン本文（{recommended_text[:80]}...）を各説明文の中に適切に織り込むこと。
"""
    stage2 = _call_gemini_api(
        api_key, model_name, stage2_prompt, system_instruction,
        temperature=temperature, thinking_budget=thinking_budget,
        response_schema=ContentSchemaFlat,
    )
    if "error" in stage2:
        return {"error": f"[Stage2エラー] {stage2['error']}",
                "raw": stage2.get("raw", ""),
                "_meta": stage2.get("_meta", {}),
                "product_profile": pp,
                "negative_review_analysis": nra}

    # フラット→ネスト変換
    stage2_nested = _unflatten_content(stage2)

    # 診断メタ情報を合算
    meta1 = stage1.get("_meta", {}) or {}
    meta2 = stage2.get("_meta", {}) or {}
    u1 = meta1.get("usage") or {}
    u2 = meta2.get("usage") or {}
    def _add(a, b):
        if a is None and b is None: return None
        return (a or 0) + (b or 0)
    combined_usage = {
        "prompt_tokens": _add(u1.get("prompt_tokens"), u2.get("prompt_tokens")),
        "output_tokens": _add(u1.get("output_tokens"), u2.get("output_tokens")),
        "thoughts_tokens": _add(u1.get("thoughts_tokens"), u2.get("thoughts_tokens")),
        "total_tokens": _add(u1.get("total_tokens"), u2.get("total_tokens")),
    }

    return {
        "product_profile": pp,
        "negative_review_analysis": nra,
        "amazon_output": stage2_nested["amazon_output"],
        "rakuten_output": stage2_nested["rakuten_output"],
        "_meta": {
            "usage": combined_usage,
            "finish_reason": f"stage1={meta1.get('finish_reason', 'N/A')}, stage2={meta2.get('finish_reason', 'N/A')}",
            "model": model_name,
            "thinking_budget": thinking_budget,
            "two_stage": True,
            "flat_schema": True,
        },
        # デバッグ用: 生のフラットレスポンスを保持
        "_raw_stage1": {k: v for k, v in stage1.items() if not k.startswith("_")},
        "_raw_stage2": {k: v for k, v in stage2.items() if not k.startswith("_")},
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

def _normalize_kw(s: str) -> str:
    """比較用のキーワード正規化。全角半角統一・大文字小文字統一・空白除去。"""
    if not s:
        return ""
    s = s.strip().lower()
    # 全角英数を半角に
    s = s.translate(str.maketrans(
        "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ",
        "0123456789abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz"
    ))
    # 空白・記号を除去
    s = re.sub(r"[\s\u3000・･]+", "", s)
    return s

def _find_title_highlight_duplicates(title: str, highlights_csv: str) -> dict:
    """商品名とハイライトで重複するキーワードを検出。

    Returns:
        {
            "duplicated_kws": [重複したハイライトKW],
            "unique_kws": [重複していないハイライトKW],
            "filtered_csv": "重複除去後のCSV文字列"
        }
    """
    if not title or not highlights_csv:
        return {"duplicated_kws": [], "unique_kws": [], "filtered_csv": highlights_csv or ""}

    title_norm = _normalize_kw(title)
    kws = [k.strip() for k in highlights_csv.split(",") if k.strip()]

    duplicated = []
    unique = []
    for kw in kws:
        kw_norm = _normalize_kw(kw)
        # 完全一致 or タイトルに部分含有 のいずれかで重複扱い
        if kw_norm and (kw_norm in title_norm):
            duplicated.append(kw)
        else:
            unique.append(kw)
    return {
        "duplicated_kws": duplicated,
        "unique_kws": unique,
        "filtered_csv": ",".join(unique),
    }

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
def _check_schema_completeness(res: dict) -> list:
    """AIレスポンスの必須フィールドが揃っているかチェックし、欠落したフィールドのパスを返す。"""
    missing = []
    # product_profile
    pp = res.get("product_profile") or {}
    for k in ["selected_type", "type_reason", "extracted_usp", "target_persona", "key_seo_keywords"]:
        if not pp.get(k):
            missing.append(f"product_profile.{k}")
    # negative_review_analysis
    nra = res.get("negative_review_analysis") or {}
    for k in ["identified_pain_point", "pattern_a_text", "pattern_b_text", "pattern_c_text",
              "recommended_pattern", "ai_recommendation"]:
        if not nra.get(k):
            missing.append(f"negative_review_analysis.{k}")
    # amazon_output
    ao = res.get("amazon_output") or {}
    for k in ["title", "product_highlights", "description", "rufus_qa_pairs"]:
        if not ao.get(k):
            missing.append(f"amazon_output.{k}")
    for i in range(1, 6):
        b = ao.get(f"bullet_{i}")
        if not b or not (isinstance(b, dict) and b.get("body")):
            missing.append(f"amazon_output.bullet_{i}")
    # rakuten_output
    ro = res.get("rakuten_output") or {}
    for k in ["catchcopy", "desc_text", "desc_html", "search_keywords_field"]:
        if not ro.get(k):
            missing.append(f"rakuten_output.{k}")
    return missing

def _g(d, key, default="（未生成）"):
    """dictから安全に値を取得。dictでない値や欠落キーに対して default を返す。"""
    if not isinstance(d, dict):
        return default
    v = d.get(key)
    if v is None or v == "":
        return default
    return v

def render_profile_and_reviews(res: dict):
    st.header("🧠 AI分析 ＆ ネガティブレビュー対策")
    col1, col2 = st.columns([1, 1.3], gap="medium")

    with col1:
        st.subheader("📋 商品プロファイリング")
        p = res.get("product_profile") or {}
        st.markdown(f"**商品タイプ**：`{_g(p, 'selected_type')}`")
        st.markdown(f"**判定理由**：{_g(p, 'type_reason')}")
        st.markdown(f"**抽出USP**：{_g(p, 'extracted_usp')}")
        st.markdown(f"**ターゲット像**：{_g(p, 'target_persona')}")
        st.markdown("**展開SEOキーワード**：")
        kws = p.get("key_seo_keywords") or []
        if kws:
            st.write("　".join([f"`{kw}`" for kw in kws]))
        else:
            st.caption("（未生成）")

    with col2:
        st.subheader("💡 ネガティブ変換 3パターン")
        n = res.get("negative_review_analysis") or {}
        st.markdown(
            f"<div class='ai-box'>"
            f"<strong>🔎 最大の不安・不満点：</strong>{_g(n, 'identified_pain_point')}<br>"
            f"<strong>⚠️ 深刻度：</strong>{_g(n, 'pain_point_severity')}<br>"
            f"<strong>🤖 推奨パターン：</strong>{_g(n, 'recommended_pattern')}<br>"
            f"<strong>💬 推奨理由：</strong>{_g(n, 'ai_recommendation')}"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.text_area("パターンA（利点強調）", value=_g(n, "pattern_a_text", ""), height=90, key="pat_a")
        st.text_area("パターンB（誠実開示：Google SEO推奨）", value=_g(n, "pattern_b_text", ""), height=90, key="pat_b")
        st.text_area("パターンC（メリット変換）", value=_g(n, "pattern_c_text", ""), height=90, key="pat_c")
        st.caption("※必要に応じてコピーし、各モールの説明文へ手動統合してください。")

def render_amazon_tab(res: dict):
    a = res.get("amazon_output") or {}
    st.subheader("📤 Amazon 最適化テキスト")
    st.caption("価格・送料表現ゼロ、Rufusが引用しやすい構造を採用。2026年仕様（タイトル75字・商品ハイライト対応）。")

    if not a:
        st.warning("⚠️ Amazon成果物が生成されませんでした。思考予算を上げて再実行してください。")
        return

    # タイトル（75文字ハード上限）
    title = a.get("title", "")
    st.markdown("##### 商品名（タイトル）※75文字ハード上限")
    st.markdown(
        _char_badge(title, AMAZON_TITLE_TARGET, hard_max=AMAZON_TITLE_HARD_MAX),
        unsafe_allow_html=True,
    )
    st.text_area("Amazonタイトル", value=title, height=80,
                 key="amz_title", label_visibility="collapsed")
    if len(title) > AMAZON_TITLE_HARD_MAX:
        st.error(f"⚠️ タイトルが75文字を超えています（現在 {len(title)} 文字）。再生成または手動で削ってください。")

    # 商品のハイライト（2026新仕様・SEOに影響）
    st.markdown("##### 🆕 商品のハイライト（カンマ区切りキーワード）")
    st.caption(
        "Amazon 2026年アップデートで検索SEOに直接影響。"
        "商品名(title)と重複するキーワードは含めず、両フィールドで検索カバレッジを最大化します。"
    )
    highlights = a.get("product_highlights", "") or ""
    kw_list = [k.strip() for k in highlights.split(",") if k.strip()]

    # 商品名との重複を検出
    dup_result = _find_title_highlight_duplicates(title, highlights)
    duplicated = dup_result["duplicated_kws"]
    unique = dup_result["unique_kws"]

    # 個数バッジ（有効KW数を目標比較の対象にする）
    st.markdown(
        _char_badge_count(unique, AMAZON_HIGHLIGHT_KW_TARGET)
        + (f'<span class="count-badge badge-ng">重複{len(duplicated)}個</span>' if duplicated else ""),
        unsafe_allow_html=True,
    )

    # 重複警告
    if duplicated:
        st.error(
            f"⚠️ 商品名と重複するキーワードが {len(duplicated)} 個含まれています "
            f"（有効な独自キーワードは {len(unique)} 個のみ）。"
            "重複キーワードは Amazon SEO のインデックス枠を無駄にするため、"
            "下記『重複除去済み』の版を使うことを推奨します。"
        )

    # 元のハイライト（AI生成のまま）
    st.markdown("**AIが生成した原文（重複含む）**")
    st.text_area("Amazon商品ハイライト_原文", value=highlights, height=80,
                 key="amz_highlights_raw", label_visibility="collapsed")

    # タグ表示：重複=赤、独自=緑
    if kw_list:
        tags_html = []
        for kw in kw_list:
            if kw in duplicated:
                tags_html.append(
                    f'<span class="theme-tag" style="background:#dc2626;">'
                    f'❌ {kw}<span style="opacity:0.7;font-size:0.7em;"> (title重複)</span></span>'
                )
            else:
                tags_html.append(
                    f'<span class="theme-tag" style="background:#16a34a;">✓ {kw}</span>'
                )
        st.markdown(" ".join(tags_html), unsafe_allow_html=True)

    # 重複除去版
    if duplicated:
        st.markdown("**✂️ 重複除去済み版（推奨・そのまま入稿可）**")
        st.text_area("Amazon商品ハイライト_重複除去",
                     value=dup_result["filtered_csv"], height=80,
                     key="amz_highlights_filtered", label_visibility="collapsed")
        if len(unique) < AMAZON_HIGHLIGHT_KW_TARGET[0]:
            st.warning(
                f"⚠️ 重複除去後は {len(unique)} 個のみ（目標 {AMAZON_HIGHLIGHT_KW_TARGET[0]} 個以上）。"
                "手動でキーワードを補うか、思考予算を上げて再生成することをおすすめします。"
            )

    # 箇条書き
    st.markdown("##### 箇条書き（5本）")
    for i in range(1, 6):
        b = a.get(f"bullet_{i}") or {}
        theme = b.get("theme", "") if isinstance(b, dict) else ""
        body = b.get("body", "") if isinstance(b, dict) else ""
        st.markdown(
            f'<span class="theme-tag">テーマ: {theme or "（未生成）"}</span>'
            f'{_char_badge(body, AMAZON_BULLET_TARGET)}',
            unsafe_allow_html=True,
        )
        st.text_area(f"bullet_{i}", value=body, height=90,
                     key=f"amz_b_{i}", label_visibility="collapsed")

    # 商品説明
    desc = a.get("description", "") or ""
    st.markdown("##### 商品説明文")
    st.markdown(_char_badge(desc, AMAZON_DESC_TARGET), unsafe_allow_html=True)
    st.text_area("Amazon説明文", value=desc, height=220,
                 key="amz_desc", label_visibility="collapsed")

    # Rufus Q&A
    st.markdown("##### Rufus想定Q&A（5個）")
    st.caption("Rufusが自然文の質問に対して抽出しやすいQ&Aペア。")
    qa_list = a.get("rufus_qa_pairs") or []
    if not qa_list:
        st.caption("（未生成）")
    for i, qa in enumerate(qa_list, 1):
        st.text_area(f"Q&A {i}", value=str(qa), height=70,
                     key=f"amz_qa_{i}", label_visibility="collapsed")

def render_rakuten_tab(res: dict):
    r = res.get("rakuten_output") or {}
    st.subheader("📤 楽天市場 最適化テキスト")
    st.caption("スマホCVR最適化 & 楽天AI検索対策。")

    if not r:
        st.warning("⚠️ 楽天成果物が生成されませんでした。思考予算を上げて再実行してください。")
        return

    catchcopy = r.get("catchcopy", "") or ""
    st.markdown("##### キャッチコピー")
    st.markdown(
        _char_badge(catchcopy, RAKUTEN_CATCH_TARGET, hard_max=RAKUTEN_CATCH_HARD_MAX),
        unsafe_allow_html=True,
    )
    st.text_area("楽天キャッチ", value=catchcopy, height=80,
                 key="rak_catch", label_visibility="collapsed")

    desc_text = r.get("desc_text", "") or ""
    st.markdown("##### 商品説明文（テキスト版）")
    st.markdown(_char_badge(desc_text, RAKUTEN_TEXT_TARGET), unsafe_allow_html=True)
    st.text_area("楽天テキスト", value=desc_text, height=180,
                 key="rak_text", label_visibility="collapsed")

    desc_html = r.get("desc_html", "") or ""
    st.markdown("##### 商品説明文（HTML版）")
    st.text_area("楽天HTML", value=desc_html, height=260,
                 key="rak_html", label_visibility="collapsed")

    if desc_html:
        with st.expander("👁️ HTMLプレビュー"):
            st.markdown(desc_html, unsafe_allow_html=True)

    kw_field = r.get("search_keywords_field", "") or ""
    st.markdown("##### 検索キーワード欄（RMS入稿用）")
    st.text_area("楽天KW欄", value=kw_field, height=80,
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
            min_value=512, max_value=8192, value=2048, step=256,
            help=(
                "2段階生成モードでは各段2048で十分安定します。"
                "本文が短いと感じたら1024〜1536に下げ、"
                "特定フィールドが欠落する場合は3072〜4096に上げてください。"
            ),
        )
        two_stage = st.checkbox(
            "🔀 2段階生成（推奨・安定性重視）",
            value=True,
            help=(
                "ON: 分析→成果物 の2回に分けてAPIを呼び出します。"
                "スキーマ複雑度が半分になるためフィールド欠落を防げます。"
                "OFF: 1回で全部生成します（速いが複雑スキーマで欠落しやすい）。"
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
            sys_inst = build_system_instruction(TONE_MAPPING[tone])
            status_placeholder = st.empty()

            if two_stage:
                # 2段階生成
                def _progress(msg):
                    status_placeholder.info(f"🔄 {msg}")

                _progress("Stage 1/2: 商品プロファイリング＆レビュー分析中...")
                res = _call_gemini_two_stage(
                    api_key=api_key,
                    model_name=model_name,
                    system_instruction=sys_inst,
                    genre=genre, tone=tone, seo_kw=c_seo,
                    base=c_base, usp=c_usp, spec=c_spec, review=c_review,
                    temperature=temperature,
                    thinking_budget=thinking_budget,
                    progress_cb=_progress,
                )
                status_placeholder.empty()
            else:
                # 1段階生成（従来）
                with st.spinner("プロのECコンサルタントAIが思考中..."):
                    user_prompt = _build_user_prompt(genre, tone, c_seo, c_base, c_usp, c_spec, c_review)
                    res = _call_gemini_api(
                        api_key, model_name, user_prompt, sys_inst,
                        temperature=temperature,
                        thinking_budget=thinking_budget,
                        response_schema=EcomUpdateSchema,
                    )

            if "error" in res:
                st.error(f"APIエラー：{res['error']}")
                st.info("モデル名を切り替える／temperature を下げる／入力を短くする、などをお試しください。")
                if res.get("raw"):
                    with st.expander("🔍 AIの生レスポンス（先頭2000文字・デバッグ用）"):
                        st.code(res["raw"], language="json")
                # Stage2失敗でもStage1の結果は表示できるように残す
                if res.get("product_profile"):
                    st.info("Stage1（分析）は成功しています。下部にStage1の結果のみ表示します。")
                    st.session_state["ecom_result"] = res
            else:
                st.session_state["ecom_result"] = res
                # 復元モードの明示
                if res.get("_meta", {}).get("recovered"):
                    st.success(
                        "生成が完了しました。"
                        "（AIレスポンスに埋め込まれた完全JSONを検出したため、Stage 2をスキップして復元しました）"
                    )
                else:
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

                # スキーマ完全性チェック（構造化出力失敗の検出）
                missing = _check_schema_completeness(res)
                if missing:
                    st.warning(
                        f"⚠️ 一部フィールドが未生成です: {', '.join(missing[:8])}"
                        + ("..." if len(missing) > 8 else "")
                        + "。 下部『AIの生レスポンス（フラット）』を開いて実際に何が返っているか確認してください。"
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

        # AIの生レスポンス（フラット構造の生JSON）- 診断に必須
        raw1 = res.get("_raw_stage1")
        raw2 = res.get("_raw_stage2")
        if raw1 or raw2:
            with st.expander("🔬 AIの生レスポンス（フラット構造・欠落診断用）", expanded=False):
                if raw1:
                    st.markdown("**Stage 1（分析）フラット出力：**")
                    st.json(raw1)
                if raw2:
                    st.markdown("**Stage 2（成果物）フラット出力：**")
                    st.json(raw2)
                st.caption(
                    "各フィールドがフラットな str として返されているかここで確認できます。"
                    "空文字や欠落のフィールドがあれば、それが構造化出力失敗の証跡です。"
                )

        with st.expander("🧾 変換後JSON（デバッグ用）"):
            st.json(res)


if __name__ == "__main__":
    main()
