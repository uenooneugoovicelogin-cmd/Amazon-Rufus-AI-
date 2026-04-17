import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="Rufus ＆ 楽天AI モール別対策ツール", layout="wide")

def _inject_custom_style():
    st.markdown("""
    <style>
      /* 全体背景とフォント */
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
      html, body, [data-testid="stAppViewContainer"] {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
      }
      
      /* サイドバーのデザイン */
      [data-testid="stSidebar"] {
        background-color: #1e293b;
        color: white;
      }
      [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 { color: #f1f5f9; }
      
      /* カード型コンテナ */
      .st-emotion-cache-12w0qpk, .st-emotion-cache-6qob1r {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        margin-bottom: 1.5rem;
      }

      /* タイトル周り */
      h1 { color: #0f172a; font-weight: 800 !important; }
      
      /* ボタンデザイン */
      div.stButton > button {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        height: 3.5em !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
      }
      div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
      }

      /* コピーボタン専用 */
      .copy-container button {
        background: #f1f5f9 !important;
        color: #475569 !important;
        border: 1px solid #e2e8f0 !important;
        height: 2.2em !important;
        margin-top: -10px !important;
        font-size: 0.8rem !important;
      }

      /* 文字数カウントのラベル */
      .char-count { font-size: 0.8rem; font-weight: bold; margin-bottom: 5px; }
      .count-ok { color: #10b981; }
      .count-ng { color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)

def _call_gemini(api_key, model_name, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        text = response.text
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}

def main():
    _inject_custom_style()
    st.title("🛡️ Rufus ＆ 楽天AI モール別対策ツール")
    
    with st.sidebar:
        st.header("⚙️ Settings")
        api_key = st.text_input("API Key", type="password")
        
        # モデル選択
        model_name = "gemini-1.5-flash"
        if api_key:
            try:
                genai.configure(api_key=api_key)
                models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = st.selectbox("Model", models)
            except:
                model_name = st.selectbox("Model", ["gemini-1.5-flash", "gemini-1.5-pro"])
        
        st.divider()
        genre = st.selectbox("商品ジャンル", ["一般雑貨", "季節行事", "推し活・ホビー", "介護・看護", "ベビー", "ペット", "スポーツ", "園芸", "その他"])
        tone = st.radio("文章トーン", ["誠実・信頼", "情熱的", "簡潔・ロジカル"])

    tab_amz, tab_rak = st.tabs(["📦 Amazon Strategy (Rufus)", "🔴 Rakuten SEO"])

    # --- Amazon 処理 ---
    with tab_amz:
        col1, col2 = st.columns([1, 1.2], gap="large")
        with col1:
            st.subheader("📥 Input")
            amz_c = st.text_area("1. 現在の文章", height=150)
            amz_s = st.text_area("2. スペック・補足", height=100)
            amz_r = st.text_area("3. カスタマーレビュー", height=100)
            if st.button("Generate for Amazon", use_container_width=True):
                if not api_key: st.error("Keyを入力してください")
                else:
                    with st.spinner("AI Analysis..."):
                        p = f"Amazon用。bullet_1〜5(各95字程度), descriptionをJSON形式で。ジャンル:{genre}。データ:{amz_c}/{amz_s}/{amz_r}"
                        st.session_state.amz_res = _call_gemini(api_key, model_name, p)

        with col2:
            st.subheader("📤 Results")
            if "amz_res" in st.session_state:
                res = st.session_state.amz_res
                if "error" in res: st.error(res["error"])
                else:
                    for i in range(1, 6):
                        txt = res.get(f"bullet_{i}", "")
                        count = len(txt)
                        color_class = "count-ok" if count <= 100 else "count-ng"
                        st.markdown(f'<div class="char-count {color_class}">箇条書き {i} : {count}/100文字</div>', unsafe_allow_html=True)
                        st.text_area(f"B{i}", value=txt, height=65, key=f"amz_b{i}", label_visibility="collapsed")
                        st.markdown('<div class="copy-container">', unsafe_allow_html=True)
                        if st.button(f"Copy Bullet {i}", key=f"cp_amz_b{i}"):
                            st.write(f'<script>navigator.clipboard.writeText(`{txt}`);</script>', unsafe_allow_html=True)
                            st.toast(f"B{i} Copied!")
                        st.markdown('</div>', unsafe_allow_html=True)

                    desc = res.get("description", "")
                    st.markdown(f'<div class="char-count">商品紹介文 : {len(desc)}文字</div>', unsafe_allow_html=True)
                    st.text_area("Desc", value=desc, height=200, label_visibility="collapsed")
                    if st.button("Copy Description"):
                        st.write(f'<script>navigator.clipboard.writeText(`{desc}`);</script>', unsafe_allow_html=True)
                        st.toast("Description Copied!")

    # --- 楽天 処理 ---
    with tab_rak:
        col1, col2 = st.columns([1, 1.2], gap="large")
        with col1:
            st.subheader("📥 Input")
            rak_c = st.text_area("1. 文章", height=150)
            rak_k = st.text_area("2. SEOキーワード", height=80)
            rak_r = st.text_area("3. レビュー内容", height=100)
            if st.button("Generate for Rakuten", use_container_width=True):
                if not api_key: st.error("Keyを入力してください")
                else:
                    with st.spinner("SEO Optimizing..."):
                        p = f"楽天用(catchcopy, desc_text, desc_html)。JSONで。KW:{rak_k}。データ:{rak_c}/{rak_r}"
                        st.session_state.rak_res = _call_gemini(api_key, model_name, p)
        
        with col2:
            st.subheader("📤 Results")
            if "rak_res" in st.session_state:
                res = st.session_state.rak_res
                if "error" in res: st.error(res["error"])
                else:
                    items = [("catchcopy", "キャッチコピー"), ("desc_text", "テキスト説明文"), ("desc_html", "RMS用HTML")]
                    for key_name, label in items:
                        val = res.get(key_name, "")
                        st.markdown(f'<div class="char-count">{label} : {len(val)}文字</div>', unsafe_allow_html=True)
                        st.text_area(label, value=val, height=100 if "html" in key_name else 70, key=f"rak_{key_name}")
                        st.markdown('<div class="copy-container">', unsafe_allow_html=True)
                        if st.button(f"Copy {label}", key=f"cp_rak_{key_name}"):
                            st.write(f'<script>navigator.clipboard.writeText(`{val}`);</script>', unsafe_allow_html=True)
                            st.toast(f"{label} Copied!")
                        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
