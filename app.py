import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="プロ仕様｜モール別AIリライトツール", layout="wide")

def _inject_css() -> None:
    st.markdown("""
    <style>
      :root { --bg: #f8f9fa; --accent: #007185; }
      .stApp { background-color: var(--bg); }
      textarea, input { background-color: #ffffff !important; border-radius: 8px !important; }
      div.stButton > button {
        background-color: #ffd814 !important;
        border: 1px solid #fcd200 !important;
        color: #111 !important;
        width: 100%;
        font-weight: bold !important;
      }
      .status-box {
        padding: 10px; border-radius: 5px; background-color: #e7f3f3;
        border-left: 5px solid #007185; margin-bottom: 20px;
      }
    </style>
    """, unsafe_allow_html=True)

def _call_gemini(api_key: str, model_id: str, prompt_text: str):
    """AI呼び出し関数（404エラー対策版）"""
    try:
        genai.configure(api_key=api_key)
        # エラー対策：models/ などの接頭辞を一切付けず、選択された名前をそのまま使用
        model = genai.GenerativeModel(model_name=model_id)
        
        response = model.generate_content(prompt_text)
        
        # JSON抽出
        res_text = response.text
        clean_text = res_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        return {"error_msg": str(e)}

def main():
    _inject_css()
    st.title("📦 モール別 AI特化型 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 認証・設定")
        api_key = st.text_input("Gemini API Key", type="password")
        # モデル名をシステムが認識しやすい形式に変更
        model_id = st.selectbox("使用モデル", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"])
        
        st.divider()
        st.header("🎨 出力設定")
        # ユーザー様の全カテゴリーを復元
        genre = st.selectbox("商品ジャンル", 
                             ["一般雑貨", "季節行事（ハロウィン・クリスマス等）", "推し活グッズ・ホビー",
                              "介護・看護・ヘルスケア", "ベビー・マタニティ", "ペット用品",
                              "スポーツ・アウトドア", "園芸・ガーデニング・DIY", "キッチン・日用品", "その他"])
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・ベネフィット重視", "簡潔・ロジカル"])

    tab_amz, tab_rak = st.tabs(["🛒 Amazon Rufus対策", "🔴 楽天 AI/SEO対策"])

    # --- Amazon タブ ---
    with tab_amz:
        st.markdown('<div class="status-box">Amazon仕様：5つの箇条書きと、スマホで見やすい紹介文。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        with col1:
            amz_curr = st.text_area("1. 現在の文章", height=150, key="amz_c")
            amz_supp = st.text_area("2. 補足スペック", placeholder="寸法、素材、Q&Aなど", height=100, key="amz_s")
            amz_rev = st.text_area("3. カスタマーレビュー", placeholder="レビューを入れるとRufus対策が強化されます", height=100, key="amz_r")
            
            if st.button("Amazon用リライト実行"):
                if not api_key or not amz_curr:
                    st.error("入力が不足しています。")
                else:
                    with st.spinner("Amazon最適化中..."):
                        prompt = f"""Amazon用リライト。ジャンル:{genre}、トーン:{tone}。
                        以下のデータを元に、箇条書き5つ(bullet_1〜5、各100文字以内)と、
                        スマホで読みやすい600-800文字の紹介文(description)をJSONで作成してください。
                        データ：{amz_curr} / {amz_supp} / {amz_rev}"""
                        st.session_state.amz_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "amz_out" in st.session_state:
                res = st.session_state.amz_out
                if "error_msg" in res:
                    st.error(f"エラーが発生しました：\n{res['error_msg']}")
                else:
                    st.subheader("📋 箇条書き（5項目）")
                    for i in range(1, 6):
                        st.text_input(f"スロット {i}", value=res.get(f"bullet_{i}", ""), key=f"amz_b_{i}")
                    st.subheader("📝 商品紹介文")
                    desc = res.get("description", "")
                    st.text_area("紹介文本体", value=desc, height=250)
                    st.caption(f"現在の文字数：{len(desc)}文字")

    # --- 楽天 タブ ---
    with tab_rak:
        st.markdown('<div class="status-box">楽天仕様：SEOキーワード網羅とHTMLタグ生成。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        with col1:
            rak_curr = st.text_area("1. 現在の文章", height=150, key="rak_c")
            rak_kw = st.text_area("2. 盛り込みたいキーワード", height=100, key="rak_k")
            if st.button("楽天用リライト実行"):
                if not api_key or not rak_curr:
                    st.error("入力が不足しています。")
                else:
                    with st.spinner("楽天最適化中..."):
                        prompt = f"""楽天用リライト。ジャンル:{genre}。
                        catchcopy, desc_text, desc_html(bタグbrタグ使用) をJSONで作成してください。
                        キーワード：{rak_kw} / データ：{rak_curr}"""
                        st.session_state.rak_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "rak_out" in st.session_state:
                res = st.session_state.rak_out
                if "error_msg" in res:
                    st.error(f"エラー：{res['error_msg']}")
                else:
                    st.text_input("キャッチコピー", value=res.get("catchcopy", ""))
                    st.text_area("テキスト説明文", value=res.get("desc_text", ""), height=200)
                    st.subheader("💻 RMS用HTML")
                    st.code(res.get("desc_html", ""), language="html")

if __name__ == "__main__":
    main()
