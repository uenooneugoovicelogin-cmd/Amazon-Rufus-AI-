import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="Rufus ＆ 楽天AI モール別AI対策ツール", layout="wide")

def _inject_custom_style():
    st.markdown("""
    <style>
      /* --- 全体背景 --- */
      html, body, [data-testid="stAppViewContainer"] {
        background-color: #f8fafc;
      }
      
      /* --- サイドバー（メニュー）の徹底した視認性向上 --- */
      [data-testid="stSidebar"] {
        background-color: #0f172a !important; /* 濃紺 */
      }
      
      /* ラベル、見出し、ラジオボタンのテキストを白に統一 */
      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
      [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] .stMarkdown p,
      [data-testid="stSidebar"] label {
        color: #ffffff !important;
        font-weight: 600 !important;
      }

      /* 入力ボックス（セレクトボックス・テキスト入力）をダーク仕様に変更 */
      [data-testid="stSidebar"] .stTextInput input, 
      [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1e293b !important; /* ボックス内を少し明るい紺に */
        color: #ffffff !important; /* 入力文字は白 */
        border: 1px solid #334155 !important;
      }
      
      /* セレクトボックスのプルダウンメニュー内の文字 */
      div[data-baseweb="popover"] * {
        color: #0f172a !important; /* 選択肢リストは白背景に黒文字で見やすく */
      }

      /* --- メインエリアのカード型デザイン --- */
      div[data-testid="stVerticalBlock"] > div.stColumn {
        background: #ffffff;
        padding: 30px !important;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
      }

      /* 実行ボタン（プロフェッショナルな青） */
      div.stButton > button:first-child {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        height: 3.8em !important;
        transition: transform 0.2s ease;
      }
      div.stButton > button:hover {
        transform: scale(1.02);
      }
      
      /* コピーボタン（控えめで清潔なデザイン） */
      .copy-area button {
        background-color: #eff6ff !important;
        color: #2563eb !important;
        border: 1px solid #bfdbfe !important;
        font-size: 0.85rem !important;
        margin-top: -12px !important;
      }

      /* 文字数バッジ */
      .count-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-bottom: 6px;
      }
      .badge-ok { background-color: #dcfce7; color: #166534; }
      .badge-ng { background-color: #fee2e2; color: #991b1b; }

      /* タブのデザイン */
      .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
      .stTabs [data-baseweb="tab"] {
        font-weight: bold;
        color: #64748b;
      }
      .stTabs [aria-selected="true"] {
        color: #2563eb !important;
        border-bottom-color: #2563eb !important;
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
        st.header("🔑 接続設定")
        api_key = st.text_input("Gemini APIキー", type="password", placeholder="ここに貼り付け")
        
        # モデル自動取得
        model_name = "gemini-1.5-flash"
        if api_key:
            try:
                genai.configure(api_key=api_key)
                models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = st.selectbox("使用AIモデル", models)
            except:
                model_name = st.selectbox("使用AIモデル", ["gemini-1.5-flash", "gemini-1.5-pro"])
        
        st.divider()
        st.header("🎨 リライト設定")
        genre = st.selectbox("商品ジャンル", ["一般雑貨", "季節行事（ハロウィン等）", "推し活・ホビー", "介護・看護", "ベビー", "ペット", "スポーツ", "園芸", "その他"])
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・売込重視", "簡潔・ロジカル"])

    tab_amz, tab_rak = st.tabs(["🛒 Amazon用 (Rufus対策)", "🔴 楽天用 (AI・SEO対策)"])

    # --- Amazon タブ ---
    with tab_amz:
        col1, col2 = st.columns([1, 1.2], gap="large")
        with col1:
            st.subheader("📥 元情報を入力")
            amz_c = st.text_area("1. 現在の商品説明・箇条書き", height=150)
            amz_s = st.text_area("2. 補足スペック・仕様", height=100)
            amz_r = st.text_area("3. カスタマーレビュー（悩み等）", height=100)
            if st.button("Amazon用のリライトを実行"):
                if not api_key: st.error("APIキーを入力してください")
                else:
                    with st.spinner("AIが箇条書きを生成中..."):
                        p = f"Amazon用。箇条書き(bullet_1〜5:各95字程度), 詳細説明(description)をJSONで。ジャンル:{genre}。データ:{amz_c}/{amz_s}/{amz_r}"
                        st.session_state.amz_res = _call_gemini(api_key, model_name, p)

        with col2:
            st.subheader("📤 AIリライト結果")
            if "amz_res" in st.session_state:
                res = st.session_state.amz_res
                if "error" in res: st.error(res['error'])
                else:
                    for i in range(1, 6):
                        txt = res.get(f"bullet_{i}", "")
                        count = len(txt)
                        badge_class = "badge-ok" if count <= 100 else "badge-ng"
                        st.markdown(f'<span class="count-badge {badge_class}">箇条書き {i} : {count} / 100文字</span>', unsafe_allow_html=True)
                        st.text_area(f"B{i}", value=txt, height=75, key=f"amz_b{i}", label_visibility="collapsed")
                        st.markdown('<div class="copy-area">', unsafe_allow_html=True)
                        if st.button(f"箇条書き {i} をコピー", key=f"cp_amz_b{i}"):
                            st.write(f'<script>navigator.clipboard.writeText(`{txt}`);</script>', unsafe_allow_html=True)
                            st.toast(f"箇条書き{i}をコピー！")
                        st.markdown('</div>', unsafe_allow_html=True)

                    desc = res.get("description", "")
                    st.markdown(f'<span class="count-badge badge-ok">商品紹介文（全文）: {len(desc)}文字</span>', unsafe_allow_html=True)
                    st.text_area("説明", value=desc, height=200, label_visibility="collapsed")
                    if st.button("紹介文全文をコピー"):
                        st.write(f'<script>navigator.clipboard.writeText(`{desc}`);</script>', unsafe_allow_html=True)
                        st.toast("紹介文をコピーしました")

    # --- 楽天 タブ ---
    with tab_rak:
        col1, col2 = st.columns([1, 1.2], gap="large")
        with col1:
            st.subheader("📥 元情報を入力")
            rak_c = st.text_area("1. 現在の文章", height=150, key="r_in_c")
            rak_k = st.text_area("2. SEO・キーワード", height=80, key="r_in_k", placeholder="例：送料無料, 楽天1位, 2024新作")
            rak_r = st.text_area("3. レビュー内容", height=100, key="r_in_r")
            if st.button("楽天用のリライトを実行", key="btn_rak"):
                if not api_key: st.error("APIキーを入力してください")
                else:
                    with st.spinner("楽天SEOに最適化中..."):
                        p = f"楽天用(catchcopy, desc_text, desc_html)。JSONで。レビュー反映重視。KW:{rak_k}。データ:{rak_c}/{rak_r}"
                        st.session_state.rak_res = _call_gemini(api_key, model_name, p)
        
        with col2:
            st.subheader("📤 AIリライト結果")
            if "rak_res" in st.session_state:
                res = st.session_state.rak_res
                if "error" in res: st.error(res["error"])
                else:
                    targets = [("catchcopy", "キャッチコピー"), ("desc_text", "説明文(テキスト)"), ("desc_html", "説明文(HTMLコード)")]
                    for key_name, label in targets:
                        val = res.get(key_name, "")
                        st.markdown(f'<span class="count-badge badge-ok">{label}: {len(val)}文字</span>', unsafe_allow_html=True)
                        st.text_area(label, value=val, height=120, key=f"out_rak_{key_name}", label_visibility="collapsed")
                        st.markdown('<div class="copy-area">', unsafe_allow_html=True)
                        if st.button(f"{label}をコピー", key=f"cp_rak_{key_name}"):
                            st.write(f'<script>navigator.clipboard.writeText(`{val}`);</script>', unsafe_allow_html=True)
                            st.toast(f"{label}をコピー！")
                        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
