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
    """AI呼び出し関数（エラーハンドリング強化版）"""
    try:
        genai.configure(api_key=api_key)
        # NotFoundエラー対策：接頭辞を調整
        m_name = model_id if model_id.startswith("models/") else f"models/{model_id}"
        model = genai.GenerativeModel(model_name=m_name)
        
        response = model.generate_content(prompt_text)
        
        # JSON抽出処理
        res_text = response.text
        clean_text = res_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        # エラー内容を画面に返す
        return {"error_msg": str(e)}

def main():
    _inject_css()
    st.title("📦 モール別 AI特化型 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 認証・設定")
        api_key = st.text_input("Gemini API Key", type="password")
        # モデル名をより一般的なものに固定
        model_id = st.selectbox("使用モデル", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"])
        
        st.divider()
        st.header("🎨 出力設定")
        genre = st.selectbox("商品ジャンル", 
                             ["一般雑貨", "季節行事（ハロウィン・クリスマス等）", "推し活グッズ・ホビー",
                              "介護・看護・ヘルスケア", "ベビー・マタニティ", "ペット用品",
                              "スポーツ・アウトドア", "園芸・ガーデニング・DIY", "その他"])
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・ベネフィット重視", "簡潔・ロジカル"])

    tab_amz, tab_rak = st.tabs(["🛒 Amazon Rufus対策", "🔴 楽天 AI/SEO対策"])

    # --- Amazon タブ ---
    with tab_amz:
        st.markdown('<div class="status-box">Amazon仕様：5つの箇条書きスロットと文字数調整。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        with col1:
            amz_curr = st.text_area("現在の文章", height=150, key="amz_c")
            amz_supp = st.text_area("補足スペック", placeholder="寸法、素材など", height=100, key="amz_s")
            amz_rev = st.text_area("カスタマーレビュー", height=100, key="amz_r")
            
            if st.button("Amazon用リライト実行"):
                if not api_key or not amz_curr:
                    st.error("APIキーと現在の文章を入力してください。")
                else:
                    with st.spinner("AIが考案中..."):
                        prompt = f"Amazon用リライト依頼。ジャンル:{genre}、トーン:{tone}。5つの箇条書き(bullet_1~5)と紹介文(description)をJSONで出力してください。規約遵守。"
                        # 実際の運用では詳細なプロンプトが必要ですが、構造維持のため簡略化
                        prompt += f"\nデータ: {amz_curr} {amz_supp} {amz_rev}"
                        st.session_state.amz_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "amz_out" in st.session_state:
                res = st.session_state.amz_out
                if "error_msg" in res:
                    st.error(f"AIとの通信でエラーが発生しました：\n{res['error_msg']}")
                    st.info("APIキーが正しいか、またはモデルを変更して再度お試しください。")
                else:
                    for i in range(1, 6):
                        st.text_input(f"箇条書き {i}", value=res.get(f"bullet_{i}", ""))
                    st.text_area("紹介文", value=res.get("description", ""), height=200)

    # --- 楽天 タブ ---
    with tab_rak:
        st.markdown('<div class="status-box">楽天仕様：キーワード網羅とHTMLタグ生成。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1.2])
        with col1:
            rak_curr = st.text_area("現在の文章", height=150, key="rak_c")
            rak_kw = st.text_area("盛り込みたいキーワード", height=100, key="rak_k")
            if st.button("楽天用リライト実行"):
                if not api_key or not rak_curr:
                    st.error("入力が不足しています。")
                else:
                    with st.spinner("楽天SEO最適化中..."):
                        prompt = f"楽天用リライト。ジャンル:{genre}。catchcopy, desc_text, desc_html をJSONで出力。KW:{rak_kw} データ:{rak_curr}"
                        st.session_state.rak_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "rak_out" in st.session_state:
                res = st.session_state.rak_out
                if "error_msg" in res:
                    st.error(f"エラー：{res['error_msg']}")
                else:
                    st.text_input("キャッチコピー", value=res.get("catchcopy", ""))
                    st.text_area("テキスト版", value=res.get("desc_text", ""), height=150)
                    st.code(res.get("desc_html", ""), language="html")

if __name__ == "__main__":
    main()
