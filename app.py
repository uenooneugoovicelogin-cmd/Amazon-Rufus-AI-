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

def get_genre_instruction(genre):
    instructions = {
        "スポーツ": "運動性能、耐久性、機能性を強調。",
        "アウトドア": "信頼性、携帯性、設営のしやすさを強調。",
        "大人コスチューム": "写真映え、質感、セット内容を強調。",
        "子供コスチューム": "安全性、着脱のしやすさ、デザインを強調。",
        "ベビー": "安全基準、肌触り、衛生面を最優先。",
        "ペット": "快適性と健康、手入れのしやすさを強調。",
        "園芸": "育てやすさ、耐久性、生活の彩りを強調。",
        "手芸・ハンドメイド": "品質、加工のしやすさ、創作の楽しさを強調。",
        "介護": "自立支援、負担軽減、安全性を最優先。",
        "ハロウィン雑貨": "パーティーの盛り上がり、インパクトを演出。",
        "クリスマス雑貨": "温かみ、ギフト適性を強調。",
        "推し活": "収納力、透明度、保護性能を強調。",
        "生活雑貨・日用品": "利便性、コスパ、耐久性を強調。",
        "革財布": "質感、経年変化、高級感を強調。",
        "スリッパ・サンダル": "履き心地、クッション性、通気性を重視。",
        "ファッション": "シルエット、着回し、トレンド感を強調。",
        "時計ベルト": "耐久性、装着感、着せ替えの楽しさを強調。"
    }
    return instructions.get(genre, "品質と利便性を説明。")

def _call_gemini(api_key, prompt_text):
    try:
        genai.configure(api_key=api_key)
        # 404エラー回避のため、最も標準的なモデル名指定を使用
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_text)
        
        # JSON抽出処理
        res_text = response.text
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()
        
        return json.loads(res_text)
    except Exception as e:
        st.error(f"⚠️ 生成に失敗しました。APIキーまたは設定を確認してください。\nエラー内容: {str(e)}")
        return None

def main():
    _inject_css()
    st.title("📦 Amazon Rufus対策 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 設定")
        api_key = st.text_input("Gemini API Key", type="password")
        st.divider()
        genre_list = [
            "スポーツ", "アウトドア", "大人コスチューム", "子供コスチューム", "ベビー", "ペット", 
            "園芸", "手芸・ハンドメイド", "介護", "ハロウィン雑貨", "クリスマス雑貨", "推し活", 
            "生活雑貨・日用品", "革財布", "スリッパ・サンダル", "ファッション", "時計ベルト"
        ]
        genre = st.selectbox("商品ジャンル", genre_list)
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・賑やか", "簡潔・ロジカル"])
        genre_advice = get_genre_instruction(genre)

    tab_amz, tab_rak = st.tabs(["Amazon Rufus対策", "楽天 AI/SEO対策"])

    # --- Amazon ---
    with tab_amz:
        st.markdown(f'<div class="status-box">Amazonリライト：{genre}</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            amz_curr = st.text_area("1. 現在の文章", height=150, key="amz_c")
            amz_supp = st.text_area("2. 補足スペック・Q&A", height=80, key="amz_s")
            amz_rev = st.text_area("3. カスタマーレビュー", height=80, key="amz_r")
            if st.button("Amazon用リライト実行"):
                if api_key and amz_curr:
                    with st.spinner("リライト中..."):
                        prompt = f"Amazon専門ライターとして、{genre}（{genre_advice}）を{tone}なトーンで。データ：現状({amz_curr}),補足({amz_supp}),レビュー({amz_rev})。必ず次のJSON形式で：{{'result_1': '箇条書き5点', 'result_2': '紹介文'}}"
                        st.session_state.amz_out = _call_gemini(api_key, prompt)
                else:
                    st.warning("APIキーと現在の文章を入力してください。")
        with col2:
            if "amz_out" in st.session_state and st.session_state.amz_out:
                st.subheader("✅ 箇条書き")
                st.code(st.session_state.amz_out.get("result_1", ""))
                st.subheader("✅ 紹介文")
                st.write(st.session_state.amz_out.get("result_2", ""))

    # --- 楽天 ---
    with tab_rak:
        st.markdown(f'<div class="status-box">楽天リライト：{genre}</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            rak_curr = st.text_area("1. 現在の文章", height=150, key="rak_c")
            rak_kw = st.text_area("2. 盛り込みたいキーワード", height=80, key="rak_k")
            rak_ben = st.text_area("3. ベネフィット", height=80, key="rak_b")
            if st.button("楽天用リライト実行"):
                if api_key and rak_curr:
                    with st.spinner("リライト中..."):
                        prompt = f"楽天コンサルとして、{genre}（{genre_advice}）を{tone}なトーンで。データ：現状({rak_curr}),キーワード({rak_kw}),体験({rak_ben})。必ず次のJSON形式で：{{'result_1': 'キャッチコピー', 'result_2': '紹介文'}}"
                        st.session_state.rak_out = _call_gemini(api_key, prompt)
        with col2:
            if "rak_out" in st.session_state and st.session_state.rak_out:
                st.subheader("✅ キャッチコピー")
                st.code(st.session_state.rak_out.get("result_1", ""))
                st.subheader("✅ 紹介文")
                st.write(st.session_state.rak_out.get("result_2", ""))

if __name__ == "__main__":
    main()
