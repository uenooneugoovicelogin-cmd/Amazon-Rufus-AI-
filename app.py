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
import csv
from io import StringIO
from datetime import datetime

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
AMAZON_SEARCH_KW_BYTE_LIMIT = 500    # Amazon 検索キーワード欄：500バイト上限（半角=1B, 全角=3B目安）
AMAZON_SEARCH_KW_TARGET = (15, 40)   # 検索キーワード欄：目安KW個数
RAKUTEN_CATCH_TARGET = (60, 120)
RAKUTEN_CATCH_HARD_MAX = 127         # スマホ表示ハード上限（超過で見切れ）
RAKUTEN_TITLE_TARGET = (60, 127)     # 楽天商品タイトル：60〜127文字
RAKUTEN_TITLE_HARD_MAX = 127         # 楽天タイトル絶対上限
RAKUTEN_TEXT_TARGET = (300, 600)
RAKUTEN_ATTR_KW_TARGET = (5, 15)     # 楽天推奨属性キーワード数

# 楽天HTMLで使用可能なタグ（スマホ・PC両対応）
RAKUTEN_HTML_ALLOWED_TAGS = ["h3", "h4", "h5", "p", "br", "ul", "ol", "li", "strong", "b", "em", "i"]
# 楽天HTMLで禁止のタグ（保存不可・表示崩れ・スマホNG）
RAKUTEN_HTML_FORBIDDEN_TAGS = ["font", "style", "script", "iframe", "form", "link", "meta",
                                "base", "applet", "object", "embed", "param", "div", "span",
                                "h1", "h2", "img", "table", "tr", "td", "th"]

# 知的財産権リスク：Amazonで違反検知されやすい有名IP/ブランド/キャラクター名（一部）
# 完全網羅は不可能なため、AIに指示＋UIで代表例を検出する二段構え
IP_RISKY_KEYWORDS = [
    # 任天堂・ポケモン系
    "ポケモン", "ピカチュウ", "イーブイ", "ミュウ", "ミュウツー", "ライチュウ", "デデンネ",
    "ヌオー", "ヤドキング", "ヤドラン", "ゼニガメ", "フシギダネ", "ヒトカゲ", "リザードン",
    "マリオ", "ルイージ", "ヨッシー", "カービィ", "ゼルダ", "スプラトゥーン", "任天堂", "Nintendo",
    "スーパーマリオ", "どうぶつの森", "ポケモンfit", "ポケモンFit", "pokemonfit", "Pokemon fit",
    # サンリオ
    "ハローキティ", "サンリオ", "キティ", "マイメロディ", "シナモロール", "クロミ", "ポムポムプリン",
    "ぐでたま", "ポチャッコ", "けろけろけろっぴ",
    # ディズニー
    "ディズニー", "Disney", "ミッキー", "ミニー", "ドナルド", "デイジー", "プーさん",
    "アナ雪", "ピクサー", "トイストーリー", "アリエル",
    # サンエックス
    "リラックマ", "すみっコぐらし", "すみっこぐらし",
    # 集英社・少年ジャンプ
    "ワンピース", "ONE PIECE", "鬼滅の刃", "呪術廻戦", "ドラゴンボール", "進撃の巨人",
    "名探偵コナン", "スラムダンク", "ハイキュー", "ジョジョ", "NARUTO", "ナルト",
    # 講談社・その他
    "セーラームーン", "ドラえもん", "アンパンマン", "しまじろう", "プリキュア",
    # VTuber・キャラ
    "にじさんじ", "ホロライブ", "ちいかわ", "うさぎ", "ハチワレ", "モモンガ",
    # サブカル略称（商品名として使用されがちなもの）
    "ともぬい", "にじぬい", "ちびぬい", "もちころりん", "にじぱぺっと",
    # Apple関連
    "iPhone", "iPad", "AirPods", "MacBook", "Apple",
    # 高級ブランド
    "エルメス", "シャネル", "ルイヴィトン", "グッチ", "プラダ", "ロレックス", "カルティエ",
]

# 推奨モデル（現行）
AVAILABLE_MODELS = [
    "gemini-2.5-pro",        # 品質最優先（推奨）
    "gemini-2.5-flash",      # 速度・コスト重視
    "gemini-2.0-flash",      # 互換用
    "gemini-1.5-pro",        # レガシー
    "gemini-1.5-flash",      # レガシー
]

# Stage 0: レビュー消化（大量レビューを処理する場合の追加ステージ）
REVIEW_DIGEST_THRESHOLD = 3000       # この文字数を超えたらStage 0を起動
REVIEW_DIGEST_MODEL = "gemini-2.5-flash"  # Stage 0はコスト効率でFlashを使用

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

# Stage 1a: 商品プロファイル（5フィールドのみ・Geminiが確実に生成できる少なさ）
class ProfileSchemaFlat(BaseModel):
    """Stage 1a: 商品プロファイル生成のみに集中"""
    selected_type: str = Field(description="商品タイプ: 機能重視 / デザイン重視 / コスパ重視 / 総合 のいずれか")
    type_reason: str = Field(description="判定理由。1〜2文で簡潔に。")
    extracted_usp: str = Field(description="独自の強み・専門情報。2〜3文で。")
    target_persona: str = Field(description="主要ターゲット像（年齢・状況・購入動機）。1〜2文で。")
    key_seo_keywords_csv: str = Field(description="展開SEOキーワードをカンマ区切りで（例: 介護用クッション,体圧分散,通気性）")

# Stage 1b: ネガティブレビュー分析（7フィールドのみ）
class NegativeAnalysisSchemaFlat(BaseModel):
    """Stage 1b: ネガティブレビュー変換3パターンの分析のみ"""
    identified_pain_point: str = Field(description="最大の不安・不満点。1文で。")
    pain_point_severity: str = Field(description="深刻度: 高 / 中 / 低 のいずれか")
    pattern_a_text: str = Field(description="パターンA（利点強調）の文章。")
    pattern_b_text: str = Field(description="パターンB（誠実開示）の文章。")
    pattern_c_text: str = Field(description="パターンC（メリット変換）の文章。")
    recommended_pattern: str = Field(description="推奨パターン: A / B / C のいずれか1文字")
    ai_recommendation: str = Field(description="推奨理由。2〜3文で。")

