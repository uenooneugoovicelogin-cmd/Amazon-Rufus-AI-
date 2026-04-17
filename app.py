import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="🛡️ モール別AI対策ツール", layout="wide")

# デザイン設定：ダークモード対策と視認性向上
st.markdown("""
<style>
    /* 全体背景 */
    [data-testid="stAppViewContainer"] { background-color: #f8fafc; }
    
    /* メインエリアのカード型デザイン */
    div[data-testid="stVerticalBlock"] > div.stColumn {
        background: #ffffff; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
    }
    
    /* テキスト入力・出力エリアの文字色強制 */
    textarea { color: #0f172a !important; background-color: #f1f5f9 !important; }
    
    /* サイドバーのデザイン */
    [data-testid="stSidebar"] { background-color: #0f172a !important; color: white !important; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: white !important; font-weight: 600; }
    
    /* 実行ボタン */
    .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important; font-weight: bold !important; width: 100%; border-radius: 8px !important;
    }
    
    /* カウントバッジ */
    .count-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; margin-bottom: 5px; }
    .badge-ok { background-color: #dcfce7; color: #166534; }
    .badge-ng { background-color: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

def _call_gemini(api_key, model_name, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        t = response.text
        # JSON部分の抽出
        if "```" in t:
            t = t.split("```")[1].replace("json", "").strip()
        return json.loads(t)
    except Exception as e:
        return {"error": f"AIエラー: {str(e)}"}

def main():
    st.title("🛡️ Rufus ＆ 楽天AI 対策ツール")
    
    with st.sidebar:
        st.header("🔑 設定")
        api_key = st.text_input("Gemini APIキー", type="password")
        model_id = st.selectbox("使用モデル", ["gemini-1.5-flash", "gemini-1.5-pro"])
        st.divider()
        genre = st.selectbox("ジャンル", ["一般雑貨", "推し活", "ベビー/ペット", "スポーツ", "その他"])
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・売込重視", "簡潔・ロジカル"])

    tab1, tab2 = st.tabs(["🛒 Amazon (Rufus対策)", "🔴 楽天 (AI・SEO対策)"])

    # --- Amazon タブ ---
    with tab1:
        c1, c2 = st.columns([1, 1.2], gap="large")
        with c1:
            st.subheader("📥 入力エリア")
            amz_in = st.text_area("現在の説明文", height=150, key="amz_in")
            amz_sp = st.text_area("補足スペック", height=100, key="amz_sp")
            amz_re = st.text_area("カスタマーレビュー", height=100, key="amz_re")
            if st.button("Amazonリライト実行"):
                if not api_key: st.error("APIキーを入力してください")
                else:
                    p = f"Amazon用JSON。bullet_1〜5(各95字), description。ジャンル:{genre}。トーン:{tone}。データ:{amz_in}/{amz_sp}/{amz_re}"
                    st.session_state.amz_res = _call_gemini(api_key, model_id, p)
        
        with c2:
            st.subheader("📤 生成結果")
            if "amz_res" in st.session_state:
                res = st.session_state.amz_res
                if "error" in res: st.error(res["error"])
                else:
                    st.info("💡 各項目の右上のアイコンをクリックでコピーできます")
                    for i in range(1, 6):
                        txt = res.get(f"bullet_{i}", "")
                        c = len(txt)
                        badge_class = "badge-ok" if 0 < c <= 100 else "badge-ng"
                        st.markdown(f'<span class="count-badge {badge_class}">箇条書き {i}: {c}/100文字</span>', unsafe_allow_html=True)
                        # st.code を使うことで標準のコピーボタンを提供
                        st.code(txt, language="")
                    
                    st.divider()
                    desc = res.get("description", "")
                    st.markdown(f'<span class="count-badge badge-ok">商品紹介文（全文）: {len(desc)}文字</span>', unsafe_allow_html=True)
                    st.code(desc, language="")

    # --- 楽天 タブ ---
    with tab2:
        r1, r2 = st.columns([1, 1.2], gap="large")
        with r1:
            st.subheader("📥 入力エリア")
            rak_in = st.text_area("現在の商品説明", height=150, key="rak_in")
            rak_kw = st.text_area("SEOキーワード", height=100, key="rak_kw")
            rak_re = st.text_area("カスタマーレビュー", height=100, key="rak_re")
            if st.button("楽天リライト実行"):
                if not api_key: st.error("APIキーを入力してください")
                else:
                    p = f"楽天用JSON。catchcopy, desc_text, desc_html。キーワード:{rak_kw}。トーン:{tone}。データ:{rak_in}/{rak_re}"
                    st.session_state.rak_res = _call_gemini(api_key, model_id, p)
        
        with r2:
            st.subheader("📤 生成結果")
            if "rak_res" in st.session_state:
                res = st.session_state.rak_res
                if "error" in res: st.error(res["error"])
                else:
                    st.info("💡 各項目の右上のアイコンをクリックでコピーできます")
                    labels = {"catchcopy": "キャッチコピー", "desc_text": "説明文(Text)", "desc_html": "説明文(HTML)"}
                    for k, label in labels.items():
                        val = res.get(k, "")
                        st.markdown(f'<span class="count-badge badge-ok">{label}: {len(val)}文字</span>', unsafe_allow_html=True)
                        st.code(val, language="")

if __name__ == "__main__":
    main()
