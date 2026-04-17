import streamlit as st
import google.generativeai as genai
import json
import streamlit.components.v1 as components

# --- ページ設定 ---
st.set_page_config(page_title="Rufus ＆ 楽天AI モール別対策ツール", layout="wide")

def _inject_custom_style():
    st.markdown("""
    <style>
      html, body, [data-testid="stAppViewContainer"] { background-color: #f8fafc; }
      [data-testid="stSidebar"] { background-color: #0f172a !important; }
      [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #ffffff !important; font-weight: 600 !important;
      }
      [data-testid="stSidebar"] div[role="radiogroup"] label div { color: #ffffff !important; }
      [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea,
      [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1e293b !important; color: #ffffff !important; border: 1px solid #334155 !important;
      }
      [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] span { color: #ffffff !important; }
      
      div[data-testid="stVerticalBlock"] > div.stColumn {
        background: #ffffff; padding: 25px !important; border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;
      }
      textarea { color: #0f172a !important; background-color: #f1f5f9 !important; border: 1px solid #cbd5e1 !important; }
      
      .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important; font-weight: bold !important; width: 100%; height: 3.5em; border-radius: 8px !important;
      }
      .count-badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; margin-bottom: 6px; }
      .badge-ok { background-color: #dcfce7; color: #166534; }
      .badge-ng { background-color: #fee2e2; color: #991b1b; }
    </style>
    """, unsafe_allow_html=True)

# ★新機能：確実にクリップボードにコピーするHTMLコンポーネント★
def st_copy_button(text, label):
    safe_text = text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$').replace('\n', '\\n')
    html_code = f"""
    <button id="copy-btn" style="
        background-color: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe;
        padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; width: 100%;
    ">{label} をコピー</button>
    <script>
    document.getElementById('copy-btn').onclick = function() {{
        const text = `{safe_text}`;
        navigator.clipboard.writeText(text).then(() => {{
            this.innerText = "✅ コピー完了！";
            this.style.backgroundColor = "#dcfce7";
            this.style.color = "#166534";
            setTimeout(() => {{
                this.innerText = "{label} をコピー";
                this.style.backgroundColor = "#eff6ff";
                this.style.color = "#2563eb";
            }}, 2000);
        }});
    }};
    </script>
    """
    components.html(html_code, height=45)

def _call_gemini(api_key, model_name, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        text = response.text
        if "
http://googleusercontent.com/immersive_entry_chip/0

---

## 🛡️ スタッフ向け：モール別AI対策ツール仕様書

社内での共有・説明にご活用ください。

### 1. 開発の背景：AIが「接客」する時代の到来
現在、Amazonや楽天では、AIがお客様の質問に答えて商品をおすすめする機能が導入されています。
* **Amazon Rufus**: 「このポーチに15cmのぬいぐるみが2体入る？」といった具体的な質問に答えます。
* **楽天AI**: 「母の日のギフトに最適な、高評価でラッピング対応の商品はどれ？」といった探しものを助けます。
このツールは、**AIが「この商品が正解です！」と答えやすくするための情報整備**を行います。

### 2. モール別リライトの特徴

#### 🛒 Amazon (Rufus対策モード)
AmazonのAI「Rufus」は、商品ページ内の情報を非常に細かく読み取ります。
* **焦点**: 「事実」と「数値」の網羅。
* **AIへのアプローチ**: 箇条書き1つを100文字以内に収めつつ、スペック（素材・サイズ・対応機種）を凝縮。AIが「はい、入ります」と即答できる文章を作ります。
* **出力**: 規約に準拠した5つの箇条書き。

#### 🔴 楽天 (AI・SEO対策モード)
楽天のAIや検索エンジンは、キーワードの関連性と、レビューに基づいた信頼性を重視します。
* **焦点**: 「共感」と「キーワード」。
* **AIへのアプローチ**: 指定したSEOキーワードを自然に組み込みつつ、レビューで高く評価されているポイントを文章化。「みんなが選んでいる理由」をAIに学習させます。
* **出力**: キャッチコピーに加え、テキスト版と装飾用のHTML版の2種類を生成。

### 3. 入力のコツ（ここが品質を分けます）
AIの精度を最大化するため、以下の情報をスタッフ間で共有してください。
1.  **「補足スペック」をサボらない**: 素材名、ミリ単位のサイズ、耐荷重など。これがないと、AIは「具体的な回答」ができません。
2.  **「低評価レビュー」も入れる**: 「思ったより重かった」というレビューがあれば、AIは「重厚でしっかりした造り」や「安定感を重視した設計」といった、**欠点を強みに変える表現**を提案してくれます。

### 4. 操作上の注意
* **コピーボタン**: 各項目の下のボタンを押すと、クリップボードに保存されます。「コピー完了！」と表示されたら、そのままAmazonセラーセントラルや楽天RMSに貼り付けてください。
