import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="Rufus ＆ 楽天AI モール別対策ツール", layout="wide")

def _inject_custom_style():
    st.markdown("""
    <style>
      /* 全体背景 */
      html, body, [data-testid="stAppViewContainer"] {
        background-color: #f1f5f9;
        color: #1e293b;
      }
      
      /* --- サイドバー（メニュー）の徹底した視認性向上 --- */
      [data-testid="stSidebar"] {
        background-color: #0f172a !important; /* 深いネイビー */
        border-right: 1px solid #e2e8f0;
      }
      
      /* サイドバー内の全テキスト（見出し、ラベル、ラジオボタンの選択肢、説明文など）を白に */
      [data-testid="stSidebar"] * {
        color: #ffffff !important;
      }
      
      /* 入力エリアの中の文字だけは入力しやすいように黒にする */
      [data-testid="stSidebar"] input, 
      [data-testid="stSidebar"] select,
      [data-testid="stSidebar"] div[role="listbox"] div {
        color: #1e293b !important;
      }
      
      /* サイドバー内の入力ボックス背景 */
      [data-testid="stSidebar"] .stTextInput input, 
      [data-testid="stSidebar"] .stSelectbox div {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
      }

      /* --- メインエリアのカードデザイン --- */
      div[data-testid="stVerticalBlock"] > div.stColumn {
        background: #ffffff;
        padding: 25px !important;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
      }

      /* タイトルと見出し */
      h1 { color: #0f172a; font-weight: 800 !important; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; }
      h2, h3 { color: #334155; }
      
      /* 実行ボタン（鮮やかなブルー） */
      div.stButton > button:first-child {
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        width: 100% !important;
        height: 3.5em !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
      }
      
      /* コピーボタン（清潔感のあるグレー） */
      .copy-area button {
        background-color: #f8fafc !important;
        color: #64748b !important;
        border: 1px solid #e2e8f0 !important;
        font-size: 0.8rem !important;
        height: 2.2em !important;
        margin-top: -10px !important;
      }
      .copy-area button:hover {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
      }

      /* 文字数表示のバッジ */
      .count-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-bottom: 4px;
      }
      .badge-ok { background-color: #dcfce7; color: #166534; }
      .badge-ng { background-color: #fee2e2; color: #991b1b; }

      /* タブのデザイン */
      .stTabs [data-baseweb="tab-list"] { gap: 10px; }
      .stTabs [data-baseweb="tab"] {
        background-color: #e2e8f0;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #475569;
      }
      .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
      }
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
        st.header("🔑 基本設定")
        api_key = st.text_input("APIキーを入力", type="password")
        
        # モデル選択
        model_name = "gemini-1.5-flash"
        if api_key:
            try:
                genai.configure(api_key=api_key)
                models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = st.selectbox("使用モデル", models)
            except:
                model_name = st.selectbox("使用モデル（予備）", ["gemini-1.5-flash", "gemini-1.5-pro"])
        
        st.divider()
        st.header("🎨 リライト設定")
        genre = st.selectbox("商品ジャンル", ["一般雑貨", "季節行事", "推し活・ホビー", "介護・看護", "ベビー", "ペット", "スポーツ", "園芸", "その他"])
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・売込重視", "簡潔・スペック重視"])

    tab_amz, tab_rak = st.tabs(["🛒 Amazon (Rufus/検索対策)", "🔴 楽天 (SEO/店舗対策)"])

    # --- Amazon タブ ---
    with tab_amz:
        col1, col2 = st.columns([1, 1.2], gap="large")
        with col1:
            st.subheader("📥 入力エリア")
            amz_c = st.text_area("1. 現在の商品説明", height=150)
            amz_s = st.text_area("2. スペック・補足情報", height=100)
            amz_r = st.text_area("3. カスタマーレビュー", height=100)
            if st.button("Amazon用リライトを実行"):
                if not api_key: st.error("APIキーを入力してください")
                else:
                    with st.spinner("AIが分析中..."):
                        p = f"Amazon用。bullet_1〜5(各90-100字), descriptionをJSONで。ジャンル:{genre}。データ:{amz_c}/{amz_s}/{amz_r}"
                        st.session_state.amz_res = _call_gemini(api_key, model_name, p)

        with col2:
            st.subheader("📤 生成結果")
            if "amz_res" in st.session_state:
                res = st.session_state.amz_res
                if "error" in res: st.error(f"エラー: {res['error']}")
                else:
                    for i in range(1, 6):
                        txt = res.get(f"bullet_{i}", "")
                        count = len(txt)
                        badge_class = "badge-ok" if count <= 100 else "badge-ng"
                        st.markdown(f'<span class="count-badge {badge_class}">箇条書き {i} : {count}/100文字</span>', unsafe_allow_html=True)
                        st.text_area(f"B{i}", value=txt, height=70, key=f"amz_b{i}", label_visibility="collapsed")
                        st.markdown('<div class="copy-area">', unsafe_allow_html=True)
                        if st.button(f"箇条書き {i} をコピー", key=f"cp_amz_b{i}"):
                            st.write(f'<script>navigator.clipboard.writeText(`{txt}`);</script>', unsafe_allow_html=True)
                            st.toast(f"箇条書き{i}をコピーしました")
                        st.markdown('</div>', unsafe_allow_html=True)

                    desc = res.get("description", "")
                    st.markdown(f'<span class="count-badge badge-ok">商品紹介文（全文）: {len(desc)}文字</span>', unsafe_allow_html=True)
                    st.text_area("説明文", value=desc, height=250, label_visibility="collapsed")
                    if st.button("紹介文全文をコピー"):
                        st.write(f'<script>navigator.clipboard.writeText(`{desc}`);</script>', unsafe_allow_html=True)
                        st.toast("紹介文をコピーしました")

    # --- 楽天 タブ ---
    with tab_rak:
        col1, col2 = st.columns([1, 1.2], gap="large")
        with col1:
            st.subheader("📥 入力エリア")
            rak_c = st.text_area("1. 現在の文章", height=150, key="r_in_c")
            rak_k = st.text_area("2. SEOキーワード", height=80, key="r_in_k")
            rak_r = st.text_area("3. レビュー内容", height=100, key="r_in_r")
            if st.button("楽天用リライトを実行", key="btn_rak"):
                if not api_key: st.error("APIキーを入力してください")
                else:
                    with st.spinner("楽天SEOに最適化中..."):
                        p = f"楽天用(catchcopy, desc_text, desc_html)。JSONで。KW:{rak_k}。データ:{rak_c}/{rak_r}"
                        st.session_state.rak_res = _call_gemini(api_key, model_name, p)
        
        with col2:
            st.subheader("📤 生成結果")
            if "rak_res" in st.session_state:
                res = st.session_state.rak_res
                if "error" in res: st.error(res["error"])
                else:
                    targets = [("catchcopy", "キャッチコピー"), ("desc_text", "説明文(テキスト)"), ("desc_html", "説明文(HTML)")]
                    for key_name, label in targets:
                        val = res.get(key_name, "")
                        st.markdown(f'<span class="count-badge badge-ok">{label}: {len(val)}文字</span>', unsafe_allow_html=True)
                        st.text_area(label, value=val, height=120, key=f"out_rak_{key_name}", label_visibility="collapsed")
                        st.markdown('<div class="copy-area">', unsafe_allow_html=True)
                        if st.button(f"{label}をコピー", key=f"cp_rak_{key_name}"):
                            st.write(f'<script>navigator.clipboard.writeText(`{val}`);</script>', unsafe_allow_html=True)
                            st.toast(f"{label}をコピーしました")
                        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
