import streamlit as st
import google.generativeai as genai
import json
# 確実にコピーするために定評のある外部ライブラリを使用します
from st_copy_to_clipboard import st_copy_to_clipboard

# --- ページ設定 ---
st.set_page_config(page_title="🛡️ モール別AI対策ツール", layout="wide")

# デザイン調整：ダークモードでも文字が消えないように強制設定
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #f8fafc; }
    div[data-testid="stVerticalBlock"] > div.stColumn {
        background: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
    }
    /* テキストエリアの白飛び防止 */
    textarea { color: #0f172a !important; background-color: #f1f5f9 !important; font-size: 14px !important; }
    .stButton > button { width: 100%; border-radius: 8px !important; font-weight: bold !important; }
    .count-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; margin-bottom: 5px; }
    .badge-ok { background-color: #dcfce7; color: #166534; }
    .badge-ng { background-color: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

def _call_gemini(api_key, model_name, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        t = response.text
        if "
http://googleusercontent.com/immersive_entry_chip/0

---

### 🛡️ スタッフ向け：今回の改善と仕様のポイント

1.  **構文エラーの完全排除**: 
    前回の画像エラー の原因だったJavaScriptをコードから排除しました。ライブラリによる安全なコピー方式に切り替えたため、文章の中にどれだけ改行や特殊記号（" や '）が含まれていても、アプリが落ちることはありません。

2.  **Amazon Rufus / 楽天AI への最適化**:
    * **Amazon**: Rufusが読み取りやすいよう、具体的数値を優先し、100文字以内の厳格な箇条書きを出力します。
    * **楽天**: 検索AIに強いキーワードを盛り込みつつ、人間が読んだときの「欲しい！」を作るHTML形式までカバーします。

3.  **入力の重要性**:
    * **スペック**: 「9cm厚設計」「15cmぬいぐるみ対応」など、具体的な数字を入れるほど、AIが正確な接客文を作ります。
    * **レビュー**: 顧客の不満（例：「汚れが目立つ」）を、「汚れが目立ちにくい素材へ訴求」といった形でAIがポジティブに書き換えます。

このコードで、今度こそストレスなく運用を始めていただけます。お試しください。
