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

def _call_gemini(api_key: str, model_id: str, prompt_text: str):
    # APIの初期化
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=f"models/{model_id}")
    
    # 生成実行
    response = model.generate_content(prompt_text)
    
    try:
        # JSON部分の抽出
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception:
        # 失敗した場合は生のテキストをダミーの辞書に入れて返す
        return {"result_1": "JSONパース失敗", "result_2": response.text}

def main():
    _inject_css()
    st.title("モール別 AI特化型 商品紹介文ジェネレーター")
    st.caption("Amazon Rufusと楽天AI、それぞれのアルゴリズムに最適化した文章を生成します。")

    with st.sidebar:
        st.header("設定")
        api_key = st.text_input("Gemini API Key", type="password")
        model_id = st.selectbox("モデル選択", ["gemini-2.5-flash", "gemini-2.0-flash"])
        st.info("各自のGoogle AI Studioで取得したAPIキーを入力してください。")

    # --- タブの作成 ---
    tab_amazon, tab_rakuten = st.tabs(["🛒 Amazon (Rufus対策)", "🔴 楽天 (AI・SEO対策)"])

    # ==========================================
    # Amazon タブ
    # ==========================================
    with tab_amazon:
        col_amz_in, col_amz_out = st.columns(2)
        
        with col_amz_in:
            st.subheader("商品情報入力（事実・客観ベース）")
            amz_specs = st.text_area("商品の特徴・スペック", placeholder="例：300gと軽量、防水IPX7、連続再生10時間...", height=150, key="amz_specs")
            amz_qa = st.text_area("想定される質問への回答", placeholder="例：Q.食洗機は使えますか？ A.はい、可能です。\nQ.保証期間は？ A.1年間です。", height=150, key="amz_qa")
            
            if st.button("Amazon用を生成", key="btn_amz"):
                if not api_key:
                    st.error("サイドバーにAPIキーを入力してください。")
                elif not amz_specs:
                    st.warning("商品の特徴を入力してください。")
                else:
                    with st.spinner("Amazon Rufus向けに論理的に構成中..."):
                        amz_prompt = f"""あなたはAmazonの専門コピーライターです。
以下の情報を元に、Amazonの会話型AI（Rufus）が顧客の質問に答えやすく、比較検討しやすいように「客観的で事実に基づいた」文章を作成してください。

【商品の特徴・スペック】
{amz_specs}

【想定される質問への回答】
{amz_qa}

出力は必ず以下のJSON形式にしてください。余計な解説は不要です。：
{{
  "result_1": "商品の要点をまとめた箇条書き（事実ベースで5点）",
  "result_2": "比較検討しやすい、具体的で分かりやすい紹介文"
}}
"""
                        try:
                            st.session_state.amz_res = _call_gemini(api_key, model_id, amz_prompt)
                        except Exception as e:
                            st.error(f"エラーが発生しました: {e}")

        with col_amz_out:
            st.subheader("生成結果 (Amazon Rufus最適化)")
            if "amz_res" in st.session_state:
                st.text_area("最適化された箇条書き", value=st.session_state.amz_res.get("result_1", ""), height=200, key="amz_out_1")
                st.text_area("最適化された紹介文", value=st.session_state.amz_res.get("result_2", ""), height=250, key="amz_out_2")

    # ==========================================
    # 楽天 タブ
    # ==========================================
    with tab_rakuten:
        col_rak_in, col_rak_out = st.columns(2)
        
        with col_rak_in:
            st.subheader("商品情報入力（感情・キーワードベース）")
            rak_benefits = st.text_area("商品のベネフィット（感動体験）", placeholder="例：毎朝の準備が5分短縮！もう満員電車で汗だくになりません。", height=150, key="rak_benefits")
            rak_keywords = st.text_area("盛り込みたいキーワード", placeholder="例：送料無料, 母の日, 日本製, おしゃれ, ランキング1位...", height=150, key="rak_keywords")
            
            if st.button("楽天用を生成", key="btn_rak"):
                if not api_key:
                    st.error("サイドバーにAPIキーを入力してください。")
                elif not rak_benefits:
                    st.warning("商品のベネフィットを入力してください。")
                else:
                    with st.spinner("楽天AI・SEO向けにキャッチーに構成中..."):
                        rak_prompt = f"""あなたは楽天市場の凄腕ECコンサルタントです。
以下の情報を元に、楽天の検索エンジン（AI）と顧客の感情に強く訴え求求心力のある文章を作成してください。
ベネフィット（便益）と指定されたキーワードを最大限に活用してください。

【商品のベネフィット（感動体験）】
{rak_benefits}

【盛り込みたいキーワード】
{rak_keywords}

出力は必ず以下のJSON形式にしてください。余計な解説は不要です。：
{{
  "result_1": "検索に引っかかりやすく、クリックしたくなる魅力的なキャッチコピー（3点）",
  "result_2": "キーワードを自然に盛り込み、購買意欲を強く煽る熱量のある紹介文"
}}
"""
                        try:
                            st.session_state.rak_res = _call_gemini(api_key, model_id, rak_prompt)
                        except Exception as e:
                            st.error(f"エラーが発生しました: {e}")

        with col_rak_out:
            st.subheader("生成結果 (楽天AI/SEO最適化)")
            if "rak_res" in st.session_state:
                st.text_area("キャッチコピー案", value=st.session_state.rak_res.get("result_1", ""), height=200, key="rak_out_1")
                st.text_area("最適化された紹介文", value=st.session_state.rak_res.get("result_2", ""), height=250, key="rak_out_2")

if __name__ == "__main__":
    main()
