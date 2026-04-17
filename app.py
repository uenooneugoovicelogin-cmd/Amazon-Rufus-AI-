import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定とブランディング復元 ---
st.set_page_config(page_title="Wonder Plaza｜モール別AIリライトツール", layout="wide")

def _inject_css():
    st.markdown("""
    <style>
      :root { --bg: #f0f2f6; --accent: #007185; }
      .stApp { background-color: var(--bg); }
      /* Amazon風の黄色ボタン */
      div.stButton > button {
        background-color: #ffd814 !important; border: 1px solid #fcd200 !important;
        color: #111 !important; width: 100%; font-weight: bold !important;
        height: 3em; border-radius: 8px !important;
      }
      .status-box {
        padding: 15px; border-radius: 10px; background-color: #ffffff;
        border-left: 6px solid #007185; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      }
      h1 { color: #232f3e; font-size: 24px !important; }
    </style>
    """, unsafe_allow_html=True)

def _call_gemini(api_key, model_name, prompt):
    """404エラーを完全に回避するための安全な呼び出し"""
    try:
        genai.configure(api_key=api_key)
        # モデル名に接頭辞が必要か不要かをライブラリに任せる
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        
        # テキストからJSONを抽出（マークダウン記法 ```json ... ``` があっても除去）
        raw_res = response.text
        if "```" in raw_res:
            raw_res = raw_res.split("```")[1].replace("json", "").strip()
        
        return json.loads(raw_res)
    except Exception as e:
        return {"error": str(e)}

def main():
    _inject_css()
    st.title("📦 Wonder Plaza｜モール別AIリライトツール")
    
    with st.sidebar:
        st.header("🔑 接続設定")
        api_key = st.text_input("Gemini API Key", type="password", help="Google AI Studioで発行したキーを入力")
        
        # --- 自動モデル取得機能 ---
        model_choice = "gemini-1.5-flash" # デフォルト
        if api_key:
            try:
                genai.configure(api_key=api_key)
                available_models = [m.name.replace('models/', '') for m in genai.list_models() 
                                   if 'generateContent' in m.supported_generation_methods]
                model_choice = st.selectbox("使用モデル（自動取得済）", available_models)
            except:
                st.error("APIキーが無効か、通信エラーです。")
                model_choice = st.selectbox("使用モデル（手動）", ["gemini-1.5-flash", "gemini-1.5-pro"])
        
        st.divider()
        st.header("🎨 リライト設定")
        # ユーザー様の全カテゴリーを復元
        genre = st.selectbox("商品ジャンル", [
            "一般雑貨", "季節行事（ハロウィン・クリスマス等）", "推し活グッズ・ホビー",
            "介護・看護・ヘルスケア", "ベビー・マタニティ", "ペット用品",
            "スポーツ・アウトドア", "園芸・ガーデニング・DIY", "キッチン・日用品", "その他"
        ])
        
        tone = st.radio("文章のトーン", [
            "誠実・信頼（規約遵守・丁寧）", 
            "情熱的（ベネフィット・購買意欲重視）", 
            "簡潔・ロジカル（スペック重視）"
        ])

    tab_amz, tab_rak = st.tabs(["🛒 Amazon Rufus対策", "🔴 楽天 AI/SEO対策"])

    # --- Amazon タブ ---
    with tab_amz:
        st.markdown('<div class="status-box"><b>Amazon仕様:</b> 5つの箇条書き（各100文字以内）と、スマホで読みやすい紹介文。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        with col1:
            amz_curr = st.text_area("1. 現在の商品説明", height=150, placeholder="既存の文章や箇条書きを入力")
            amz_supp = st.text_area("2. 補足（素材・サイズ・Q&A）", height=100, placeholder="1688等のスペック情報")
            amz_rev = st.text_area("3. レビュー（任意）", height=100, placeholder="レビュー内容を反映してRufusの回答精度を上げます")
            
            if st.button("Amazon用リライト実行"):
                if not api_key or not amz_curr:
                    st.error("APIキーと説明文を入力してください。")
                else:
                    with st.spinner("AIが生成中..."):
                        prompt = f"""
                        Amazonの商品リライト。ジャンル:{genre}、トーン:{tone}。
                        以下を厳守し、JSON形式で出力せよ。
                        1. bullet_1〜5: 各100文字以内の箇条書き。
                        2. description: 600文字程度の自然な商品紹介文。
                        データ: {amz_curr} / {amz_supp} / {amz_rev}
                        """
                        st.session_state.amz_res = _call_gemini(api_key, model_choice, prompt)

        with col2:
            if "amz_res" in st.session_state:
                res = st.session_state.amz_res
                if "error" in res:
                    st.error(f"エラーが発生しました: {res['error']}")
                else:
                    st.subheader("📋 箇条書き（スロット1-5）")
                    for i in range(1, 6):
                        st.text_input(f"箇条書き {i}", value=res.get(f"bullet_{i}", ""))
                    st.subheader("📝 商品紹介文")
                    st.text_area("全文コピー用", value=res.get("description", ""), height=250)

    # --- 楽天 タブ ---
    with tab_rak:
        st.markdown('<div class="status-box"><b>楽天仕様:</b> キャッチコピー、PC/スマホ共通説明文、HTMLタグ生成。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        with col1:
            rak_curr = st.text_area("現在の文章", height=150, key="rak_c")
            rak_kw = st.text_area("盛り込みたいキーワード", height=100, placeholder="送料無料, おまけ付, 即納など", key="rak_k")
            if st.button("楽天用リライト実行"):
                if not api_key: st.error("APIキーを入力してください")
                else:
                    with st.spinner("楽天SEO最適化中..."):
                        prompt = f"楽天用リライト。catchcopy, desc_text, desc_html(bタグbrタグ使用)をJSONで作成。ジャンル:{genre}。KW:{rak_kw} データ:{rak_curr}"
                        st.session_state.rak_res = _call_gemini(api_key, model_choice, prompt)

        with col2:
            if "rak_res" in st.session_state:
                res = st.session_state.rak_res
                if "error" in res:
                    st.error(res['error'])
                else:
                    st.text_input("キャッチコピー（全角60文字以内）", value=res.get("catchcopy", ""))
                    st.text_area("商品説明（テキスト版）", value=res.get("desc_text", ""), height=200)
                    st.subheader("💻 RMS用HTML")
                    st.code(res.get("desc_html", ""), language="html")

if __name__ == "__main__":
    main()
