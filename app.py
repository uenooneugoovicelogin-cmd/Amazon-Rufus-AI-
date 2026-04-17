import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="Wonder Plaza｜モール別AIリライト", layout="wide")

def _inject_css() -> None:
    st.markdown("""
    <style>
      :root { --bg: #f8f9fa; --accent: #007185; }
      .stApp { background-color: var(--bg); }
      .status-box {
        padding: 10px; border-radius: 5px; background-color: #e7f3f3;
        border-left: 5px solid #007185; margin-bottom: 20px;
      }
      div.stButton > button {
        background-color: #ffd814 !important; color: #111 !important;
        width: 100%; font-weight: bold !important;
      }
    </style>
    """, unsafe_allow_html=True)

def _call_gemini(api_key: str, model_id: str, prompt_text: str):
    """エラーを徹底的に回避する生成関数"""
    try:
        genai.configure(api_key=api_key)
        # 404対策：モデル名の頭に models/ が付いていない場合は付与するが、
        # ライブラリによっては不要なため、最新の命名規則に合わせる
        target_model = model_id if "/" in model_id else f"models/{model_id}"
        model = genai.GenerativeModel(model_name=target_model)
        
        response = model.generate_content(prompt_text)
        
        # JSONレスポンスの整形
        res_text = response.text
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0]
            
        return json.loads(res_text.strip())
    except Exception as e:
        return {"error_msg": str(e), "full_trace": f"Model attempted: {model_id}"}

def main():
    _inject_css()
    st.title("📦 モール別 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 認証・設定")
        api_key = st.text_input("Gemini API Key", type="password", help="APIキーを入力してください")
        
        # 2026年現在の安定モデルリスト
        model_id = st.selectbox("使用モデル（404が出る場合は変更してください）", 
                                ["gemini-1.5-flash", 
                                 "gemini-1.5-flash-latest", 
                                 "gemini-1.5-pro", 
                                 "gemini-2.0-flash"])
        
        if st.button("🔌 接続テスト（使用可能モデルを確認）"):
            if not api_key:
                st.warning("先にAPIキーを入力してください。")
            else:
                try:
                    genai.configure(api_key=api_key)
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    st.success("接続成功！使用可能なモデル一覧:")
                    st.write(models)
                except Exception as e:
                    st.error(f"接続失敗: {e}")

        st.divider()
        st.header("🎨 出力設定")
        genre = st.selectbox("商品ジャンル", ["一般雑貨", "推し活グッズ・ホビー", "季節行事", "介護・看護", "ベビー・ペット", "スポーツ・アウトドア", "その他"])
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・ベネフィット重視"])

    tab_amz, tab_rak = st.tabs(["🛒 Amazon用", "🔴 楽天用"])

    # --- Amazon タブ ---
    with tab_amz:
        col1, col2 = st.columns([1, 1.2])
        with col1:
            amz_curr = st.text_area("1. 現在の文章", height=150)
            amz_supp = st.text_area("2. 補足スペック", height=100)
            amz_rev = st.text_area("3. カスタマーレビュー", height=100)
            
            if st.button("Amazonリライト実行"):
                if not api_key or not amz_curr:
                    st.error("入力が不足しています。")
                else:
                    with st.spinner("AI生成中..."):
                        prompt = f"Amazon用紹介文をJSON形式(bullet_1, bullet_2, bullet_3, bullet_4, bullet_5, description)で作成してください。ジャンル:{genre}。データ:{amz_curr} {amz_supp} {amz_rev}"
                        st.session_state.amz_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "amz_out" in st.session_state:
                res = st.session_state.amz_out
                if "error_msg" in res:
                    st.error(f"エラー: {res['error_msg']}")
                    st.info("解決策: 左メニューの『接続テスト』を押し、表示されたモデル名をコピーして『使用モデル』に直接入力するか、別のモデルを選んでください。")
                else:
                    for i in range(1, 6):
                        st.text_input(f"箇条書き {i}", value=res.get(f"bullet_{i}", ""))
                    st.text_area("紹介文本体", value=res.get("description", ""), height=250)

    # --- 楽天 タブ ---
    with tab_rak:
        col1, col2 = st.columns([1, 1.2])
        with col1:
            rak_curr = st.text_area("現在の文章", key="rak_c")
            rak_kw = st.text_area("盛り込みたいキーワード", key="rak_k")
            if st.button("楽天リライト実行"):
                if not api_key: st.error("APIキーが必要です")
                else:
                    with st.spinner("楽天SEO最適化中..."):
                        prompt = f"楽天用紹介文をJSON形式(catchcopy, desc_text, desc_html)で作成。ジャンル:{genre}。KW:{rak_kw} データ:{rak_curr}"
                        st.session_state.rak_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "rak_out" in st.session_state:
                res = st.session_state.rak_out
                if "error_msg" in res:
                    st.error(res['error_msg'])
                else:
                    st.text_input("キャッチコピー", value=res.get("catchcopy", ""))
                    st.text_area("テキスト説明文", value=res.get("desc_text", ""), height=200)
                    st.code(res.get("desc_html", ""), language="html")

if __name__ == "__main__":
    main()
