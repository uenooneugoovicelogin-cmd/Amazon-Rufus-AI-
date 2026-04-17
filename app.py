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
        # 実務に合わせたジャンル展開
        genre = st.selectbox("商品ジャンル", 
                             ["一般雑貨", 
                              "イベント・パーティグッズ（ハロウィン・クリスマス等）", 
                              "介護・看護用品", 
                              "ベビー・ペット用品", 
                              "園芸・DIY・スポーツ"])
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・ベネフィット重視", "簡潔・ロジカル"])
        
        st.info("※生成された文章は必ず人間が最終確認し、PSC法などの安全基準や、キャラクター知財等の権利侵害がないかチェックしてください。")

    tab_amz, tab_rak = st.tabs(["🛒 Amazon Rufus対策", "🔴 楽天 AI/SEO対策"])

    # ==========================================
    # Amazon タブ
    # ==========================================
    with tab_amz:
        st.markdown('<div class="status-box">Amazon仕様：5つの箇条書きスロットと、スマホで読みやすい文字数制限（約600〜800文字）を適用します。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            amz_curr = st.text_area("1. 現在の文章（箇条書き・説明文）", height=150)
            amz_supp = st.text_area("2. 補足スペック・Q&A情報", placeholder="素材、寸法、よくある質問（食洗機可否など）", height=100)
            amz_rev = st.text_area("3. カスタマーレビュー", placeholder="実際のレビューを入れるとRufus対策の精度が上がります", height=100)
            
            if st.button("Amazon用リライト実行", key="btn_amz"):
                if not api_key or not amz_curr:
                    st.error("APIキーと現在の文章は必須です。")
                else:
                    with st.spinner("Amazon仕様（5項目分割・文字数調整）で生成中..."):
                        prompt = f"""あなたはAmazonのシニアコピーライターです。
ジャンル：{genre}、トーン：{tone} でリライトしてください。

【重要ルール】
1. 箇条書きは必ず「5つ」作成し、1つあたり100文字以内、冒頭に【】で見出しをつけること。
2. 商品紹介文は全体で600〜800文字以内。見出しや空白（改行）を使い、スマホで拾い読みしやすい構造にすること。
3. 誇大表現、安全基準（PSC等）に関する虚偽表現、他社ブランド名（キャラクター名等）の無断使用は厳禁。

【現在のデータ】
{amz_curr}
【補足・Q&A】
{amz_supp}
【レビュー】
{amz_rev}

JSON形式で出力：
{{
  "bullet_1": "1つ目の箇条書き",
  "bullet_2": "2つ目の箇条書き",
  "bullet_3": "3つ目の箇条書き",
  "bullet_4": "4つ目の箇条書き",
  "bullet_5": "5つ目の箇条書き",
  "description": "Rufusが引用しやすく、ユーザーが読みやすい構造化された紹介文"
}}"""
                        st.session_state.amz_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "amz_out" in st.session_state:
                res = st.session_state.amz_out
                if "error" in res:
                    st.error("生成に失敗しました。もう一度お試しください。")
                else:
                    st.subheader("📋 箇条書き（セラーセントラル用5枠）")
                    st.caption("※各テキストボックスの中身をコピペして使えます")
                    st.text_input("箇条書き 1", value=res.get("bullet_1", ""))
                    st.text_input("箇条書き 2", value=res.get("bullet_2", ""))
                    st.text_input("箇条書き 3", value=res.get("bullet_3", ""))
                    st.text_input("箇条書き 4", value=res.get("bullet_4", ""))
                    st.text_input("箇条書き 5", value=res.get("bullet_5", ""))
                    
                    st.subheader("📝 商品紹介文")
                    desc_text = res.get("description", "")
                    st.text_area("スマホ最適化済み紹介文", value=desc_text, height=250)
                    
                    # 文字数カウンターと警告
                    desc_len = len(desc_text)
                    if desc_len > 1000:
                        st.error(f"⚠️ 現在の文字数：{desc_len}文字（長すぎます。手動で削るか再生成してください）")
                    else:
                        st.success(f"✅ 現在の文字数：{desc_len}文字（適正な長さです）")

    # ==========================================
    # 楽天 タブ
    # ==========================================
    with tab_rak:
        st.markdown('<div class="status-box rakuten-box">楽天仕様：キーワードを網羅し、RMSにそのまま貼れるHTMLタグ付き文章も生成します。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            rak_curr = st.text_area("1. 現在の商品説明文", height=150, key="rak_c")
            rak_kw = st.text_area("2. 盛り込みたいキーワード", placeholder="送料無料、あす楽、母の日、お買い物マラソンなど", height=100)
            rak_ben = st.text_area("3. ベネフィット・感動体験", placeholder="この商品で生活がどう変わるか", height=100)
            
            if st.button("楽天用リライト実行", key="btn_rak"):
                if not api_key or not rak_curr:
                    st.error("APIキーと現在の文章は必須です。")
                else:
                    with st.spinner("楽天SEO最適化＆HTML生成中..."):
                        prompt = f"""あなたは楽天のトップECコンサルタントです。
ジャンル：{genre}、トーン：{tone} でリライトしてください。

【重要ルール】
1. 指定キーワードを不自然にならないよう網羅すること。
2. 商品説明文は800〜1000文字程度で、読者の感情を動かす構成にすること。
3. 通常のテキスト版に加え、RMS（楽天管理画面）用に、重要なキーワードや見出しを <b> や <br> タグで装飾したHTML版も作成すること。

【現在のデータ】
{rak_curr}
【キーワード】
{rak_kw}
【ベネフィット】
{rak_ben}

JSON形式で出力：
{{
  "catchcopy": "検索結果で目立つ、魅力的なキャッチコピー（1案、最大60文字）",
  "desc_text": "プレーンテキスト版の紹介文",
  "desc_html": "<b>や<br>タグを含めた、RMSにそのまま貼れるHTML版の紹介文"
}}"""
                        st.session_state.rak_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "rak_out" in st.session_state:
                res = st.session_state.rak_out
                if "error" in res:
                    st.error("生成に失敗しました。もう一度お試しください。")
                else:
                    st.subheader("🎯 キャッチコピー")
                    st.text_input("商品名やPCキャッチコピー欄へ", value=res.get("catchcopy", ""))
                    
                    st.subheader("📝 商品説明文（プレーンテキスト）")
                    st.text_area("スマホ用などの通常テキスト", value=res.get("desc_text", ""), height=200)
                    
                    st.subheader("💻 楽天RMS用（HTMLタグ付き）")
                    st.caption("※これをコピーしてPC用商品説明文に貼ると、自動で太字や改行が反映されます")
                    st.code(res.get("desc_html", ""), language="html")

if __name__ == "__main__":
    main()
