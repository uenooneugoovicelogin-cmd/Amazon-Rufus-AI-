import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="Amazon Rufus対策｜リライトツール", layout="wide")

def _inject_css():
    st.markdown("""
    <style>
      .stApp { background-color: #f8f9fa; }
      textarea { border-radius: 8px !important; }
      div.stButton > button {
        background-color: #ffd814 !important;
        border: 1px solid #fcd200 !important;
        color: #111 !important;
        font-weight: bold !important;
        width: 100%;
      }
      .status-box {
        padding: 10px; border-radius: 5px; background-color: #e7f3f3;
        border-left: 5px solid #007185; margin-bottom: 20px;
      }
    </style>
    """, unsafe_allow_html=True)

def _call_gemini_safe(api_key, prompt_text):
    """モデル名を自動探索して実行する最強の呼び出し関数"""
    try:
        genai.configure(api_key=api_key)
        
        # 1. まず標準的な名前で試す
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt_text)
            return _parse_json(response.text)
        except Exception:
            pass

        # 2. 失敗した場合、あなたのAPIキーで「今、本当に使えるモデル」をリストアップして試す
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # gemini-1.5系、1.0系の順に優先して探す
        best_model = next((m for m in available_models if "1.5-flash" in m), 
                          next((m for m in available_models if "gemini-pro" in m), available_models[0]))
        
        model = genai.GenerativeModel(best_model)
        response = model.generate_content(prompt_text)
        return _parse_json(response.text)

    except Exception as e:
        st.error(f"深刻なエラー: {str(e)}")
        if 'available_models' in locals():
            st.info(f"利用可能なモデルリスト: {available_models}")
        return None

def _parse_json(text):
    """AIの返答からJSONを抜き出す"""
    try:
        clean_text = text
        if "```json" in text:
            clean_text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            clean_text = text.split("```")[1].split("```")[0].strip()
        return json.loads(clean_text)
    except:
        return {"result_1": "解析エラー", "result_2": text}

def main():
    _inject_css()
    st.title("📦 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 設定")
        api_key = st.text_input("Gemini API Key", type="password")
        genre_list = ["推し活", "スポーツ", "アウトドア", "大人コスチューム", "子供コスチューム", "ベビー", "ペット", "園芸", "手芸", "介護", "ハロウィン", "クリスマス", "生活雑貨", "革財布", "スリッパ", "ファッション", "時計ベルト"]
        genre = st.selectbox("ジャンル", genre_list)
        tone = st.radio("トーン", ["誠実・信頼", "情熱的", "簡潔"])

    tab_amz, tab_rak = st.tabs(["Amazon", "楽天"])

    with tab_amz:
        col1, col2 = st.columns(2)
        with col1:
            amz_curr = st.text_area("現在の文章", height=150)
            amz_supp = st.text_area("補足情報", height=80)
            amz_rev = st.text_area("レビュー内容", height=80)
            if st.button("Amazon用リライト実行"):
                if api_key and amz_curr:
                    with st.spinner("モデルを探索して生成中..."):
                        prompt = f"Amazon専門ライターとして{genre}の商品を{tone}に。元文:{amz_curr},補足:{amz_supp},レビュー:{amz_rev}。JSONで出力：{{'result_1': '箇条書き', 'result_2': '紹介文'}}"
                        st.session_state.amz_out = _call_gemini_safe(api_key, prompt)

        with col2:
            if "amz_out" in st.session_state and st.session_state.amz_out:
                st.subheader("✅ 箇条書き")
                st.code(st.session_state.amz_out.get("result_1", ""))
                st.subheader("✅ 紹介文")
                st.write(st.session_state.amz_out.get("result_2", ""))

    with tab_rak:
        col1, col2 = st.columns(2)
        with col1:
            rak_curr = st.text_area("商品説明文", height=150, key="rk_c")
            rak_kw = st.text_area("キーワード", height=80, key="rk_k")
            rak_ben = st.text_area("ベネフィット", height=80, key="rk_b")
            if st.button("楽天用リライト実行"):
                if api_key and rak_curr:
                    with st.spinner("モデルを探索して生成中..."):
                        prompt = f"楽天コンサルとして{genre}の商品を{tone}に。元文:{rak_curr},KW:{rak_kw},体験:{rak_ben}。JSONで出力：{{'result_1': 'キャッチコピー', 'result_2': '紹介文'}}"
                        st.session_state.rak_out = _call_gemini_safe(api_key, prompt)

        with col2:
            if "rak_out" in st.session_state and st.session_state.rak_out:
                st.subheader("✅ キャッチコピー")
                st.code(st.session_state.rak_out.get("result_1", ""))
                st.subheader("✅ 紹介文")
                st.write(st.session_state.rak_out.get("result_2", ""))

if __name__ == "__main__":
    main()
