import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="Amazon Rufus対策 ジェネレーター", layout="wide")

def _inject_css() -> None:
    st.markdown("""
    <style>
      :root {
        --bg: #f4f7f9;
        --card: #ffffff;
        --text: #1a1a1a;
        --accent: #007185;
        --border: #d1d9e0;
      }
      .stApp { background-color: var(--bg); color: var(--text); }
      .card {
        border: 1px solid var(--border);
        background: var(--card);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
      }
      textarea { color: #1a1a1a !important; background-color: #ffffff !important; }
      div.stButton > button {
        background-color: #ffd814 !important;
        border-color: #fcd200 !important;
        color: #111 !important;
        font-weight: bold !important;
        border-radius: 8px !important;
      }
    </style>
    """, unsafe_allow_html=True)

def _call_gemini(api_key: str, model_id: str, bullets: str, reviews: str):
    # APIの初期化
    genai.configure(api_key=api_key)
    
    # 【重要】モデル名の形式を最新の安定版に合わせる
    # ここを 'models/gemini-1.5-flash' に固定することで404エラーを回避します
    model = genai.GenerativeModel(model_name=f"models/{model_id}")
    
    prompt = f"""あなたはAmazonのコピーライターです。
以下の情報を元に、Rufus（Amazon AI）に最適化された「魅力的な箇条書き」と「紹介文」を作成してください。

【現在の箇条書き】
{bullets}

【参考レビュー】
{reviews}

出力は必ず以下のJSON形式にしてください。余計な解説は不要です。：
{{
  "bullets": "修正後の箇条書き（5点）",
  "description": "修正後の紹介文"
}}
"""
    # 生成実行
    response = model.generate_content(prompt)
    
    try:
        # JSON部分の抽出
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception:
        # 失敗した場合は生のテキストを返す
        return {"bullets": "生成失敗", "description": response.text}

def main():
    _inject_css()
    st.title("Amazon Rufus対策 商品紹介文ジェネレーター (Gemini無料版)")
    st.caption("最新のGemini 1.5 Flashモデルを使用して無料でリライトします。")

    with st.sidebar:
        st.header("設定")
        api_key = st.text_input("Gemini API Key", type="password")
        # 選択肢をシンプルにIDのみにする
        model_id = st.selectbox("モデル選択", ["gemini-2.5-flash", "gemini-2.0-flash"])
        st.info("APIキーは Google AI Studio で取得したものを使用してください。")

    col_in, col_out = st.columns(2)

    with col_in:
        st.subheader("元データ入力")
        bullets = st.text_area("現在の箇条書き", placeholder="ここに現在の箇条書きを貼り付けてください", height=200)
        reviews = st.text_area("カスタマーレビュー（任意）", placeholder="レビューを入れるとより精度の高いリライトが可能です", height=150)
        
        if st.button("AI提案を生成"):
            if not api_key:
                st.error("左側のサイドバーにAPIキーを入力してください。")
            elif not bullets:
                st.warning("リライトする元の箇条書きを入力してください。")
            else:
                with st.spinner("AIが考案中..."):
                    try:
                        res = _call_gemini(api_key, model_id, bullets, reviews)
                        st.session_state.res = res
                    except Exception as e:
                        st.error(f"エラーが発生しました: {e}")

    with col_out:
        st.subheader("AI作成案")
        if "res" in st.session_state:
            st.text_area("最適化された箇条書き", value=st.session_state.res.get("bullets", ""), height=200)
            st.text_area("最適化された紹介文", value=st.session_state.res.get("description", ""), height=250)

if __name__ == "__main__":
    main()