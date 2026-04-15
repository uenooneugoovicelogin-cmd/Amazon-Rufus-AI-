import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="モール別 AI特化型 商品紹介文生成ツール", layout="wide")

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

def _call_gemini(api_key: str, model_id: str, prompt_text: str):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=f"models/{model_id}")
    response = model.generate_content(prompt_text)
    try:
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception:
        return {"result_1": "JSONパース失敗", "result_2": response.text}

def main():
    _inject_css()
    st.title("モール別 AI特化型 商品紹介文ジェネレーター")

    with st.sidebar:
        st.header("設定")
        api_key = st.text_input("Gemini API Key", type="password")
        model_id = st.selectbox("モデル選択", ["gemini-1.5-flash", "gemini-2.0-flash"])
        st.info("APIキーを入力して使用してください。")

    tab_amazon, tab_rakuten = st.tabs(["🛒 Amazon (Rufus対策)", "🔴 楽天 (AI・SEO対策)"])

    # ==========================================
    # Amazon タブ
    # ==========================================
    with tab_amazon:
        col_amz_in, col_amz_out = st.columns(2)
        with col_amz_in:
            st.subheader("Amazon入力データ")
            amz_specs = st.text_area("1. 商品の特徴・スペック", placeholder="例：300gと軽量、防水IPX7...", height=100, key="amz_specs")
            amz_qa = st.text_area("2. 想定される質問への回答", placeholder="例：Q.食洗機は使えますか？ A.はい...", height=100, key="amz_qa")
            amz_reviews = st.text_area("3. カスタマーレビュー（重要）", placeholder="実際のレビューを貼り付けるとRufus対策の精度が上がります", height=150, key="amz_reviews")
            
            if st.button("Amazon用を生成", key="btn_amz"):
                if not api_key or not amz_specs:
                    st.error("APIキーと特徴を入力してください。")
                else:
                    with st.spinner("生成中..."):
                        amz_prompt = f"""あなたはAmazon専門コピーライターです。Rufus（会話型AI）向けに、以下の情報を元に客観的で信頼性の高い文章を作ってください。
【特徴】{amz_specs}
【Q&A】{amz_qa}
【レビュー】{amz_reviews}
JSON形式で出力：{{"result_1": "修正後の箇条書き5点", "result_2": "Rufusが引用しやすい紹介文"}}"""
                        st.session_state.amz_res = _call_gemini(api_key, model_id, amz_prompt)

        with col_amz_out:
            st.subheader("Amazon生成結果")
            if "amz_res" in st.session_state:
                st.text_area("最適化された箇条書き", value=st.session_state.amz_res.get("result_1", ""), height=200)
                st.text_area("最適化された紹介文", value=st.session_state.amz_res.get("result_2", ""), height=250)

    # ==========================================
    # 楽天 タブ
    # ==========================================
    with tab_rakuten:
        col_rak_in, col_rak_out = st.columns(2)
        with col_rak_in:
            st.subheader("楽天入力データ")
            rak_benefits = st.text_area("1. 商品のベネフィット", placeholder="例：毎朝の準備が5分短縮！", height=100, key="rak_benefits")
            rak_keywords = st.text_area("2. 盛り込みたいキーワード", placeholder="例：送料無料, 母の日...", height=100, key="rak_keywords")
            rak_ref = st.text_area("3. 参考情報・レビュー", placeholder="楽天での悩み事や過去のレビューなど", height=150, key="rak_ref")
            
            if st.button("楽天用を生成", key="btn_rak"):
                if not api_key or not rak_benefits:
                    st.error("APIキーとベネフィットを入力してください。")
                else:
                    with st.spinner("生成中..."):
                        rak_prompt = f"""あなたは楽天ECコンサルタントです。AIと検索SEO、顧客心理を意識した熱量の高い文章を作ってください。
【ベネフィット】{rak_benefits}
【キーワード】{rak_keywords}
【参考】{rak_ref}
JSON形式で出力：{{"result_1": "魅力的なキャッチコピー案", "result_2": "キーワードを網羅した紹介文"}}"""
                        st.session_state.rak_res = _call_gemini(api_key, model_id, rak_prompt)

        with col_rak_out:
            st.subheader("楽天生成結果")
            if "rak_res" in st.session_state:
                st.text_area("キャッチコピー案", value=st.session_state.rak_res.get("result_1", ""), height=200)
                st.text_area("最適化された紹介文", value=st.session_state.rak_res.get("result_2", ""), height=250)

if __name__ == "__main__":
    main()