# Stage 0: 大量レビューを Flash モデルでダイジェスト化するためのスキーマ
class ReviewDigestSchema(BaseModel):
    """Stage 0: 大量レビューを消化して構造化ダイジェストを作成"""
    top_negative_themes: str = Field(description="頻出ネガティブテーマをカンマ区切りで3〜5個。例: サイズ違い,汚れやすい,梱包が雑")
    top_positive_themes: str = Field(description="頻出ポジティブテーマをカンマ区切りで3〜5個。例: しっかりした作り,可愛い,コスパ良い")
    main_pain_point: str = Field(description="最も頻出する不満・不安を1文で。ネガティブレビューの本質")
    representative_negative_quote: str = Field(description="代表的なネガティブレビュー引用（短く、原文の言い回しを保持）")
    representative_positive_quote: str = Field(description="代表的なポジティブレビュー引用（短く、原文の言い回しを保持）")
    emerging_keywords: str = Field(description="レビューに頻出するが商品説明にはあまり出てこない語句をカンマ区切りで5〜10個。SEO発掘対象。")
    usage_scenes: str = Field(description="レビューから読み取れる主な使用シーンをカンマ区切りで3〜5個")
    target_users: str = Field(description="レビューから読み取れる主な購入者層をカンマ区切りで2〜4個")
    overall_sentiment: str = Field(description="全体的な評価傾向。ポジ多め/中立/ネガ多め のいずれか + 一言")
    review_count_processed: str = Field(description="実際に読み込んだレビューの推定件数（例: 250件）")

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
    amz_search_keywords: str = Field(description="Amazon検索キーワード欄。半角スペース区切りで500バイト以内。【最重要】amz_titleとamz_product_highlightsに含まれるキーワードは絶対に含めない（Amazon SEO重複排除ルール）。同義語・関連語・別シーン語で構成する。")
    # 楽天
    rak_title: str = Field(description="楽天商品タイトル。60〜127文字（絶対上限127）。SEO主要KWを冒頭に配置。ブランド名→主要KW→スペック→用途の順。")
    rak_catchcopy: str = Field(description="楽天キャッチコピー60〜120文字（絶対上限127）")
    rak_desc_text: str = Field(description="楽天テキスト説明300〜600文字")
    rak_desc_html: str = Field(description="楽天HTML説明。使用可能タグは h3/h4/h5/p/br/ul/ol/li/strong/b/em/i のみ。font/style/script/iframe/div/span/h1/h2/img/table/インラインstyle属性は絶対禁止（スマホで保存不可）。色装飾は使わず見出しとstrong強調のみで視覚設計する。")
    rak_attributes: str = Field(description="楽天推奨属性キーワード。カンマ区切りで、以下のカテゴリを含める：カラー・サイズ・素材・ブランド・キャラクター(該当あれば)・対象年齢・使用シーン。例: カラー:ホワイト,サイズ:15×21×9cm,素材:PUレザー,ブランド:iikuru,対象:大人女性,シーン:推し活")
    rak_color_palette: str = Field(description="""楽天RMSエディタで色装飾を手動適用する際の推奨カラーパレット提案。以下の固定フォーマットで返す（改行区切り）:
メインカラー: #XXXXXX | 用途と理由
サブカラー: #XXXXXX | 用途と理由
アクセントカラー: #XXXXXX | 用途と理由
背景色: #XXXXXX | 用途と理由
配色戦略: 商品ジャンル・ターゲット・購買心理を踏まえた戦略説明
※HTML本体には色は含めず、あくまで参考情報として提示。""")

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
        "search_keywords": flat.get("amz_search_keywords", ""),
    }
    for i in range(1, 6):
        amazon[f"bullet_{i}"] = {
            "theme": flat.get(f"amz_bullet_{i}_theme", ""),
            "body": flat.get(f"amz_bullet_{i}_body", ""),
        }
    rakuten = {
        "title": flat.get("rak_title", ""),
        "catchcopy": flat.get("rak_catchcopy", ""),
        "desc_text": flat.get("rak_desc_text", ""),
        "desc_html": flat.get("rak_desc_html", ""),
        "attributes": flat.get("rak_attributes", ""),
        "color_palette": flat.get("rak_color_palette", ""),
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
- 【最重要】以下の「構造化出力の内部識別子」は絶対にテキスト値として出力しないこと。
  これらは出力すべきコンテンツではなく、システム内部の識別子である：
  ・json_start / json_end / json_content / json_body
  ・response_start / response_end / response_content
  ・output_start / output_end / content_start / content_end
  ・schema_start / schema_end / field_start / field_end
  上記の識別子が万一頭に浮かんでも、それは出力してはならない。ユーザー向けの日本語コンテンツだけを書くこと。
- 【最重要】同じ単語・フレーズを連続して繰り返さないこと。
  「A A A A A」「AB AB AB AB」のような反復パターンは絶対に生成しない。
  もしそのような反復が始まりそうになったら、直ちに別の内容に切り替えるか、そのフィールドの生成を打ち切って次のフィールドに移ること。
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

# 【★最重要 Amazon 商品名(amz_title)・商品ハイライト(amz_product_highlights)・検索キーワード(amz_search_keywords) 3フィールド重複禁止ルール】
- この3フィールドは Amazon 検索アルゴリズムでそれぞれ独立してインデックスされるため、
  複数のフィールドで同じキーワードを使うことはSEO上「インデックス枠の無駄遣い」となり、
  検索カバレッジを大きく損なう最大のアンチパターンである。
- ルール: 3フィールド間で同じキーワードは絶対に重複させない。各フィールドは互いに補完する異なる検索語で構成する。
- 具体例:
  ・NG: title「ぬいポーチ 15cm PUレザー」 highlights「ぬいポーチ,15cm,PUレザー」 search_kw「ぬいポーチ 15cm」
    → 全て重複でSEO無効
  ・OK: title「ぬいポーチ 15cm PUレザー」 highlights「痛バッグ,ディスプレイケース,自立」 search_kw「見せる収納 大人向け 韓国風」
    → 3フィールドすべて補完関係で検索カバレッジ最大化
- 生成手順（厳守）:
  Step1. amz_title を先に確定させる（主要検索KWを配置）
  Step2. title の各キーワードをリストアップして記憶する（リストA）
  Step3. amz_product_highlights は リストA に含まれない語だけで構成する（リストBを構築）
  Step4. amz_search_keywords は リストA + リストB のいずれにも含まれない語だけで構成する
- 表記ゆれも重複扱いとする（例: 「15cm」と「15センチ」、「PUレザー」と「PUL」など）。
- amz_search_keywords は500バイト以内（半角スペース区切り、半角英数=1B・全角=約3B）。

# 【★最重要 楽天HTML説明文(rak_desc_html)の使用可能タグ制限（スマホ保存対応）】
- 楽天RMSのスマホ版商品説明文には厳しいタグ制限があり、以下を厳守しないと保存できない。
- 【使用可能タグ（このリスト以外は絶対禁止）】:
  <h3>, <h4>, <h5>, <p>, <br>, <ul>, <ol>, <li>, <strong>, <b>, <em>, <i>
- 【使用禁止タグ】:
  <font>, <style>, <script>, <iframe>, <form>, <link>, <meta>, <base>, <applet>,
  <object>, <embed>, <param>, <div>, <span>, <h1>, <h2>, <img>, <table>, <tr>, <td>, <th>
- 【禁止属性】: すべてのタグの style="..." インラインCSS属性、class属性、id属性、onclick等のイベント属性
- 【禁止事項】: 色装飾（<font color=...> や style="color:..." など）は一切使用しない。
  視覚設計は「見出し(h3)、リスト(ul li)、強調(strong)」のみで構成すること。
- 出力例（正しい）:
  <h3>製品の特徴</h3>
  <p>大切なぬいぐるみを美しく守る、上質な素材を採用しました。</p>
  <ul>
  <li><strong>厚さ9cmのマチ</strong>で余裕の収納力</li>
  <li>丁寧な縫製で長く使える耐久性</li>
  </ul>
- rak_desc_html はPCとスマホの両方で問題なく表示・保存できるHTMLである必要がある。

# 【楽天商品タイトル(rak_title)の【】配置ルール】
- 【】(隅付きカッコ) の使用は視認性を大きく上げるため、SEOだけでなくCVR向上にも重要。
- 配置ルール（厳守）:
  ・「訴求性の高い要素」（送料無料、ランキング入賞、期間限定、○○対応、大人気 等）は
    **必ずタイトル先頭に**【】で配置。ユーザーの目を最初に引く役割。
  ・「補足属性」（サイズ、カラー、素材、対象年齢、キャラクター名 等）は
    **タイトル末尾に**【】で配置。詳細情報として補完する役割。
  ・【】は1タイトルあたり最大2箇所まで（先頭1つ、末尾1つ）。3つ以上は視認性を損なう。
  ・訴求性の高い要素が無い場合は先頭の【】は省略してよい。
- 良い例: 【送料無料】厚手PUレザー ぬいポーチ 2WAY 大人向け【15cmサイズ対応】
- 悪い例（不要な多用）: 【新作】【送料無料】ぬいポーチ【PUレザー】【15cm】【推し活】

# 【楽天カラーパレット(rak_color_palette)の提案ルール】
- rak_desc_html には色装飾を含めない（スマホ規約準拠のため）。
- しかし楽天RMSエディタでは店舗運営者が手動で色装飾を追加できるため、
  rak_color_palette フィールドで推奨配色を提案する。
- ジャンル別の推奨配色戦略:
  ・推し活・ホビー: ビビッドな色（ピンク #FF6B9D、パープル #9C27B0、イエロー #FFC107）
    → 感情を喚起、SNS映え、購買意欲刺激
  ・介護・看護: 落ち着いた色（ソフトブルー #4A90E2、ミントグリーン #7FBDA5、ベージュ #F5E6D3）
    → 信頼感、安心感、清潔感
  ・ベビー: パステルカラー（薄ピンク #FFD1DC、ベビーブルー #B0E0E6、クリーム #FFF8DC）
    → 優しさ、安全性、可愛らしさ
  ・スポーツ: 力強い色（レッド #D32F2F、ブラック #212121、ネオングリーン #00E676）
    → エネルギー、勝負感、モチベーション
  ・ペット: 温かい色（オレンジ #FF9800、ブラウン #6D4C41、クリーム #FFECB3）
    → 愛らしさ、親しみ、家庭的
  ・園芸: 自然色（グリーン #4CAF50、アーステラコッタ #A0522D、スカイブルー #87CEEB）
    → 自然、成長、癒し
  ・季節行事（ハロウィン等）: 季節色（オレンジ #FF6F00、パープル #6A1B9A、ブラック #212121）
    → 期間限定感、テーマ性
  ・一般雑貨: 中立で信頼できる色（ネイビー #1565C0、グレー #616161、白 #FAFAFA）
    → 汎用性、上品さ、読みやすさ
- 常に4色（メイン・サブ・アクセント・背景）とその戦略を明示。ジャンル + ターゲット層に合わせて調整。
- ターゲットが「読みやすさ重視」の場合は、背景の白ベースにダーク系メインカラー。
- ターゲットが「購買欲刺激重視」の場合は、暖色系（赤・オレンジ・ピンク）を活用。

# 【★最重要 知的財産権リスク回避】
- 商品名・キャッチコピー・説明文・キーワード欄・箇条書き・Q&A・その他すべてのフィールドで、
  他社が権利を持つブランド名・キャラクター名・作品名を絶対に使用しない。
- 【使用禁止の代表例（これらを含めた場合Amazon違反検知される可能性が高い）】:
  ・任天堂: ポケモン、ピカチュウ、イーブイ、ライチュウ、ヌオー、ヤドキング、デデンネ、ミュウ、
    ゼニガメ、フシギダネ、ヒトカゲ、リザードン、マリオ、ルイージ、ヨッシー、カービィ、ゼルダ、
    スーパーマリオ、ポケモンfit、Pokemon fit、Nintendo
  ・サンリオ: ハローキティ、キティ、マイメロディ、シナモロール、クロミ、ポムポムプリン、ぐでたま
  ・ディズニー・ピクサー: Disney、ディズニー、ミッキー、ミニー、ドナルド、プーさん、アナ雪、
    トイストーリー、ピクサー
  ・サンエックス: リラックマ、すみっコぐらし
  ・少年ジャンプ: ワンピース、ONE PIECE、鬼滅の刃、呪術廻戦、ドラゴンボール、進撃の巨人、
    NARUTO、ジョジョ、ハイキュー
  ・その他IP: ドラえもん、アンパンマン、しまじろう、プリキュア、名探偵コナン、セーラームーン
  ・VTuber: にじさんじ、ホロライブ、ちいかわ、ハチワレ、うさぎ（ちいかわ）
  ・略称/俗称: ともぬい、にじぬい、ちびぬい、もちころりん、にじぱぺっと
    （これらは他社IPの商品カテゴリ名・略称であり使用不可）
  ・Apple: iPhone、iPad、AirPods、Apple、MacBook
  ・高級ブランド: エルメス、シャネル、ルイヴィトン、グッチ、プラダ、ロレックス
- 【代替表現の作り方】:
  ・特定キャラ名の代わりに → 「お気に入りのキャラクター」「大切なぬいぐるみ」「推しの人形」
  ・特定シリーズ名の代わりに → 「15cmサイズのぬいぐるみ」「ボリュームのあるぬいぐるみ」
  ・他社ブランド名の代わりに → 「一般的な○○」「他社製品」（比較表現も控えめに）
- 疑わしい場合は使わない。一般名詞（ぬいぐるみ、ポーチ、バッグ等）は問題なし。

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
    - 末尾の記号ゴミ（\\n\\n- \\n\\n"\\n" のような箇条書きモドキ）

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
    # 繰り返しループを検出・除去
    text = _strip_repetition_loop(text)
    # 末尾の記号ゴミを除去
    text = _strip_trailing_garbage(text)
    # 末尾の空白・改行を除去
    return text.strip()

def _strip_trailing_garbage(text: str) -> str:
    """末尾の記号ゴミ（意味のない記号・改行・引用符の連続）を除去する。

    Gemini 2.5 Pro は稀に、実質的な文章を書き終えた後に
    「\\n\\n- \\n\\n\"\\n \"\\n\\n\"」のような箇条書きモドキの記号列を
    延々と生成する。この状態に入ると次のフィールドの生成に到達しなくなる。

    対策: 末尾の意味のある文の終わり（。！？）を探し、その後ろに
    「意味のない記号だけ」が続くならその部分を除去する。
    """
    if not text or not isinstance(text, str) or len(text) < 30:
        return text

    # 意味のある文字：日本語文字（漢字・ひらがな・カタカナ）、英字、数字
    meaningful_chars = re.compile(r'[一-龥ぁ-んァ-ヴー々〆ヵヶa-zA-Z0-9]')

    # 末尾から遡って「文末記号（。！？.!?）」の位置を探す
    sentence_end_pattern = re.compile(r'[。！？.!?]')
    last_sentence_end = -1
    for i in range(len(text) - 1, -1, -1):
        if sentence_end_pattern.match(text[i]):
            last_sentence_end = i
            break

    # 文末記号が見つからなければ、末尾から意味のある文字の位置を探す
    if last_sentence_end == -1:
        last_meaningful = -1
        for i in range(len(text) - 1, -1, -1):
            if meaningful_chars.match(text[i]):
                last_meaningful = i
                break
        if last_meaningful == -1:
            return text
        # 意味のある文字の直後で切る
        tail = text[last_meaningful + 1:]
        # tailが記号ゴミなら削除
        if len(tail) > 15 and len(re.findall(meaningful_chars, tail)) < 3:
            return text[:last_meaningful + 1].rstrip()
        return text

    # 文末記号より後の内容を検査
    tail_after_end = text[last_sentence_end + 1:]

    # tailが十分長く、意味のある文字がほとんど無いなら記号ゴミ扱いで削除
    if len(tail_after_end) > 15:
        meaningful_count = len(re.findall(meaningful_chars, tail_after_end))
        # tail のうち意味のある文字が10%未満なら削除
        if meaningful_count / max(1, len(tail_after_end)) < 0.10:
            return text[:last_sentence_end + 1].rstrip()

    return text

# Geminiが内部トークンとして扱う識別子（テキスト値に露出したら異常）
_GEMINI_INTERNAL_TOKENS = [
    "json_start", "json_end", "json_content", "json_body",
    "response_start", "response_end", "response_content",
    "output_start", "output_end", "content_start", "content_end",
    "schema_start", "schema_end", "field_start", "field_end",
]

def _strip_repetition_loop(text: str) -> str:
    """AI応答内の繰り返しループを検出・除去する。

    Gemini 2.5 Pro は稀に構造化出力の内部トークン（json_start等）を
    テキスト値として出力し、そのままループに陥って何百回も繰り返すバグがある。
    また、任意の単語やフレーズを異常な回数繰り返すこともある。

    対策:
    1. Gemini内部トークンが5回以上出現 → 全て除去
    2. 3〜30文字のフレーズが5回以上連続で繰り返される → 初回のみ残して除去
    3. 単語（3文字以上）が5回以上繰り返される → 初回のみ残す
    """
    if not text or len(text) < 20:
        return text

    # 1. Gemini内部トークンの露出を検出・除去
    for token in _GEMINI_INTERNAL_TOKENS:
        # 部分一致検索（json_start_extra なども対象）
        if text.count(token) >= 3:
            # トークン全体を除去（前後の区切り文字も一緒に）
            text = re.sub(rf"\b{re.escape(token)}\w*\b\s*[,、。\s]*", "", text, flags=re.IGNORECASE)

    # 2. 単語レベルの繰り返しループを除去
    # 3文字以上の英数字語 or 2文字以上の日本語が5回以上連続 → 初回のみ残す
    # 英語単語
    text = re.sub(r"(\b\w{3,}\b)(\s+\1){4,}", r"\1", text)
    # 日本語単語（漢字/ひらがな/カタカナ 2文字以上）
    text = re.sub(r"([一-龥ぁ-んァ-ヴー]{2,})(\s*\1){4,}", r"\1", text)

    # 3. 短フレーズ（4〜30文字）が5回以上繰り返される場合、初回のみ残す
    # 例: "abc def abc def abc def abc def abc def" → "abc def"
    for phrase_len in [4, 6, 8, 10, 15, 20, 30]:
        pattern = rf"(.{{{phrase_len}}}?)(?:\1){{4,}}"
        text = re.sub(pattern, r"\1", text)

    # 4. 連続空白の圧縮
    text = re.sub(r"[ \t]{3,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def _detect_repetition_loop(text: str) -> dict:
    """繰り返しループが元々存在したかを判定（UI警告用）。

    Returns:
        {
            "detected": bool,
            "type": "internal_token" | "phrase_repetition" | None,
            "sample": "検出されたパターンの例",
        }
    """
    if not text or len(text) < 50:
        return {"detected": False, "type": None, "sample": ""}

    # 内部トークン検出
    for token in _GEMINI_INTERNAL_TOKENS:
        if text.count(token) >= 3:
            return {"detected": True, "type": "internal_token", "sample": token}

    # 単語の異常繰り返し
    m = re.search(r"(\b\w{3,}\b)(\s+\1){4,}", text)
    if m:
        return {"detected": True, "type": "phrase_repetition", "sample": m.group(1)}

    m = re.search(r"([一-龥ぁ-んァ-ヴー]{2,})(\s*\1){4,}", text)
    if m:
        return {"detected": True, "type": "phrase_repetition", "sample": m.group(1)}

    return {"detected": False, "type": None, "sample": ""}

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
                prompt_t = getattr(um, "prompt_token_count", None)
                output_t = getattr(um, "candidates_token_count", None)
                total_t = getattr(um, "total_token_count", None)
                # 思考トークン: SDKバージョンで属性名が異なるため複数試す
                thoughts_t = (
                    getattr(um, "thoughts_token_count", None)
                    or getattr(um, "thinking_token_count", None)
                    or getattr(um, "reasoning_token_count", None)
                )
                # 属性が見つからない場合、合計から逆算する（Gemini APIの設計上必ず成立）
                # total = prompt + output + thoughts なので thoughts = total - prompt - output
                if thoughts_t is None and total_t and prompt_t is not None and output_t is not None:
                    diff = total_t - prompt_t - output_t
                    # マイナスやゼロは意味のある「思考0」として扱う
                    thoughts_t = max(0, diff)
                last_usage = {
                    "prompt_tokens": prompt_t,
                    "output_tokens": output_t,
                    "thoughts_tokens": thoughts_t,
                    "total_tokens": total_t,
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

def _run_stage0_review_digest(api_key: str, review: str, temperature: float = 0.4,
                                progress_cb=None) -> tuple:
    """Stage 0: 大量のレビューを Flash モデルで構造化ダイジェスト化する。

    Stage 1（Pro モデル）がレビュー全文を読むと以下の問題が起きる：
    - 注意力の希釈で本質的なペインポイントを見逃す
    - 入力量に負荷がかかりフィールド欠落や反復ループが発生
    - コストが跳ね上がる（プロは Flash の 12.5 倍高い）

    そこで先に安価な Flash モデルでレビューを消化し、
    構造化されたダイジェスト（200〜300文字）を作成する。
    Stage 1/2 にはこのダイジェストを渡すことで、注意力を集中させる。

    Returns:
        (digest_text, digest_dict): ダイジェストのテキスト形式と生辞書
        レビューが短い場合や失敗時は (元のreview, None) を返す。
    """
    if not review or len(review) <= REVIEW_DIGEST_THRESHOLD:
        return review, None

    if progress_cb:
        progress_cb(f"Stage 0/3: 長文レビュー({len(review)}文字)をFlashモデルでダイジェスト化中...")

    digest_prompt = f"""以下は商品のカスタマーレビュー原文です。ダイジェスト化して構造化JSONで返してください。

【レビュー原文（{len(review)}文字）】
{review}

【指示】
10フィールド全てを埋めた JSON を返してください。全体を通読して頻出パターンを抽出すること。
- 極端に少数の意見や1件だけの不満に引きずられず、複数レビューで共通するテーマを優先
- 引用は原文の言い回しを保持（勝手に言い換えない）
- emerging_keywords はレビュー独特の用語・略語・シーン語を発掘する対象
"""

    digest_result = _call_gemini_api(
        api_key=api_key,
        model_name=REVIEW_DIGEST_MODEL,
        user_prompt=digest_prompt,
        system_instruction="あなたはカスタマーレビュー分析のエキスパートです。大量のレビューから本質的なインサイトを客観的に抽出します。個人的な感想や創作は絶対にせず、レビュー原文に忠実な要約のみを行います。",
        temperature=temperature,
        thinking_budget=512,  # Flash + シンプルタスクなので思考予算は最小限
        max_retries=1,
        response_schema=ReviewDigestSchema,
    )

    if "error" in digest_result:
        if progress_cb:
            progress_cb(f"Stage 0 エラー: {digest_result.get('error', '不明')[:80]}。元レビューをそのまま使用します。")
        return review, None

    # ダイジェストをテキスト化して Stage 1/2 に渡す形にする
    def _get(k):
        v = digest_result.get(k, "") or ""
        return v.strip() if isinstance(v, str) else str(v)

    digest_text = f"""【レビューダイジェスト（原文{len(review)}文字を要約）】
処理レビュー件数: {_get('review_count_processed')}
全体評価傾向: {_get('overall_sentiment')}

■ 最頻出の不満: {_get('main_pain_point')}
■ ネガティブテーマ（頻出順）: {_get('top_negative_themes')}
■ 代表的なネガレビュー引用: 「{_get('representative_negative_quote')}」

■ ポジティブテーマ（頻出順）: {_get('top_positive_themes')}
■ 代表的なポジレビュー引用: 「{_get('representative_positive_quote')}」

■ レビューで頻出のキーワード: {_get('emerging_keywords')}
■ 主な使用シーン: {_get('usage_scenes')}
■ 主な購入者層: {_get('target_users')}
"""

    if progress_cb:
        progress_cb(f"✅ Stage 0 完了: {len(review)}文字 → {len(digest_text)}文字に集約")

    # digest_dict にはメタ情報も含める
    digest_dict = {k: v for k, v in digest_result.items() if not k.startswith("_")}
    digest_dict["_original_review_length"] = len(review)
    digest_dict["_digest_text_length"] = len(digest_text)
    digest_dict["_stage0_meta"] = digest_result.get("_meta", {})

    return digest_text, digest_dict


def _call_gemini_two_stage(api_key: str, model_name: str,
                            system_instruction: str,
                            genre: str, tone: str, seo_kw: str,
                            base: str, usp: str, spec: str, review: str,
                            current_title: str = "",
                            competitor_info: str = "",
                            temperature: float = 0.5,
                            thinking_budget: int = 2048,
                            use_stage0: bool = True,
                            progress_cb=None) -> dict:
    """2段階（レビュー消化を含む場合3段階）生成: 分析→成果物 に分けてフラットスキーマで確実に生成する。

    Geminiの構造化出力はList[str]やネストクラスでフィールド欠落が起きやすいため、
    各段とも全フィールドをstrに平坦化したスキーマで呼び出す。
    パース後に元のネスト構造へ組み直して返す。

    current_title: 現在の商品名（あれば）。整合性維持のためStage 1/2の文脈に渡す。
    competitor_info: 自社商品と競合商品の情報（あれば）。extracted_uspの深掘りに使用。
    use_stage0: レビューが長い場合にStage 0（Flash モデルでの要約）を実行するか
    """
    # ---- Stage 0: レビューが長い場合の消化（Flash モデルで安価に処理） ----
    review_digest_dict = None
    if use_stage0:
        review, review_digest_dict = _run_stage0_review_digest(
            api_key=api_key,
            review=review,
            temperature=temperature,
            progress_cb=progress_cb,
        )

    # ---- Stage 1: 分析（フラット12フィールド） ----
    if progress_cb:
        stage_prefix = "Stage 2/3" if review_digest_dict else "Stage 1/2"
        progress_cb(f"{stage_prefix}: 商品プロファイリング＆レビュー分析中...")

    stage1_prompt = f"""
【商品情報】
- ジャンル: {genre}
- 文章トーン: {tone}
- 狙いSEOキーワード: {seo_kw if seo_kw else "（未入力：文脈から自動抽出）"}

【入力データ】
1. 現在の商品名: {current_title if current_title else "（未入力）"}
2. 現在の商品説明: {base}
3. 自社の強み・USP: {usp if usp else "（未入力：既存文から抽出）"}
4. スペック・仕様: {spec}
5. カスタマーレビュー: {review}

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

    # ---- Stage 1 を 1a と 1b に分割して確実に生成する ----
    # 12フィールドを一気に生成させると Gemini 2.5 Pro でフィールド欠落が頻発するため、
    # 5フィールド(プロファイル) + 7フィールド(レビュー分析) に分割する。

    # === Stage 1a: 商品プロファイル（5フィールド） ===
    if progress_cb:
        stage_prefix = "Stage 2a/3" if review_digest_dict else "Stage 1a/2"
        progress_cb(f"{stage_prefix}: 商品プロファイル生成中（5フィールド）...")

    # 競合商品情報セクション（提供された場合のみ）
    competitor_section = ""
    if competitor_info and competitor_info.strip():
        competitor_section = f"""

【競合商品との比較情報（USPの深掘りに使用）】
{competitor_info}

【追加指示（競合情報がある場合）】
extracted_usp フィールドには、上記の競合商品と比較して**自社商品にしかない独自の強み**を反映してください。
競合が持っていない差別化ポイントを最優先で抽出し、「他社との違い」を明確に示すこと。
"""

    stage1a_prompt = f"""【商品情報】
- ジャンル: {genre}
- 文章トーン: {tone}
- 狙いSEOキーワード: {seo_kw if seo_kw else "（未入力：文脈から自動抽出）"}
- 現在の商品名: {current_title if current_title else "（未入力）"}

【入力データ】
- 商品説明: {base}
- 自社USP: {usp if usp else "（未入力：既存文から抽出）"}
- スペック: {spec}
- レビュー: {review}
{competitor_section}
【指示】
以下5フィールドのフラットJSONを返してください。全て必須。空文字禁止。装飾なし。

【JSON出力例】
{{
  "selected_type": "総合",
  "type_reason": "機能性とデザイン性が両立しており、バランスの良さから総合タイプと判定しました。",
  "extracted_usp": "他社にない独自の素材と製法により、耐久性と美観を高次元で両立している点が最大の差別化ポイントです。",
  "target_persona": "30代の女性で、日常使いのアイテムに品質と見た目の両方を求める層。SNSで情報収集する傾向がある。",
  "key_seo_keywords_csv": "主要キーワード1,主要キーワード2,関連語1,関連語2,関連語3,シーン語1,シーン語2"
}}

上記の**構造**を厳密に守り、内容は商品情報に合わせて書き起こしてください。
"""
    stage1a = _call_gemini_api(
        api_key, model_name, stage1a_prompt, system_instruction,
        temperature=temperature, thinking_budget=thinking_budget,
        response_schema=ProfileSchemaFlat,
    )
    if "error" in stage1a:
        return {"error": f"[Stage1aエラー] {stage1a['error']}",
                "raw": stage1a.get("raw", ""),
                "_meta": stage1a.get("_meta", {})}

    # === Stage 1b: ネガティブレビュー分析（7フィールド） ===
    if progress_cb:
        stage_prefix = "Stage 2b/3" if review_digest_dict else "Stage 1b/2"
        progress_cb(f"{stage_prefix}: ネガティブレビュー3パターン変換中（7フィールド）...")

    # Stage 1a の結果を Stage 1b の文脈に渡す（一貫性向上）
    persona = stage1a.get("target_persona", "")

    stage1b_prompt = f"""【商品情報】
- ジャンル: {genre}
- 文章トーン: {tone}

【入力データ】
- 商品説明: {base}
- スペック: {spec}
- レビュー: {review}
- ターゲット像（Stage 1aで確定）: {persona}

【指示】
以下7フィールドのフラットJSONを返してください。全て必須。空文字禁止。装飾なし。

【JSON出力例】
{{
  "identified_pain_point": "耐久性への不安と、写真と実物の色味の差異を心配する声が最も多い。",
  "pain_point_severity": "中",
  "pattern_a_text": "厳格な品質検査を経てお届け。素材本来の色合いを写真忠実に再現しており、実物との差はほぼありません。",
  "pattern_b_text": "モニター環境により多少の色味の差が出る可能性があります。気になる場合は30日以内であれば返品を承ります。",
  "pattern_c_text": "微細な色ムラは天然素材ならではの表情で、二つとして同じものがない一点物としてお楽しみいただけます。",
  "recommended_pattern": "B",
  "ai_recommendation": "誠実開示によって購入後のミスマッチを防ぎ、信頼獲得と長期的なブランド価値向上に繋がるパターンBを推奨します。"
}}

上記の**構造**を厳密に守り、内容は商品情報に合わせて書き起こしてください。
"""
    stage1b = _call_gemini_api(
        api_key, model_name, stage1b_prompt, system_instruction,
        temperature=temperature, thinking_budget=thinking_budget,
        response_schema=NegativeAnalysisSchemaFlat,
    )
    if "error" in stage1b:
        # Stage 1a は成功しているので、その結果は残しつつ 1b の失敗を通知
        return {"error": f"[Stage1bエラー] {stage1b['error']}",
                "raw": stage1b.get("raw", ""),
                "_meta": stage1b.get("_meta", {}),
                "product_profile": _unflatten_analysis({**stage1a})["product_profile"]}

    # Stage 1a と 1b の結果をマージして stage1 として扱う
    stage1 = {**stage1a, **stage1b}
    # メタ情報も合算
    m1a = stage1a.get("_meta", {}) or {}
    m1b = stage1b.get("_meta", {}) or {}
    u1a = m1a.get("usage") or {}
    u1b = m1b.get("usage") or {}
    def _add_num(a, b):
        if a is None and b is None: return None
        return (a or 0) + (b or 0)
    stage1["_meta"] = {
        "usage": {
            "prompt_tokens": _add_num(u1a.get("prompt_tokens"), u1b.get("prompt_tokens")),
            "output_tokens": _add_num(u1a.get("output_tokens"), u1b.get("output_tokens")),
            "thoughts_tokens": _add_num(u1a.get("thoughts_tokens"), u1b.get("thoughts_tokens")),
            "total_tokens": _add_num(u1a.get("total_tokens"), u1b.get("total_tokens")),
        },
        "finish_reason": f"1a={m1a.get('finish_reason', 'N/A')}, 1b={m1b.get('finish_reason', 'N/A')}",
        "model": model_name,
        "split_stage1": True,
    }


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
        # Stage 0あり: 4段階 / Stage 0なし: 3段階
        stage_prefix = "Stage 3c/3" if review_digest_dict else "Stage 2c/2"
        progress_cb(f"{stage_prefix}: Amazon＆楽天テキスト生成中...")

    recommended = str(nra.get("recommended_pattern", "b")).lower()
    recommended_text = nra.get(f"pattern_{recommended}_text", "")

    stage2_prompt = f"""
【商品情報】
- ジャンル: {genre}
- 文章トーン: {tone}
- 狙いSEOキーワード: {seo_kw if seo_kw else "（Stage1のkey_seo_keywordsを活用）"}

【入力データ】
1. 現在の商品名: {current_title if current_title else "（未入力：新規に最適タイトルを生成）"}
2. 現在の商品説明: {base}
3. 自社の強み・USP: {usp if usp else "（未入力）"}
4. スペック・仕様: {spec}
5. カスタマーレビュー: {review}

【Stage1で確定済みの分析結果（前提として使用）】
- 商品タイプ: {pp.get('selected_type', '')}
- 抽出USP: {pp.get('extracted_usp', '')}
- ターゲット像: {pp.get('target_persona', '')}
- 展開SEOキーワード: {', '.join(pp.get('key_seo_keywords', []) or [])}
- 最大の不安点: {nra.get('identified_pain_point', '')}
- 推奨パターン: {nra.get('recommended_pattern', '')}
- 推奨パターン本文: {recommended_text}

【指示】
以下24フィールドを全て埋めた JSON を出力してください。1フィールドも省略・空文字禁止。
また、システム命令に定義された下記3つのルールを絶対に守ること：
(A) 知的財産権リスクキーワード（ポケモン等の有名IP）は一切使わない
(B) rak_desc_html はスマホ保存規約準拠のタグのみ使用（h3/h4/h5/p/br/ul/ol/li/strong/b/em/i のみ、色装飾禁止）
(C) Amazon 3フィールド間の重複禁止（title / product_highlights / search_keywords）

# Amazon系（14フィールド）
1. amz_title: 商品名（50〜75文字、絶対上限75文字）
2. amz_product_highlights: 商品ハイライト（カンマ区切り7〜15個）
   ★重複禁止★ amz_title に含まれるキーワードは絶対に使用しない
3-12. amz_bullet_1_theme, amz_bullet_1_body, ..., amz_bullet_5_theme, amz_bullet_5_body:
     箇条書き5本のテーマと本文。テーマは重複禁止。
13. amz_description: 商品説明文（500〜800文字）
14-18. amz_qa_1〜5: Rufus想定Q&A。『Q: 質問 / A: 回答』形式
19. amz_search_keywords: 検索キーワード欄（半角スペース区切り、500バイト以内）
   ★重複禁止★ amz_title と amz_product_highlights のどちらにも含まれないキーワードだけを配置

  【Amazon 3フィールド生成手順（重複回避）】
   Step1. amz_title 完成
   Step2. title の各語をリストアップ → リストA
   Step3. amz_product_highlights は リストA に無い語のみで構成 → リストB作成
   Step4. amz_search_keywords は リストA+B のどちらにも無い語のみで構成

# 楽天系（5フィールド）
20. rak_title: 楽天商品タイトル（60〜127文字、絶対上限127）。SEO主要KWを冒頭に配置。
21. rak_catchcopy: キャッチコピー（60〜120文字、絶対上限127）
22. rak_desc_text: テキスト説明文（300〜600文字）
23. rak_desc_html: HTML説明文
   ★スマホ保存規約★ 使用可能タグは h3/h4/h5/p/br/ul/ol/li/strong/b/em/i のみ。
   font/style/script/div/span/h1/h2/img/table等は禁止。インラインstyle属性禁止。色装飾禁止。
24. rak_attributes: 推奨属性キーワード（カンマ区切り、5〜15個）
   カラー・サイズ・素材・ブランド・キャラクター（該当あれば）・対象年齢・使用シーン等
   例: カラー:ホワイト,サイズ:15×21×9cm,素材:PUレザー,ブランド:iikuru,対象年齢:大人,シーン:推し活
25. rak_color_palette: 楽天RMSエディタでの手動色装飾用の推奨カラーパレット
   ジャンル「{genre}」とターゲット層に合わせて、メイン/サブ/アクセント/背景の4色を提案。
   固定フォーマット:
     メインカラー: #XXXXXX | 用途と理由
     サブカラー: #XXXXXX | 用途と理由
     アクセントカラー: #XXXXXX | 用途と理由
     背景色: #XXXXXX | 用途と理由
     配色戦略: 商品ジャンル・購買心理を踏まえた戦略説明
   rak_desc_html本体には色は含めない。この提案は参考情報として提示するだけ。

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
            "stage0_used": review_digest_dict is not None,
        },
        # デバッグ用: 生のフラットレスポンスを保持
        "_raw_stage1": {k: v for k, v in stage1.items() if not k.startswith("_")},
        "_raw_stage2": {k: v for k, v in stage2.items() if not k.startswith("_")},
        "_review_digest": review_digest_dict,  # Stage 0の結果（UIで表示用）
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

def _byte_length(s: str) -> int:
    """UTF-8バイト数を返す（Amazon検索キーワード欄の500B制限判定用）。"""
    return len((s or "").encode("utf-8"))

def _split_search_kw(text: str) -> list:
    """検索キーワード文字列を半角/全角スペース・カンマ・読点で分割。"""
    if not text:
        return []
    parts = re.split(r"[\s\u3000,、]+", text.strip())
    return [p.strip() for p in parts if p.strip()]

def _find_multi_duplicates(title: str, highlights_csv: str, search_kws_text: str) -> dict:
    """3フィールド間の重複を検出する。

    ルール：
    - highlights の各KWが title に含まれる → highlights_dup
    - search_kws の各KWが title か highlights に含まれる → search_dup
    - 検索キーワード欄は独自KWで構成すべきという Amazon SEO ベストプラクティス

    Returns:
        highlights側の重複結果と、search側の重複結果を返す。
    """
    # ハイライト側の重複
    h_result = _find_title_highlight_duplicates(title, highlights_csv)

    # 検索キーワード側の重複
    if not search_kws_text:
        return {
            "highlights": h_result,
            "search": {"duplicated_kws": [], "unique_kws": [], "filtered_text": ""},
        }
    title_norm = _normalize_kw(title or "")
    highlights_kws = [k.strip() for k in (highlights_csv or "").split(",") if k.strip()]
    highlights_norm_set = {_normalize_kw(k) for k in highlights_kws}

    search_kws = _split_search_kw(search_kws_text)
    s_dup = []
    s_uniq = []
    for kw in search_kws:
        kw_norm = _normalize_kw(kw)
        if not kw_norm:
            continue
        if (kw_norm in title_norm) or (kw_norm in highlights_norm_set):
            s_dup.append(kw)
        else:
            s_uniq.append(kw)
    return {
        "highlights": h_result,
        "search": {
            "duplicated_kws": s_dup,
            "unique_kws": s_uniq,
            "filtered_text": " ".join(s_uniq),
        },
    }

def _find_ip_violations(text: str) -> list:
    """テキスト内の知的財産権リスクキーワード（有名IP/ブランド/キャラクター）を検出。

    Returns: [検出されたキーワード]
    完全一致でなく部分一致で検出（"ポケモンfit" も "ポケモン" として検出）。
    """
    if not text:
        return []
    text_norm = _normalize_kw(text)
    found = []
    for kw in IP_RISKY_KEYWORDS:
        kw_norm = _normalize_kw(kw)
        if kw_norm and kw_norm in text_norm:
            found.append(kw)
    # 重複除去（同じキーワードが複数箇所で見つかる場合）
    return list(dict.fromkeys(found))

def _check_rakuten_html_compliance(html: str) -> dict:
    """楽天HTML説明文が使用可能タグ規約に準拠しているかチェック。

    Returns:
        {
            "forbidden_tags_found": [検出された禁止タグ],
            "inline_style_found": bool,  # style="..." 属性
            "is_compliant": bool,
        }
    """
    if not html:
        return {"forbidden_tags_found": [], "inline_style_found": False, "is_compliant": True}

    forbidden = []
    for tag in RAKUTEN_HTML_FORBIDDEN_TAGS:
        # 開始タグ or 単独タグを検出
        if re.search(rf"<\s*{tag}(\s|>|/)", html, re.IGNORECASE):
            forbidden.append(tag)

    # インラインstyle属性
    inline_style = bool(re.search(r'\sstyle\s*=\s*["\']', html, re.IGNORECASE))

    return {
        "forbidden_tags_found": forbidden,
        "inline_style_found": inline_style,
        "is_compliant": (not forbidden) and (not inline_style),
    }

# =========================================================================
# CSV生成関数群
# =========================================================================
def _csv_from_rows(rows: list, fieldnames: list) -> str:
    """行データからCSV文字列を生成（全項目クォート・改行対応）"""
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        quoting=csv.QUOTE_ALL,
        lineterminator="\r\n",  # Excel互換
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()

def _generate_full_csv(res: dict) -> str:
    """全項目を1行のワイドCSVとして生成（スプレッドシート一覧管理用）"""
    p = res.get("product_profile") or {}
    n = res.get("negative_review_analysis") or {}
    a = res.get("amazon_output") or {}
    r = res.get("rakuten_output") or {}

    # 重複除去済み版も併記
    amz_title = a.get("title", "") or ""
    amz_highlights = a.get("product_highlights", "") or ""
    amz_search = a.get("search_keywords", "") or ""
    dedup_h = _find_title_highlight_duplicates(amz_title, amz_highlights)["filtered_csv"]
    dedup_multi = _find_multi_duplicates(amz_title, amz_highlights, amz_search)
    dedup_s = dedup_multi["search"]["filtered_text"]

    row = {}
    # === プロファイル ===
    row["商品タイプ"] = p.get("selected_type", "") or ""
    row["判定理由"] = p.get("type_reason", "") or ""
    row["抽出USP"] = p.get("extracted_usp", "") or ""
    row["ターゲット像"] = p.get("target_persona", "") or ""
    row["展開SEOキーワード"] = ", ".join(p.get("key_seo_keywords", []) or [])
    # === ネガティブ分析 ===
    row["最大の不安点"] = n.get("identified_pain_point", "") or ""
    row["深刻度"] = n.get("pain_point_severity", "") or ""
    row["パターンA(利点強調)"] = n.get("pattern_a_text", "") or ""
    row["パターンB(誠実開示)"] = n.get("pattern_b_text", "") or ""
    row["パターンC(メリット変換)"] = n.get("pattern_c_text", "") or ""
    row["推奨パターン"] = n.get("recommended_pattern", "") or ""
    row["推奨理由"] = n.get("ai_recommendation", "") or ""
    # === Amazon ===
    row["Amazon_商品名"] = amz_title
    row["Amazon_商品ハイライト_原文"] = amz_highlights
    row["Amazon_商品ハイライト_重複除去済み"] = dedup_h
    for i in range(1, 6):
        b = a.get(f"bullet_{i}") or {}
        theme = b.get("theme", "") if isinstance(b, dict) else ""
        body = b.get("body", "") if isinstance(b, dict) else ""
        row[f"Amazon_箇条書き{i}_テーマ"] = theme or ""
        row[f"Amazon_箇条書き{i}_本文"] = body or ""
    row["Amazon_商品説明"] = a.get("description", "") or ""
    row["Amazon_検索キーワード_原文"] = amz_search
    row["Amazon_検索キーワード_重複除去済み"] = dedup_s
    qas = a.get("rufus_qa_pairs", []) or []
    for i in range(5):
        row[f"Amazon_想定QA_{i+1}"] = str(qas[i]) if i < len(qas) else ""
    # === 楽天 ===
    row["楽天_商品タイトル"] = r.get("title", "") or ""
    row["楽天_キャッチコピー"] = r.get("catchcopy", "") or ""
    row["楽天_商品説明文_テキスト版"] = r.get("desc_text", "") or ""
    row["楽天_商品説明文_HTML版"] = r.get("desc_html", "") or ""
    row["楽天_推奨属性キーワード"] = r.get("attributes", "") or ""
    row["楽天_推奨カラーパレット"] = r.get("color_palette", "") or ""

    return _csv_from_rows([row], list(row.keys()))

def _generate_amazon_csv(res: dict) -> str:
    """Amazon項目のみを縦型CSVで生成（項目名 x 内容の2列）"""
    a = res.get("amazon_output") or {}
    amz_title = a.get("title", "") or ""
    amz_highlights = a.get("product_highlights", "") or ""
    amz_search = a.get("search_keywords", "") or ""
    dedup_h = _find_title_highlight_duplicates(amz_title, amz_highlights)["filtered_csv"]
    dedup_multi = _find_multi_duplicates(amz_title, amz_highlights, amz_search)
    dedup_s = dedup_multi["search"]["filtered_text"]

    rows = []
    rows.append({"項目": "商品名(タイトル)", "内容": amz_title})
    rows.append({"項目": "商品のハイライト(原文)", "内容": amz_highlights})
    rows.append({"項目": "商品のハイライト(重複除去済み・推奨)", "内容": dedup_h})
    for i in range(1, 6):
        b = a.get(f"bullet_{i}") or {}
        theme = b.get("theme", "") if isinstance(b, dict) else ""
        body = b.get("body", "") if isinstance(b, dict) else ""
        rows.append({"項目": f"箇条書き{i} テーマ", "内容": theme})
        rows.append({"項目": f"箇条書き{i} 本文", "内容": body})
    rows.append({"項目": "商品説明文", "内容": a.get("description", "") or ""})
    rows.append({"項目": "検索キーワード欄(原文)", "内容": amz_search})
    rows.append({"項目": "検索キーワード欄(重複除去済み・推奨)", "内容": dedup_s})
    qas = a.get("rufus_qa_pairs", []) or []
    for i in range(5):
        qa = str(qas[i]) if i < len(qas) else ""
        rows.append({"項目": f"想定Q&A {i+1}", "内容": qa})

    return _csv_from_rows(rows, ["項目", "内容"])

def _generate_rakuten_csv(res: dict) -> str:
    """楽天項目のみを縦型CSVで生成"""
    r = res.get("rakuten_output") or {}
    rows = [
        {"項目": "商品タイトル", "内容": r.get("title", "") or ""},
        {"項目": "キャッチコピー", "内容": r.get("catchcopy", "") or ""},
        {"項目": "商品説明文(テキスト版)", "内容": r.get("desc_text", "") or ""},
        {"項目": "商品説明文(HTML版)", "内容": r.get("desc_html", "") or ""},
        {"項目": "推奨属性キーワード", "内容": r.get("attributes", "") or ""},
        {"項目": "推奨カラーパレット", "内容": r.get("color_palette", "") or ""},
    ]
    return _csv_from_rows(rows, ["項目", "内容"])

def _generate_analysis_csv(res: dict) -> str:
    """プロファイル＋ネガティブレビュー分析のみを縦型CSVで生成"""
    p = res.get("product_profile") or {}
    n = res.get("negative_review_analysis") or {}
    rows = [
        {"項目": "商品タイプ", "内容": p.get("selected_type", "") or ""},
        {"項目": "判定理由", "内容": p.get("type_reason", "") or ""},
        {"項目": "抽出USP", "内容": p.get("extracted_usp", "") or ""},
        {"項目": "ターゲット像", "内容": p.get("target_persona", "") or ""},
        {"項目": "展開SEOキーワード", "内容": ", ".join(p.get("key_seo_keywords", []) or [])},
        {"項目": "最大の不安点", "内容": n.get("identified_pain_point", "") or ""},
        {"項目": "深刻度", "内容": n.get("pain_point_severity", "") or ""},
        {"項目": "パターンA(利点強調)", "内容": n.get("pattern_a_text", "") or ""},
        {"項目": "パターンB(誠実開示)", "内容": n.get("pattern_b_text", "") or ""},
        {"項目": "パターンC(メリット変換)", "内容": n.get("pattern_c_text", "") or ""},
        {"項目": "推奨パターン", "内容": n.get("recommended_pattern", "") or ""},
        {"項目": "推奨理由", "内容": n.get("ai_recommendation", "") or ""},
    ]
    return _csv_from_rows(rows, ["項目", "内容"])

# =========================================================================
# 競合商品情報取得関数（URLからの抽出 / ペースト対応）
# =========================================================================
def _fetch_product_from_url(url: str, timeout: int = 10) -> dict:
    """商品URLからHTMLを取得して主要情報を抽出する（ベストエフォート）。

    Amazon・楽天のような大手ECサイトはボット対策が厳しいため、取得失敗するケースも多い。
    失敗時は {"error": "..."} を返す。取得成功時は辞書で以下を返す:
    - title: タイトル
    - description: メタ説明
    - h1: h1見出し
    - main_text: 本文抜粋（最大3000文字）
    """
    if not url or not url.strip():
        return None
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {"error": "requests/beautifulsoup4 ライブラリが未インストールです（pip install requests beautifulsoup4）"}

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        r = requests.get(url.strip(), headers=headers, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return {"error": f"HTTPステータス {r.status_code}（アクセス拒否またはページ移動の可能性）"}

        # 文字エンコーディング推定
        if r.encoding == "ISO-8859-1":
            r.encoding = r.apparent_encoding

        soup = BeautifulSoup(r.text, "html.parser")

        # 不要要素の除去
        for tag in soup(["script", "style", "nav", "footer", "header", "iframe"]):
            tag.decompose()

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc.get("content", "").strip() if meta_desc else ""
        if not description:
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            description = og_desc.get("content", "").strip() if og_desc else ""

        h1_tag = soup.find("h1")
        h1 = h1_tag.get_text(strip=True) if h1_tag else ""

        # 本文抽出（過度に長くしない）
        main_text = soup.get_text(separator="\n", strip=True)
        main_text = re.sub(r"\n{3,}", "\n\n", main_text)
        main_text = main_text[:3000]

        return {
            "url": url,
            "title": title,
            "description": description,
            "h1": h1,
            "main_text": main_text,
        }
    except Exception as e:
        return {"error": f"取得エラー: {type(e).__name__}: {str(e)[:100]}"}

def _format_competitor_info(own: dict, competitors: list) -> str:
    """自社商品情報と競合商品情報群を、AI に渡すためのテキストに整形。"""
    parts = []
    if own and own.get("main_text"):
        parts.append(f"""■ 自社商品情報
タイトル: {own.get('title', '')}
説明: {own.get('description', '')}
見出し: {own.get('h1', '')}
本文抜粋: {own.get('main_text', '')[:1500]}
""")
    for i, c in enumerate(competitors, 1):
        if c and c.get("main_text"):
            parts.append(f"""■ 競合商品 {i}
タイトル: {c.get('title', '')}
説明: {c.get('description', '')}
見出し: {c.get('h1', '')}
本文抜粋: {c.get('main_text', '')[:1500]}
""")
    return "\n".join(parts) if parts else ""

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
    for k in ["title", "product_highlights", "description", "rufus_qa_pairs", "search_keywords"]:
        if not ao.get(k):
            missing.append(f"amazon_output.{k}")
    for i in range(1, 6):
        b = ao.get(f"bullet_{i}")
        if not b or not (isinstance(b, dict) and b.get("body")):
            missing.append(f"amazon_output.bullet_{i}")
    # rakuten_output
    ro = res.get("rakuten_output") or {}
    for k in ["title", "catchcopy", "desc_text", "desc_html", "attributes", "color_palette"]:
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

    # 商品プロファイリング解説パネル（初見担当者向け）
    with st.expander("❓ 商品プロファイリングの見方（クリックで解説を表示）", expanded=False):
        st.markdown("""
**このセクションで表示される4つの項目の意味と使い方**

| 項目 | 意味 | どう使うか |
|---|---|---|
| **商品タイプ** | AIが商品を「機能重視/デザイン重視/コスパ重視/総合」の4つに分類した結果 | 訴求ポイントの優先度決めに使用。例：機能重視なら「性能・仕様」を全面に、デザイン重視なら「見た目・世界観」を全面に |
| **判定理由** | なぜそのタイプと判定したかの根拠 | 判定が妥当か人の目で確認する材料。違和感があれば入力データを見直す |
| **抽出USP** | 他社と差別化できる独自の強み（Unique Selling Proposition）をAIが整理したもの | 商品説明文の中核メッセージ。全モールの最適化テキストの土台になる |
| **ターゲット像** | 主要な購入者ペルソナ（年齢・状況・購入動機） | 文章のトーンや使う語彙を決める。例：40代女性ならフォーマル寄り、10代ならカジュアル寄り |
| **展開SEOキーワード** | 狙いキーワードから派生した関連語・共起語のリスト | 各モールの検索キーワード欄への配分に使用。1つのフィールドに詰め込まず、タイトル/ハイライト/検索KWで役割分担 |

**展開SEOキーワードの有効性の目安**
- **5〜7個**: 商品ジャンルが狭く、コア検索語が明確な商品向け
- **8〜10個**: 一般的なEC商品（推奨レンジ）
- **10個超**: 汎用性が高い商品や、シーン別に訴求先が広い商品向け

主要KWは商品名(title)に、共起語はハイライトと検索キーワード欄に分散配置するのがベストプラクティスです。
        """)

    col1, col2 = st.columns([1, 1.3], gap="medium")

    # 繰り返しループ検出（全フィールドを対象に走査）
    p = res.get("product_profile") or {}
    n = res.get("negative_review_analysis") or {}
    loop_detected_fields = []
    for field_name in ["type_reason", "extracted_usp", "target_persona"]:
        v = p.get(field_name, "")
        det = _detect_repetition_loop(v) if isinstance(v, str) else {"detected": False}
        if det["detected"]:
            loop_detected_fields.append((f"product_profile.{field_name}", det["sample"]))
    for field_name in ["identified_pain_point", "pattern_a_text", "pattern_b_text",
                        "pattern_c_text", "ai_recommendation"]:
        v = n.get(field_name, "")
        det = _detect_repetition_loop(v) if isinstance(v, str) else {"detected": False}
        if det["detected"]:
            loop_detected_fields.append((f"negative_review_analysis.{field_name}", det["sample"]))

    if loop_detected_fields:
        sample_names = ", ".join([f"`{fn}` (「{sm}」を反復)" for fn, sm in loop_detected_fields[:3]])
        st.error(
            f"⚠️ **AIの繰り返しループ幻覚を検出しました**（Gemini 2.5系の既知バグ）\n\n"
            f"対象フィールド: {sample_names}"
            + ("..." if len(loop_detected_fields) > 3 else "")
            + "\n\n該当フィールドは自動的に反復部分を除去して表示していますが、"
            "内容が短くなっている可能性があります。品質確保のため、思考予算を上げて再生成することを推奨します。"
        )

    with col1:
        st.subheader("📋 商品プロファイリング")
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

    # 全体の知的財産権リスクチェック（title + highlights + search_kw + description をまとめて検査）
    title = a.get("title", "")
    highlights = a.get("product_highlights", "") or ""
    search_kws_text = a.get("search_keywords", "") or ""
    description = a.get("description", "") or ""
    bullets_text = " ".join([
        (a.get(f"bullet_{i}") or {}).get("body", "") if isinstance(a.get(f"bullet_{i}"), dict) else ""
        for i in range(1, 6)
    ])
    combined_text = f"{title} {highlights} {search_kws_text} {description} {bullets_text}"
    ip_violations = _find_ip_violations(combined_text)
    if ip_violations:
        st.error(
            f"⚠️ **知的財産権リスクの可能性があるキーワードを検出**：`{'`, `'.join(ip_violations)}`\n\n"
            "これらは他社の商標・キャラクター・作品名の可能性があり、"
            "Amazon で違反検知される可能性があります。該当箇所を確認し、"
            "一般名詞（例: 「キャラクター」「ぬいぐるみ」）に置き換えることを強く推奨します。"
        )

    # 3フィールド重複検出
    multi_dup = _find_multi_duplicates(title, highlights, search_kws_text)
    h_dup_result = multi_dup["highlights"]
    s_dup_result = multi_dup["search"]

    # タイトル（75文字ハード上限）
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
    kw_list = [k.strip() for k in highlights.split(",") if k.strip()]
    duplicated = h_dup_result["duplicated_kws"]
    unique = h_dup_result["unique_kws"]

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
                     value=h_dup_result["filtered_csv"], height=80,
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
    st.markdown("##### 商品説明文")
    st.markdown(_char_badge(description, AMAZON_DESC_TARGET), unsafe_allow_html=True)
    st.text_area("Amazon説明文", value=description, height=220,
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

    # 🆕 検索キーワード欄（500バイト上限、title/highlights と重複禁止）
    st.markdown("##### 🆕 検索キーワード欄（500バイト以内）")
    st.caption(
        "Amazon 検索キーワード欄。半角スペース区切りで入稿。"
        "タイトルとハイライトのどちらにも含まれていないキーワードだけを配置します。"
    )
    search_kws_all = _split_search_kw(search_kws_text)
    s_duplicated = s_dup_result["duplicated_kws"]
    s_unique = s_dup_result["unique_kws"]

    byte_len = _byte_length(search_kws_text)
    byte_badge_cls = "badge-ok" if byte_len <= AMAZON_SEARCH_KW_BYTE_LIMIT else "badge-ng"
    st.markdown(
        f'<span class="count-badge {byte_badge_cls}">{byte_len} / {AMAZON_SEARCH_KW_BYTE_LIMIT}バイト</span>'
        + _char_badge_count(s_unique, AMAZON_SEARCH_KW_TARGET)
        + (f'<span class="count-badge badge-ng">重複{len(s_duplicated)}個</span>' if s_duplicated else ""),
        unsafe_allow_html=True,
    )

    if byte_len > AMAZON_SEARCH_KW_BYTE_LIMIT:
        st.error(f"⚠️ 500バイトを超えています（現在 {byte_len}B）。キーワードを削減してください。")
    if s_duplicated:
        st.error(
            f"⚠️ タイトル or ハイライトと重複するキーワードが {len(s_duplicated)} 個あります "
            f"（有効な独自キーワードは {len(s_unique)} 個のみ）。"
            "重複はSEO無効化になるため、下記『重複除去済み』の版を推奨します。"
        )

    st.markdown("**AIが生成した原文（重複含む）**")
    st.text_area("Amazon検索キーワード_原文", value=search_kws_text, height=90,
                 key="amz_search_raw", label_visibility="collapsed")

    if search_kws_all:
        tags_html = []
        for kw in search_kws_all:
            if kw in s_duplicated:
                tags_html.append(
                    f'<span class="theme-tag" style="background:#dc2626;">'
                    f'❌ {kw}<span style="opacity:0.7;font-size:0.7em;"> (重複)</span></span>'
                )
            else:
                tags_html.append(
                    f'<span class="theme-tag" style="background:#16a34a;">✓ {kw}</span>'
                )
        st.markdown(" ".join(tags_html), unsafe_allow_html=True)

    if s_duplicated:
        st.markdown("**✂️ 重複除去済み版（推奨・そのまま入稿可）**")
        st.text_area("Amazon検索キーワード_重複除去",
                     value=s_dup_result["filtered_text"], height=90,
                     key="amz_search_filtered", label_visibility="collapsed")
        filtered_byte = _byte_length(s_dup_result["filtered_text"])
        st.caption(f"重複除去後: {filtered_byte} バイト / {len(s_unique)} 個のキーワード")

def render_rakuten_tab(res: dict):
    r = res.get("rakuten_output") or {}
    st.subheader("📤 楽天市場 最適化テキスト")
    st.caption("スマホCVR最適化 & 楽天AI検索対策。HTML説明文はスマホ保存規約に準拠。")

    if not r:
        st.warning("⚠️ 楽天成果物が生成されませんでした。思考予算を上げて再実行してください。")
        return

    # 全体の知的財産権リスクチェック
    title = r.get("title", "") or ""
    catchcopy = r.get("catchcopy", "") or ""
    desc_text = r.get("desc_text", "") or ""
    desc_html = r.get("desc_html", "") or ""
    attributes = r.get("attributes", "") or ""
    combined_text = f"{title} {catchcopy} {desc_text} {attributes}"
    ip_violations = _find_ip_violations(combined_text)
    if ip_violations:
        st.error(
            f"⚠️ **知的財産権リスクの可能性があるキーワードを検出**：`{'`, `'.join(ip_violations)}`\n\n"
            "楽天でも他社商標・キャラクター名は違反リスクがあります。該当箇所を確認し、"
            "一般名詞に置き換えることを推奨します。"
        )

    # 🆕 商品タイトル
    st.markdown("##### 🆕 商品タイトル（60〜127文字）")
    st.caption("楽天検索SEOで最重要。冒頭にSEO主要KWを配置。127文字を超えると検索結果でも見切れる。")
    st.markdown(
        _char_badge(title, RAKUTEN_TITLE_TARGET, hard_max=RAKUTEN_TITLE_HARD_MAX),
        unsafe_allow_html=True,
    )
    st.text_area("楽天タイトル", value=title, height=80,
                 key="rak_title", label_visibility="collapsed")
    if len(title) > RAKUTEN_TITLE_HARD_MAX:
        st.error(f"⚠️ 127文字を超えています（現在 {len(title)} 文字）。手動で削るか再生成してください。")

    # キャッチコピー
    st.markdown("##### キャッチコピー")
    st.markdown(
        _char_badge(catchcopy, RAKUTEN_CATCH_TARGET, hard_max=RAKUTEN_CATCH_HARD_MAX),
        unsafe_allow_html=True,
    )
    st.text_area("楽天キャッチ", value=catchcopy, height=80,
                 key="rak_catch", label_visibility="collapsed")

    # 商品説明文（テキスト版）
    st.markdown("##### 商品説明文（テキスト版）")
    st.markdown(_char_badge(desc_text, RAKUTEN_TEXT_TARGET), unsafe_allow_html=True)
    st.text_area("楽天テキスト", value=desc_text, height=180,
                 key="rak_text", label_visibility="collapsed")

    # 商品説明文（HTML版）＋ スマホ規約チェック
    st.markdown("##### 商品説明文（HTML版）")
    html_check = _check_rakuten_html_compliance(desc_html)
    if not html_check["is_compliant"]:
        problems = []
        if html_check["forbidden_tags_found"]:
            problems.append(f"禁止タグ: `<{'>`, `<'.join(html_check['forbidden_tags_found'])}>`")
        if html_check["inline_style_found"]:
            problems.append("インライン`style=\"...\"`属性")
        st.error(
            "⚠️ **楽天スマホ規約違反**：以下の要素が含まれているためスマホでは保存できません。\n\n"
            + "\n".join([f"- {p}" for p in problems])
            + f"\n\n使用可能なタグは `{'`, `'.join(RAKUTEN_HTML_ALLOWED_TAGS)}` のみです。"
            "手動で修正するか、思考予算を上げて再生成してください。"
        )
    else:
        st.success("✅ 楽天スマホ規約に準拠したHTMLです（PC・スマホ両対応）")

    st.text_area("楽天HTML", value=desc_html, height=260,
                 key="rak_html", label_visibility="collapsed")

    if desc_html:
        with st.expander("👁️ HTMLプレビュー"):
            st.markdown(desc_html, unsafe_allow_html=True)

    # 🆕 推奨属性キーワード（旧 検索KW欄を置き換え）
    st.markdown("##### 🆕 推奨属性キーワード")
    st.caption(
        "楽天RMS商品登録の推奨項目に対応。"
        "カラー・サイズ・素材・ブランド・キャラクター・対象年齢・使用シーンなどをカンマ区切りで入力可能な形式。"
    )
    attr_list = [k.strip() for k in attributes.split(",") if k.strip()]
    st.markdown(
        _char_badge_count(attr_list, RAKUTEN_ATTR_KW_TARGET),
        unsafe_allow_html=True,
    )
    st.text_area("楽天推奨属性", value=attributes, height=100,
                 key="rak_attr", label_visibility="collapsed")
    if attr_list:
        st.markdown(" ".join([f'<span class="theme-tag">{a}</span>' for a in attr_list]),
                    unsafe_allow_html=True)

    # 🆕 推奨カラーパレット
    color_palette = r.get("color_palette", "") or ""
    if color_palette:
        st.markdown("##### 🎨 推奨カラーパレット（楽天RMSエディタで手動適用する際の参考）")
        st.caption(
            "商品ジャンルとターゲット層に応じた推奨配色。"
            "rak_desc_html には色装飾を含めていません（スマホ規約準拠のため）が、"
            "楽天RMSエディタで手動で色を追加する際にこの配色を参考にしてください。"
        )
        # カラーパレット文字列から色コードを抽出して視覚表示
        color_matches = re.findall(r'([#][0-9A-Fa-f]{6})', color_palette)
        if color_matches:
            # カラースウォッチを表示
            swatch_cols = st.columns(min(len(color_matches), 5))
            for i, color_code in enumerate(color_matches[:5]):
                with swatch_cols[i]:
                    st.markdown(
                        f'<div style="background-color:{color_code};height:60px;border-radius:6px;'
                        f'border:1px solid #ccc;display:flex;align-items:center;justify-content:center;">'
                        f'<span style="color:#fff;text-shadow:0 0 3px #000;font-weight:bold;font-size:0.8rem;">'
                        f'{color_code}</span></div>',
                        unsafe_allow_html=True,
                    )
        # 説明文を表示
        st.text_area("カラーパレット詳細（コピー可）", value=color_palette, height=180,
                     key="rak_color_palette", label_visibility="collapsed")

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
        use_stage0 = st.checkbox(
            "🆕 Stage 0: 長文レビュー自動要約（推奨）",
            value=True,
            help=(
                f"ON: レビューが{REVIEW_DIGEST_THRESHOLD}文字を超える場合、"
                f"先に安価な Flash モデルで構造化ダイジェスト化してから Stage 1/2 に渡します。"
                "長文レビューでのフィールド欠落バグを防ぎ、コストも下がります。"
                "OFF: レビュー原文をそのまま Stage 1 に渡します（30〜100件程度のレビュー向け）。"
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

    # 入力クリアコールバック
    _input_keys = [
        "input_current_title", "input_base", "input_usp", "input_spec",
        "input_review", "input_seo",
        "input_own_url", "input_comp_url_1", "input_comp_url_2", "input_comp_url_3",
        "input_own_paste", "input_comp_paste",
    ]
    def _clear_all_inputs():
        for k in _input_keys:
            if k in st.session_state:
                st.session_state[k] = ""
        # 競合取得キャッシュもクリア
        if "fetched_competitor_info" in st.session_state:
            del st.session_state["fetched_competitor_info"]

    def _clear_single_input(key):
        """個別項目のクリアコールバック"""
        st.session_state[key] = ""

    def _input_with_clear(label, key, area=True, height=110, placeholder="", help=None):
        """ラベル + 右横クリアボタン + 入力ウィジェット をコンパクトに配置するヘルパー。

        Streamlit の on_click コールバックを使い、指定 key の session_state を空にする。
        area=True: text_area / area=False: text_input を使い分ける。
        """
        header_cols = st.columns([6, 1])
        with header_cols[0]:
            st.markdown(f"**{label}**")
        with header_cols[1]:
            st.button(
                "🗑 クリア",
                key=f"btn_clr_{key}",
                on_click=_clear_single_input,
                args=(key,),
                use_container_width=True,
                help="この項目のみクリア",
            )
        if area:
            return st.text_area(
                label, key=key, height=height, placeholder=placeholder,
                help=help, label_visibility="collapsed",
            )
        else:
            return st.text_input(
                label, key=key, placeholder=placeholder,
                help=help, label_visibility="collapsed",
            )

    # ヘッダ行に「すべてクリア」ボタン
    col_hdr1, col_hdr2 = st.columns([4, 1])
    with col_hdr2:
        st.button("🗑 入力をすべてクリア", on_click=_clear_all_inputs, use_container_width=True)

    # 現在の商品名
    c_current_title = _input_with_clear(
        "0. 現在の商品名（任意・強く推奨）",
        "input_current_title",
        area=False,
        placeholder="例: iikuru ぬいぐるみポーチ 2WAY ショルダーバッグ",
        help="現在使用中の商品名を入力すると、新しい商品名との整合性が保たれ、"
             "既存の商品識別との連続性が確保されます。空欄でも問題なく生成できますが、"
             "既存の商品を最適化する場合は入力を強くおすすめします。",
    )

    col_in1, col_in2 = st.columns(2, gap="medium")
    with col_in1:
        c_base = _input_with_clear(
            "1. 現在の商品説明・箇条書き（必須）", "input_base",
            height=140,
            placeholder="既存の商品ページ文章を貼り付けてください。",
        )
        c_usp = _input_with_clear(
            "2. 自社独自の強み・こだわり・専門情報（任意）", "input_usp",
            height=110,
            placeholder="工場直接仕入れ、独自の検品体制、素材規格など。空欄ならAIが自動抽出します。",
        )
    with col_in2:
        c_spec = _input_with_clear(
            "3. 補足スペック・仕様・サイズ等（必須）", "input_spec",
            height=140,
            placeholder="サイズ、重量、素材、耐荷重、付属品などの正確な数値（Rufus対策に直結）。",
        )
        c_review = _input_with_clear(
            "4. カスタマーレビュー・顧客の悩み（必須）", "input_review",
            height=110,
            placeholder="ネガティブなレビューや、購入者が迷いやすいポイントを貼り付けてください。",
        )
        c_seo = _input_with_clear(
            "5. 狙いたいSEOキーワード（任意）", "input_seo",
            area=False,
            placeholder="例：介護用クッション, 洗える, 通気性",
        )

    # ---- 競合商品比較セクション ----
    with st.expander("🔍 6. 競合商品との比較（任意・独自USPの深掘りに使用）", expanded=False):
        st.caption(
            "自社商品と競合商品のURLを入力するか、直接ペーストしてください。"
            "AIがそれらを比較して、自社商品にしかない独自の強みを 抽出USP に反映します。"
            "URL取得は大手ECサイトのボット対策で失敗することがあるため、失敗時は直接ペーストしてください。"
        )
        col_own, col_comp = st.columns(2, gap="medium")
        with col_own:
            st.markdown("**🏢 自社商品**")
            c_own_url = _input_with_clear(
                "自社商品のURL", "input_own_url",
                area=False,
                placeholder="https://...",
            )
            c_own_paste = _input_with_clear(
                "または直接ペースト（自社商品情報）", "input_own_paste",
                height=120,
                placeholder="商品ページのタイトル・説明・スペック等を貼り付け",
            )
        with col_comp:
            st.markdown("**🎯 競合商品（最大3件）**")
            c_comp_url_1 = _input_with_clear(
                "競合商品URL 1", "input_comp_url_1",
                area=False, placeholder="https://...",
            )
            c_comp_url_2 = _input_with_clear(
                "競合商品URL 2", "input_comp_url_2",
                area=False, placeholder="https://...",
            )
            c_comp_url_3 = _input_with_clear(
                "競合商品URL 3", "input_comp_url_3",
                area=False, placeholder="https://...",
            )
            c_comp_paste = _input_with_clear(
                "または直接ペースト（競合商品情報）", "input_comp_paste",
                height=120,
                placeholder="複数競合を1つのテキストにまとめて貼り付け可能",
            )

        # URL取得ボタン
        fetch_col1, fetch_col2 = st.columns([1, 3])
        with fetch_col1:
            if st.button("🔎 URLから情報取得", use_container_width=True):
                with st.spinner("URLから商品情報を取得中..."):
                    own_info = _fetch_product_from_url(c_own_url) if c_own_url else None
                    comp_infos = []
                    for u in [c_comp_url_1, c_comp_url_2, c_comp_url_3]:
                        if u and u.strip():
                            comp_infos.append(_fetch_product_from_url(u))
                    st.session_state["fetched_competitor_info"] = {
                        "own": own_info,
                        "competitors": comp_infos,
                    }
        with fetch_col2:
            if "fetched_competitor_info" in st.session_state:
                fci = st.session_state["fetched_competitor_info"]
                own_ok = fci.get("own") and "error" not in fci["own"]
                comp_ok_count = sum(1 for c in fci.get("competitors", [])
                                    if c and "error" not in c)
                if own_ok or comp_ok_count > 0:
                    st.success(f"取得成功: 自社{'✓' if own_ok else '✗'} / 競合{comp_ok_count}件")
                # エラー情報も表示
                if fci.get("own") and "error" in fci["own"]:
                    st.warning(f"自社URL: {fci['own']['error']}")
                for i, c in enumerate(fci.get("competitors", []), 1):
                    if c and "error" in c:
                        st.warning(f"競合URL{i}: {c['error']}")

        # 取得結果のプレビュー
        if "fetched_competitor_info" in st.session_state:
            fci = st.session_state["fetched_competitor_info"]
            with st.expander("📄 URL取得結果プレビュー"):
                own = fci.get("own")
                if own and "error" not in own:
                    st.markdown("**自社商品:**")
                    st.text(f"タイトル: {own.get('title', '')[:200]}")
                    st.text(f"説明: {own.get('description', '')[:300]}")
                for i, c in enumerate(fci.get("competitors", []), 1):
                    if c and "error" not in c:
                        st.markdown(f"**競合{i}:**")
                        st.text(f"タイトル: {c.get('title', '')[:200]}")
                        st.text(f"説明: {c.get('description', '')[:300]}")

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

                # 競合情報を組み立て（URL取得済み + ペースト の両方を統合）
                competitor_info = ""
                fci = st.session_state.get("fetched_competitor_info")
                if fci:
                    own = fci.get("own")
                    comps = [c for c in fci.get("competitors", []) if c and "error" not in c]
                    own_ok = own and "error" not in own
                    competitor_info = _format_competitor_info(
                        own if own_ok else None, comps
                    )
                # ペースト内容も追加
                if c_own_paste or c_comp_paste:
                    paste_section = ""
                    if c_own_paste:
                        paste_section += f"\n■ 自社商品情報（手動ペースト）\n{c_own_paste}\n"
                    if c_comp_paste:
                        paste_section += f"\n■ 競合商品情報（手動ペースト）\n{c_comp_paste}\n"
                    competitor_info = (competitor_info + "\n" + paste_section).strip()

                _progress("初期化中...")
                res = _call_gemini_two_stage(
                    api_key=api_key,
                    model_name=model_name,
                    system_instruction=sys_inst,
                    genre=genre, tone=tone, seo_kw=c_seo,
                    base=c_base, usp=c_usp, spec=c_spec, review=c_review,
                    current_title=c_current_title,
                    competitor_info=competitor_info,
                    temperature=temperature,
                    thinking_budget=thinking_budget,
                    use_stage0=use_stage0,
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

        # === CSV ダウンロードセクション ===
        st.markdown("### 📥 生成結果を CSV でダウンロード")
        st.caption(
            "文字コードは UTF-8 BOM 付き（Excel で文字化けしません）。"
            "改行やカンマを含む本文は全てクォート処理済み。"
        )
        _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        _dl1, _dl2, _dl3, _dl4 = st.columns(4)
        with _dl1:
            st.download_button(
                label="📊 全項目CSV",
                data=_generate_full_csv(res).encode("utf-8-sig"),
                file_name=f"ecom_seo_全項目_{_ts}.csv",
                mime="text/csv",
                help="全項目を1行にまとめたワイド形式CSV。複数商品をスプレッドシートで一覧管理する用途に最適。",
                use_container_width=True,
            )
        with _dl2:
            st.download_button(
                label="🛒 Amazon項目CSV",
                data=_generate_amazon_csv(res).encode("utf-8-sig"),
                file_name=f"ecom_seo_amazon_{_ts}.csv",
                mime="text/csv",
                help="Amazon項目のみ縦型(項目名×内容)でまとめたCSV。Amazon Seller Central への手動入稿補助用。重複除去済み版も併記。",
                use_container_width=True,
            )
        with _dl3:
            st.download_button(
                label="🔴 楽天項目CSV",
                data=_generate_rakuten_csv(res).encode("utf-8-sig"),
                file_name=f"ecom_seo_rakuten_{_ts}.csv",
                mime="text/csv",
                help="楽天項目のみ縦型でまとめたCSV。楽天RMSへの手動入稿補助用。",
                use_container_width=True,
            )
        with _dl4:
            st.download_button(
                label="🧠 分析結果CSV",
                data=_generate_analysis_csv(res).encode("utf-8-sig"),
                file_name=f"ecom_seo_分析_{_ts}.csv",
                mime="text/csv",
                help="商品プロファイル＋ネガティブレビュー分析のみのCSV。社内資料・報告用。",
                use_container_width=True,
            )
        st.markdown("---")

        # Stage 0が動いていた場合、ダイジェストを表示
        digest = res.get("_review_digest")
        if digest:
            with st.expander(
                f"📚 Stage 0 レビューダイジェスト（原文 {digest.get('_original_review_length', 0):,}文字 → 集約 {digest.get('_digest_text_length', 0):,}文字）",
                expanded=False,
            ):
                st.caption(
                    "長文レビューを Gemini 2.5 Flash で構造化ダイジェスト化した結果です。"
                    "Stage 1/2 にはこの要約が渡され、AI が本質的なインサイトに集中できるようになっています。"
                )
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("##### 🔻 ネガティブ側")
                    st.markdown(f"**最頻出の不満**：{digest.get('main_pain_point', '')}")
                    st.markdown(f"**ネガティブテーマ**：{digest.get('top_negative_themes', '')}")
                    st.markdown(f"**代表引用**：「{digest.get('representative_negative_quote', '')}」")
                with c2:
                    st.markdown("##### 🔺 ポジティブ側")
                    st.markdown(f"**全体傾向**：{digest.get('overall_sentiment', '')}")
                    st.markdown(f"**ポジティブテーマ**：{digest.get('top_positive_themes', '')}")
                    st.markdown(f"**代表引用**：「{digest.get('representative_positive_quote', '')}」")
                st.markdown("---")
                st.markdown(f"**📌 レビュー頻出キーワード**：`{digest.get('emerging_keywords', '')}`")
                st.markdown(f"**🎯 主な使用シーン**：{digest.get('usage_scenes', '')}")
                st.markdown(f"**👥 主な購入者層**：{digest.get('target_users', '')}")
                st.markdown(f"**📊 処理レビュー件数**：{digest.get('review_count_processed', '不明')}")

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
