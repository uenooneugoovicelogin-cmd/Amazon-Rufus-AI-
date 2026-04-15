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
            st.subheader("Amazon現在のデータ & 補足情報")
            amz_current = st.text_area("1. 現在の商品説明・箇条書き", placeholder="現在使用中の文章をここに貼り付けてください", height=150, key="amz_current")
            amz_qa = st.text_area("2. Q&A・スペック情報", placeholder="Rufusが回答に使いそうな事実情報を入力（例：防水性能、サイズ感など）", height=100, key="amz_qa")
            amz_reviews = st.text_area("3. カスタマーレビュー", placeholder="実際のレビューを貼り付けると、不満の解消や利点の強調が強化されます", height=100, key="amz_reviews")
            
            if st.button("Amazon用を生成", key="btn_amz"):
                if not api_key or not amz_current:
                    st.error("APIキーと現在の文章を入力してください。")
                else:
                    with st.spinner("Amazon Rufus向けにリライト中..."):
                        amz_prompt = f"""あなたはAmazon専門のコピーライターです。
現在の文章をベースに、Amazonの会話型AI（Rufus）が「顧客の疑問に答えやすく」かつ「比較検討で選ばれやすい」内容にリライトしてください。

【現在の文章】
{amz_current}
【補足スペック・Q&A】
{amz_qa}
【カスタマーレビュー】
{amz_reviews}

出力は必ず以下のJSON形式にしてください。：
{{
  "result_1": "修正後の箇条書き（5点）",
  "result_2": "Rufus対策済みの商品紹介文"
}}"""
                        st.session_state.amz_res = _call_gemini(api_key, model_id, amz_prompt)

        with col_amz_out:
            st.subheader("Amazon生成結果")
            if "amz_res" in st.session_state:
                st.text_area("最適化された箇条書き", value=st.session_state.amz_res.get("result_1", ""), height=200)
                st.text_area("最適化された紹介文", value=st.session_state.amz_res.get("result_2", ""), height=300)

    # ==========================================
    # 楽天 タブ
    # ==========================================
    with tab_rakuten:
        col_rak_in, col_rak_out = st.columns(2)
        with col_rak_in:
            st.subheader("楽天現在のデータ & 補足情報")
            rak_current = st.text_area("1. 現在の商品説明文", placeholder="現在使用中の文章をここに貼り付けてください", height=150, key="rak_current")
            rak_keywords = st.text_area("2. 盛り込みたいキーワード", placeholder="送料無料、あす楽、母の日、ランキング受賞など", height=100, key="rak_keywords")
            rak_benefits = st.text_area("3. ベネフィット・レビュー情報", placeholder="ユーザーが手にする感動体験や、過去の好評なレビュー内容など", height=100, key="rak_benefits")
            
            if st.button("楽天用を生成", key="btn_rak"):
                if not api_key or not rak_current:
                    st.error("APIキーと現在の文章を入力してください。")
                else:
                    with st.spinner("楽天AI・SEO向けにリライト中..."):
                        rak_prompt = f"""あなたは楽天ECコンサルタントです。
現在の文章をベースに、楽天の検索AIに評価されやすく、かつユーザーの購買意欲を煽る熱量の高い文章にリライトしてください。

【現在の文章】
{rak_current}
【キーワード】
{rak_keywords}
【ベネフィット・参考情報】
{rak_benefits}

出力は必ず以下のJSON形式にしてください。：
{{
  "result_1": "魅力的なキャッチコピー案（3点）",
  "result_2": "キーワードを網羅し、ベネフィットを強調した紹介文"
}}"""
                        st.session_state.rak_res = _call_gemini(api_key, model_id, rak_prompt)

        with col_rak_out:
            st.subheader("楽天生成結果")
            if "rak_res" in st.session_state:
                st.text_area("キャッチコピー案", value=st.session_state.rak_res.get("result_1", ""), height=200)
                st.text_area("最適化された紹介文", value=st.session_state.rak_res.get("result_2", ""), height=300)

if __name__ == "__main__":
    main()
