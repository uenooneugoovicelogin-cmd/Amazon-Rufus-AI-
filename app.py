import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="プロ仕様｜モール別AIリライトツール", layout="wide")

def _inject_css() -> None:
    st.markdown("""
    <style>
      :root {
        --bg: #f8f9fa;
        --card: #ffffff;
        --text: #1a1a1a;
        --accent: #007185;
      }
      .stApp { background-color: var(--bg); }
      textarea { background-color: #ffffff !important; border-radius: 8px !important; }
      div.stButton > button {
        background-color: #ffd814 !important;
        border: 1px solid #fcd200 !important;
        color: #111 !important;
        width: 100%;
        font-weight: bold !important;
      }
      .status-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #e7f3f3;
        border-left: 5px solid #007185;
        margin-bottom: 20px;
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
        return {"result_1": "生成エラー", "result_2": response.text}

def main():
    _inject_css()
    st.title("📦 モール別 AI特化型 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 認証・設定")
        api_key = st.text_input("Gemini API Key", type="password", help="Google AI Studioで取得したキー")
        model_id = st.selectbox("使用モデル", ["gemini-1.5-flash", "gemini-2.0-flash"])
        
        st.divider()
        st.header("🎨 出力設定")
        genre = st.selectbox("商品ジャンル", 
                             ["一般雑貨", "ベビー・玩具（PSC注意）", "介護・看護用品", "コスチューム・ホビー", "ペット用品", "園芸・DIY", "スポーツ・アウトドア"])
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・賑やか", "簡潔・ロジカル"])
        
        st.info("※生成された文章は必ず人間が最終確認し、規約・法律違反がないかチェックしてください。")

    tab_amz, tab_rak = st.tabs(["Amazon Rufus対策", "楽天 AI/SEO対策"])

    # ==========================================
    # Amazon タブ
    # ==========================================
    with tab_amz:
        st.markdown('<div class="status-box">Amazon Rufus対策：事実に基づいた論理的な回答と、比較に強い箇条書きを生成します。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            amz_curr = st.text_area("1. 現在の文章（箇条書き・説明文）", height=150, key="amz_c")
            amz_supp = st.text_area("2. 補足スペック・Q&A情報", placeholder="サイズ、重量、素材、よくある質問など", height=100, key="amz_s")
            amz_rev = st.text_area("3. カスタマーレビュー（不満点・好評点）", height=100, key="amz_r")
            
            if st.button("Amazon用リライト実行"):
                if not api_key or not amz_curr:
                    st.error("APIキーと現在の文章は必須です。")
                else:
                    with st.spinner("Amazon Rufus最適化中..."):
                        prompt = f"""あなたはAmazonのシニアコピーライターです。
ジャンル：{genre}、トーン：{tone} でリライトしてください。

【重要ルール】
・不当表示（最大、最高、100%など）の禁止。
・安全基準（PSC等）に関する虚偽表現の禁止。
・他社ブランド名の無断使用禁止。
・事実に基づいた比較しやすい構成。

【現在のデータ】
{amz_curr}
【補足・Q&A】
{amz_supp}
【レビュー】
{amz_rev}

JSON形式で出力：
{{
  "result_1": "修正後の箇条書き5点（各点冒頭に【】で要約、全体で1000文字以内）",
  "result_2": "Rufusが引用しやすい、ターゲットの悩みに寄り添った商品紹介文"
}}"""
                        st.session_state.amz_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "amz_out" in st.session_state:
                st.subheader("✅ 最適化済み：箇条書き")
                st.code(st.session_state.amz_out.get("result_1", ""))
                st.subheader("✅ 最適化済み：紹介文")
                st.write(st.session_state.amz_out.get("result_2", ""))

    # ==========================================
    # 楽天 タブ
    # ==========================================
    with tab_rak:
        st.markdown('<div class="status-box">楽天SEO対策：検索キーワードの網羅と、ユーザーの感情を動かすキャッチコピーを生成します。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            rak_curr = st.text_area("1. 現在の商品説明文", height=150, key="rak_c")
            rak_kw = st.text_area("2. 盛り込みたいキーワード", placeholder="送料無料、あす楽、ランキング1位など", height=100, key="rak_k")
            rak_ben = st.text_area("3. ベネフィット・感動体験", placeholder="この商品で生活がどう変わるか", height=100, key="rak_b")
            
            if st.button("楽天用リライト実行"):
                if not api_key or not rak_curr:
                    st.error("APIキーと現在の文章は必須です。")
                else:
                    with st.spinner("楽天SEO最適化中..."):
                        prompt = f"""あなたは楽天のトップECコンサルタントです。
ジャンル：{genre}、トーン：{tone} でリライトしてください。

【重要ルール】
・「送料無料」「あす楽」等のキーワードを自然に配置。
・スマホ閲覧を意識した、改行の多い読みやすい構成。
・誇大広告、薬機法違反を避けた表現。
・ベネフィット（便益）を強調。

【現在のデータ】
{rak_curr}
【キーワード】
{rak_kw}
【ベネフィット】
{rak_ben}

JSON形式で出力：
{{
  "result_1": "思わずクリックしたくなるキャッチコピー（3案）",
  "result_2": "キーワードを網羅し、ユーザーの背中を押す熱量の高い紹介文"
}}"""
                        st.session_state.rak_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "rak_out" in st.session_state:
                st.subheader("✅ 魅力的なキャッチコピー")
                st.code(st.session_state.rak_out.get("result_1", ""))
                st.subheader("✅ 購買意欲を高める紹介文")
                st.write(st.session_state.rak_out.get("result_2", ""))

if __name__ == "__main__":
    main()
