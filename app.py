import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定とアプリ名 ---
st.set_page_config(page_title="Rufus ＆楽天AI モール別AI対策ツール", layout="wide")

def _inject_css_and_js():
    st.markdown("""
    <style>
      :root { --bg: #f0f2f6; --accent: #007185; }
      .stApp { background-color: var(--bg); }
      /* メインボタン（黄色） */
      div.stButton > button:first-child {
        background-color: #ffd814 !important; border: 1px solid #fcd200 !important;
        color: #111 !important; width: 100%; font-weight: bold !important;
        border-radius: 8px !important; height: 3em;
      }
      /* コピーボタン専用（水色） */
      .copy-btn-container button {
        background-color: #e7f3f3 !important; border: 1px solid #007185 !important;
        color: #007185 !important; height: 2.2em !important; font-size: 0.85em !important;
        margin-top: -15px !important; margin-bottom: 10px !important;
      }
      .status-box {
        padding: 15px; border-radius: 10px; background-color: #ffffff;
        border-left: 6px solid #007185; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      }
      /* テキストエリアのラベルを見やすく */
      .stTextArea label, .stTextInput label { font-weight: bold !important; color: #232f3e; }
    </style>
    """, unsafe_allow_html=True)

def copy_to_clipboard(text, label_id):
    """確実にクリップボードへ送るためのJavaScript実行"""
    if st.button(f"📋 この内容をコピー", key=f"btn_{label_id}"):
        # JSを使って直接クリップボードに書き込む
        st.components.v1.html(f"""
            <script>
            navigator.clipboard.writeText(`{text}`).then(() => {{
                parent.postMessage({{type: 'streamlit:toast', data: '✅ コピーしました！'}}, '*');
            }});
            </script>
        """, height=0)
        st.toast(f"✅ コピー完了")

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
        col1, col2 = st.columns([1, 1.2])
        with col1:
            amz_curr = st.text_area("1. 現在の商品説明", height=150)
            amz_supp = st.text_area("2. 補足（スペック等）", height=100)
            amz_rev = st.text_area("3. カスタマーレビュー", height=100)
            
            if st.button("Amazon用リライト実行", key="run_amz"):
                if not api_key or not amz_curr: st.error("入力不足です")
                else:
                    with st.spinner("生成中..."):
                        prompt = f"Amazon用。bullet_1〜5(各100字), descriptionをJSONで。ジャンル:{genre}。データ:{amz_curr}/{amz_supp}/{amz_rev}"
                        st.session_state.amz_res = _call_gemini(api_key, model_choice, prompt)

        with col2:
            st.subheader("📋 リライト結果")
            if "amz_res" in st.session_state:
                res = st.session_state.amz_res
                if "error" in res: st.error(res['error'])
                else:
                    # 箇条書きを1つずつ表示
                    for i in range(1, 6):
                        val = res.get(f"bullet_{i}", "")
                        st.text_input(f"箇条書き {i}", value=val, key=f"input_amz_b{i}")
                        st.markdown('<div class="copy-btn-container">', unsafe_allow_html=True)
                        copy_to_clipboard(val, f"amz_b{i}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    desc = res.get("description", "")
                    st.text_area("商品紹介文（全文）", value=desc, height=250, key="input_amz_desc")
                    st.markdown('<div class="copy-btn-container">', unsafe_allow_html=True)
                    copy_to_clipboard(desc, "amz_desc")
                    st.markdown('</div>', unsafe_allow_html=True)

    # --- 楽天 タブ ---
    with tab_rak:
        col1, col2 = st.columns([1, 1.2])
        with col1:
            rak_curr = st.text_area("1. 現在の商品説明", height=150, key="r_curr")
            rak_kw = st.text_area("2. 盛り込みキーワード", height=80, key="r_kw")
            rak_rev = st.text_area("3. カスタマーレビュー", height=100, key="r_rev")
            
            if st.button("楽天用リライト実行", key="run_rak"):
                if not api_key or not rak_curr: st.error("入力不足です")
                else:
                    with st.spinner("生成中..."):
                        prompt = f"楽天用。catchcopy, desc_text, desc_htmlをJSONで。レビュー反映重視。ジャンル:{genre}。KW:{rak_kw} データ:{rak_curr}/{rak_rev}"
                        st.session_state.rak_res = _call_gemini(api_key, model_choice, prompt)

        with col2:
            st.subheader("📋 リライト結果")
            if "rak_res" in st.session_state:
                res = st.session_state.rak_res
                if "error" in res: st.error(res['error'])
                else:
                    cc = res.get("catchcopy", "")
                    st.text_input("キャッチコピー", value=cc, key="input_rak_cc")
                    st.markdown('<div class="copy-btn-container">', unsafe_allow_html=True)
                    copy_to_clipboard(cc, "rak_cc")
                    st.markdown('</div>', unsafe_allow_html=True)

                    dt = res.get("desc_text", "")
                    st.text_area("商品説明（テキスト）", value=dt, height=150, key="input_rak_dt")
                    st.markdown('<div class="copy-btn-container">', unsafe_allow_html=True)
                    copy_to_clipboard(dt, "rak_dt")
                    st.markdown('</div>', unsafe_allow_html=True)

                    dh = res.get("desc_html", "")
                    st.text_area("RMS用HTML（コピー用）", value=dh, height=150, key="input_rak_dh")
                    st.markdown('<div class="copy-btn-container">', unsafe_allow_html=True)
                    copy_to_clipboard(dh, "rak_dh")
                    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
