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

def _call_gemini(api_key, prompt_text):
    try:
        genai.configure(api_key=api_key)
        
        # エラー回避策：複数のモデル名候補を順番に試す
        model_names = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'models/gemini-1.5-flash']
        
        model = None
        last_error = ""
        
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                response = model.generate_content(prompt_text)
                # 成功したらループを抜ける
                res_text = response.text
                break
            except Exception as e:
                last_error = str(e)
                continue
        
        if not model or 'res_text' not in locals():
            raise Exception(f"全てのモデル名試行に失敗しました。最新のエラー: {last_error}")

        # JSON抽出
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()
        
        return json.loads(res_text)
    except Exception as e:
        st.error(f"⚠️ 接続エラー: {str(e)}")
        st.info("💡 対策: GitHubの 'requirements.txt' に 'google-generativeai>=0.5.0' が記載されているか確認してください。")
        return None

def main():
    _inject_css()
    st.title("📦 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 設定")
        api_key = st.text_input("Gemini API Key", type="password")
        genre = st.selectbox("ジャンル", ["推し活", "スポーツ", "アウトドア", "ベビー", "ペット", "介護", "ファッション", "生活雑貨"])
        tone = st.radio("トーン", ["誠実・信頼", "情熱的", "簡潔"])

    tab_amz, tab_rak = st.tabs(["Amazon", "楽天"])

    with tab_amz:
        amz_curr = st.text_area("1. 現在の文章", height=150)
        if st.button("リライト実行"):
            if api_key and amz_curr:
                with st.spinner("通信中..."):
                    prompt = f"Amazon用リライト。ジャンル:{genre}, トーン:{tone}。元文:{amz_curr}。出力は必ず以下のJSON形式：{{'result_1': '箇条書き', 'result_2': '紹介文'}}"
                    out = _call_gemini(api_key, prompt)
                    if out:
                        st.subheader("✅ 箇条書き")
                        st.code(out.get("result_1", ""))
                        st.subheader("✅ 紹介文")
                        st.write(out.get("result_2", ""))
            else:
                st.warning("入力が不足しています。")

if __name__ == "__main__":
    main()
