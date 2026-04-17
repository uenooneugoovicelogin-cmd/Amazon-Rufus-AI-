import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定と新アプリ名 ---
st.set_page_config(page_title="Rufus ＆楽天AI モール別AI対策ツール", layout="wide")

def _inject_css_and_js():
    # CSS: デザイン調整
    st.markdown("""
    <style>
      :root { --bg: #f0f2f6; --accent: #007185; }
      .stApp { background-color: var(--bg); }
      div.stButton > button {
        background-color: #ffd814 !important; border: 1px solid #fcd200 !important;
        color: #111 !important; width: 100%; font-weight: bold !important;
        border-radius: 8px !important;
      }
      /* コピーボタン専用スタイル */
      .copy-btn-style > div > button {
        background-color: #e7f3f3 !important; border: 1px solid #007185 !important;
        color: #007185 !important; height: 2.5em !important; font-size: 0.8em !important;
      }
      .status-box {
        padding: 15px; border-radius: 10px; background-color: #ffffff;
        border-left: 6px solid #007185; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      }
    </style>
    """, unsafe_allow_html=True)

def copy_to_clipboard(text, label):
    """ワンクリックコピー機能を実現するヘルパー"""
    if st.button(f"📋 {label}をコピー", key=f"btn_{label}", help="クリックでコピー"):
        st.write(f'<script>navigator.clipboard.writeText(`{text}`);</script>', unsafe_allow_html=True)
        st.toast(f"✅ {label}をコピーしました！")

def _call_gemini(api_key, model_name, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        raw_res = response.text
        if "```" in raw_res:
            raw_res = raw_res.split("```")[1].replace("json", "").strip()
        return json.loads(raw_res)
    except Exception as e:
        return {"error": str(e)}

def main():
    _inject_css_and_js()
    st.title("📦 Rufus ＆楽天AI モール別AI対策ツール")
    
    with st.sidebar:
        st.header("🔑 接続設定")
        api_key = st.text_input("Gemini API Key", type="password")
        
        # モデル自動取得
        model_choice = "gemini-1.5-flash"
        if api_key:
            try:
                genai.configure(api_key=api_key)
                available_models = [m.name.replace('models/', '') for m in genai.list_models() 
                                   if 'generateContent' in m.supported_generation_methods]
                model_choice = st.selectbox("使用モデル", available_models)
            except:
                model_choice = st.selectbox("使用モデル（手動）", ["gemini-1.5-flash", "gemini-1.5-pro"])
        
        st.divider()
        st.header("🎨 出力設定")
        genre = st.selectbox("商品ジャンル", [
            "一般雑貨", "季節行事（ハロウィン・クリスマス等）", "推し活グッズ・ホビー",
            "介護・看護・ヘルスケア", "ベビー・マタニティ", "ペット用品",
            "スポーツ・アウトドア", "園芸・ガーデニング・DIY", "キッチン・日用品", "その他"
        ])
        tone = st.radio("文章のトーン", ["誠実・信頼", "情熱的", "簡潔・ロジカル"])

    tab_amz, tab_rak = st.tabs(["🛒 Amazon Rufus対策", "🔴 楽天 AI/SEO対策"])

    # --- Amazon タブ ---
    with tab_amz:
        st.markdown('<div class="status-box">Amazon仕様: 5つの箇条書きとスマホ最適化紹介文。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        with col1:
            amz_curr = st.text_area("1. 現在の商品説明", height=150, key="amz_c")
            amz_supp = st.text_area("2. 補足（スペック等）", height=100, key="amz_s")
            amz_rev = st.text_area("3. カスタマーレビュー", height=100, key="amz_r")
            
            if st.button("Amazon用リライト実行"):
                if not api_key or not amz_curr: st.error("入力不足です")
                else:
                    with st.spinner("生成中..."):
                        prompt = f"Amazon用リライト(bullet_1〜5, descriptionをJSONで)。ジャンル:{genre}。データ:{amz_curr} / {amz_supp} / {amz_rev}"
                        st.session_state.amz_res = _call_gemini(api_key, model_choice, prompt)

        with col2:
            if "amz_res" in st.session_state:
                res = st.session_state.amz_res
                if "error" in res: st.error(res['error'])
                else:
                    st.subheader("📋 出力結果")
                    for i in range(1, 6):
                        val = res.get(f"bullet_{i}", "")
                        st.text_input(f"箇条書き {i}", value=val, key=f"out_amz_b{i}")
                        st.markdown('<div class="copy-btn-style">', unsafe_allow_html=True)
                        copy_to_clipboard(val, f"箇条書き {i}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    desc = res.get("description", "")
                    st.text_area("商品紹介文", value=desc, height=200)
                    st.markdown('<div class="copy-btn-style">', unsafe_allow_html=True)
                    copy_to_clipboard(desc, "紹介文全文")
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- 楽天 タブ ---
    with tab_rak:
        st.markdown('<div class="status-box">楽天仕様: キャッチコピー・レビュー反映型説明文。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        with col1:
            rak_curr = st.text_area("1. 現在の商品説明", height=150, key="rak_c")
            rak_kw = st.text_area("2. 盛り込みキーワード", height=80, key="rak_k")
            rak_rev = st.text_area("3. カスタマーレビュー（新設）", height=100, key="rak_r", placeholder="レビューの悩み解決を反映します")
            
            if st.button("楽天用リライト実行"):
                if not api_key or not rak_curr: st.error("入力不足です")
                else:
                    with st.spinner("生成中..."):
                        prompt = f"楽天用リライト(catchcopy, desc_text, desc_htmlをJSONで)。レビュー反映重視。ジャンル:{genre}。KW:{rak_kw} データ:{rak_curr} / {rak_rev}"
                        st.session_state.rak_res = _call_gemini(api_key, model_choice, prompt)

        with col2:
            if "rak_res" in st.session_state:
                res = st.session_state.rak_res
                if "error" in res: st.error(res['error'])
                else:
                    cc = res.get("catchcopy", "")
                    st.text_input("キャッチコピー", value=cc)
                    st.markdown('<div class="copy-btn-style">', unsafe_allow_html=True)
                    copy_to_clipboard(cc, "キャッチコピー")
                    st.markdown('</div>', unsafe_allow_html=True)

                    dt = res.get("desc_text", "")
                    st.text_area("商品説明（テキスト）", value=dt, height=150)
                    st.markdown('<div class="copy-btn-style">', unsafe_allow_html=True)
                    copy_to_clipboard(dt, "テキスト説明文")
                    st.markdown('</div>', unsafe_allow_html=True)

                    dh = res.get("desc_html", "")
                    st.subheader("💻 RMS用HTML")
                    st.code(dh, language="html")
                    st.markdown('<div class="copy-btn-style">', unsafe_allow_html=True)
                    copy_to_clipboard(dh, "HTMLコード")
                    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
