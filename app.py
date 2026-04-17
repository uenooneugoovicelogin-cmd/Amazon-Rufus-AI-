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
      .rakuten-box {
        border-left: 5px solid #bf0000;
        background-color: #fdf2f2;
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
        return {"error": "生成エラー", "raw_text": response.text}

def main():
    _inject_css()
    st.title("📦 モール別 AI特化型 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 認証・設定")
        api_key = st.text_input("Gemini API Key", type="password", help="Google AI Studioで取得したキー")
        model_id = st.selectbox("使用モデル", ["gemini-1.5-flash", "gemini-2.0-flash"])
        
        st.divider()
        st.header("🎨 出力設定")
        # ユーザー様の取り扱いジャンルを網羅
        genre = st.selectbox("商品ジャンル", 
                             ["一般雑貨", 
                              "季節行事（ハロウィン・クリスマス等）", 
                              "推し活グッズ・ホビー",
                              "介護・看護・ヘルスケア", 
                              "ベビー・マタニティ", 
                              "ペット用品",
                              "スポーツ・アウトドア",
                              "園芸・ガーデニング・DIY",
                              "キッチン・日用品",
                              "その他（カスタム指示へ）"])
        
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・ベネフィット重視", "簡潔・ロジカル"])
        
        st.info("※生成された文章は必ず人間が最終確認し、法律（PSC法・薬機法）や知財権（キャラクター著作権等）に抵触しないかチェックしてください。")

    tab_amz, tab_rak = st.tabs(["🛒 Amazon Rufus対策", "🔴 楽天 AI/SEO対策"])

    # ==========================================
    # Amazon タブ
    # ==========================================
    with tab_amz:
        st.markdown('<div class="status-box">Amazon仕様：5つの箇条書きスロットと、スマホで読みやすい文字数調整を適用します。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            amz_curr = st.text_area("1. 現在の文章（箇条書き・説明文）", height=150, key="amz_c_input")
            amz_supp = st.text_area("2. 補足スペック・Q&A情報", placeholder="素材、寸法、よくある質問など", height=100, key="amz_s_input")
            amz_rev = st.text_area("3. カスタマーレビュー", placeholder="実際のレビュー内容", height=100, key="amz_r_input")
            
            if st.button("Amazon用リライト実行", key="btn_amz"):
                if not api_key or not amz_curr:
                    st.error("APIキーと現在の文章は必須です。")
                else:
                    with st.spinner("Amazon仕様で生成中..."):
                        prompt = f"""あなたはAmazonのシニアコピーライターです。
ジャンル：{genre}、トーン：{tone} でリライトしてください。

【重要ルール】
1. 箇条書きは必ず「5つ」作成。1項目100文字以内、冒頭に【要約見出し】をつけること。
2. 商品紹介文は全体で600〜800文字以内。見出しや空白（改行）を使い、読みやすく構造化すること。
3. 法律・規約遵守。虚偽記載、他社ブランド名の無断引用は厳禁。

【現在のデータ】
{amz_curr}
【補足・Q&A】
{amz_supp}
【レビュー】
{amz_rev}

JSON形式で出力：
{{
  "bullet_1": "箇条書き1",
  "bullet_2": "箇条書き2",
  "bullet_3": "箇条書き3",
  "bullet_4": "箇条書き4",
  "bullet_5": "箇条書き5",
  "description": "構造化された紹介文"
}}"""
                        st.session_state.amz_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "amz_out" in st.session_state:
                res = st.session_state.amz_out
                if "error" in res:
                    st.error("生成エラーが発生しました。")
                else:
                    st.subheader("📋 箇条書き（5枠個別）")
                    st.text_input("箇条書き 1", value=res.get("bullet_1", ""))
                    st.text_input("箇条書き 2", value=res.get("bullet_2", ""))
                    st.text_input("箇条書き 3", value=res.get("bullet_3", ""))
                    st.text_input("箇条書き 4", value=res.get("bullet_4", ""))
                    st.text_input("箇条書き 5", value=res.get("bullet_5", ""))
                    
                    st.subheader("📝 商品紹介文")
                    desc_text = res.get("description", "")
                    st.text_area("最適化済み紹介文", value=desc_text, height=250)
                    
                    # 文字数カウンター
                    desc_len = len(desc_text)
                    if desc_len > 1000:
                        st.error(f"⚠️ 文字数：{desc_len}文字（長すぎます）")
                    else:
                        st.success(f"✅ 文字数：{desc_len}文字（適正）")

    # ==========================================
    # 楽天 タブ
    # ==========================================
    with tab_rak:
        st.markdown('<div class="status-box rakuten-box">楽天仕様：キーワードを網羅し、RMS直貼り用のHTMLタグ付き文章も生成します。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            rak_curr = st.text_area("1. 現在の商品説明文", height=150, key="rak_c_input")
            rak_kw = st.text_area("2. 盛り込みたいキーワード", placeholder="送料無料、あす楽など", height=100, key="rak_k_input")
            rak_ben = st.text_area("3. ベネフィット・レビュー", placeholder="使用感やメリット", height=100, key="rak_b_input")
            
            if st.button("楽天用リライト実行", key="btn_rak"):
                if not api_key or not rak_curr:
                    st.error("APIキーと現在の文章は必須です。")
                else:
                    with st.spinner("楽天SEO最適化中..."):
                        prompt = f"""あなたは楽天のトップECコンサルタントです。
ジャンル：{genre}、トーン：{tone} でリライトしてください。

【重要ルール】
1. 指定キーワードを自然に網羅。
2. 商品説明文は800〜1000文字程度。
3. プレーンテキスト版と、RMS用に <b> や <br> タグを適度に使用したHTML版を作成すること。

【データ】{rak_curr} / 【KW】{rak_kw} / 【ベネフィット】{rak_ben}

JSON形式で出力：
{{
  "catchcopy": "魅力的なキャッチコピー",
  "desc_text": "テキスト版",
  "desc_html": "HTMLタグ付き版"
}}"""
                        st.session_state.rak_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "rak_out" in st.session_state:
                res = st.session_state.rak_out
                if "error" in res:
                    st.error("エラー")
                else:
                    st.subheader("🎯 キャッチコピー")
                    st.text_input("コピー", value=res.get("catchcopy", ""))
                    st.subheader("📝 テキスト版")
                    st.text_area("通常テキスト", value=res.get("desc_text", ""), height=200)
                    st.subheader("💻 楽天RMS用（HTMLコード）")
                    st.code(res.get("desc_html", ""), language="html")

if __name__ == "__main__":
    main()
