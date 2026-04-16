import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="Amazon Rufus対策 楽天 AI/SEO対策", layout="wide")

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
        "スポーツ": "運動性能、耐久性、吸汗速乾性を強調。",
        "アウトドア": "過酷な環境での信頼性、携帯性、設営のしやすさを重視。",
        "大人コスチューム": "イベントでの写真映え、生地の質感、セット内容を強調。",
        "子供コスチューム": "安全性、着脱のしやすさ、子供が喜ぶデザイン性を強調。",
        "ベビー": "安全基準（PSC等）、肌触り、衛生面を最優先。",
        "ペット": "快適性と健康、飼い主のお手入れのしやすさを中心に構成。",
        "園芸": "育てやすさ、サイズ感、緑のある暮らしの豊かさを表現。",
        "手芸・ハンドメイド": "素材の品質、加工のしやすさ、創作の楽しさを強調。",
        "介護": "利用者の自立支援、介助者の負担軽減、安全性を最優先。",
        "ハロウィン雑貨": "パーティーの盛り上がり、装飾のインパクトを演出。",
        "クリスマス雑貨": "温かみ、家族との時間、ギフトとしての魅力を強調。",
        "推し活": "収納力、透明度、大切なグッズを守る性能を強調。",
        "生活雑貨・日用品": "日常の不便解消、コスパ、耐久性を強調。",
        "革財布": "本革の質感、エイジング、高級感とギフト適性を訴求。",
        "スリッパ・サンダル": "履き心地、クッション性、滑り止めを重視。",
        "ファッション": "シルエットの美しさ、着回し力、トレンド感を表現。",
        "時計ベルト": "耐久性、装着感、手持ちの時計との相性を強調。"
    }
    return instructions.get(genre, "商品の品質を客観的に説明してください。")

def _call_gemini_safe(api_key, prompt_text):
    try:
        genai.configure(api_key=api_key)
        
        # 2026年現在の利用可能リストに基づき、Flashモデル（制限が緩い）を優先
        model_priority = ['gemini-3.0-flash-latest', 'gemini-2.5-flash', 'gemini-1.5-flash']
        
        res_text = ""
        for name in model_priority:
            try:
                model = genai.GenerativeModel(name)
                response = model.generate_content(prompt_text)
                res_text = response.text
                break
            except Exception:
                continue
        
        if not res_text:
            # 最終手段：リストから自動取得
            available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            model = genai.GenerativeModel(available[0])
            res_text = model.generate_content(prompt_text).text

        # JSON抽出
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0].strip()
        return json.loads(res_text)

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            st.error("🚨 APIの利用制限（Quota Exceeded）にかかっています。数分待ってから再度お試しください。")
        else:
            st.error(f"⚠️ エラーが発生しました: {error_msg}")
        return None

def main():
    _inject_css()
    st.title("Amazon Rufus対策 楽天 AI/SEO対策") # タイトルを復旧
    
    with st.sidebar:
        st.header("🔑 設定")
        api_key = st.text_input("Gemini API Key", type="password")
        st.divider()
        genre_list = ["スポーツ", "アウトドア", "大人コスチューム", "子供コスチューム", "ベビー", "ペット", "園芸", "手芸・ハンドメイド", "介護", "ハロウィン雑貨", "クリスマス雑貨", "推し活", "生活雑貨・日用品", "革財布", "スリッパ・サンダル", "ファッション", "時計ベルト"]
        genre = st.selectbox("商品ジャンル", genre_list)
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・賑やか", "簡潔・ロジカル"])
        genre_advice = get_genre_instruction(genre)

    tab_amz, tab_rak = st.tabs(["Amazon Rufus対策", "楽天 AI/SEO対策"])

    with tab_amz:
        st.markdown(f'<div class="status-box">Amazon：{genre}（{tone}）</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            amz_curr = st.text_area("1. 現在の文章", height=150, key="amz_c")
            amz_supp = st.text_area("2. 補足スペック・Q&A", height=100, key="amz_s")
            amz_rev = st.text_area("3. カスタマーレビュー", height=100, key="amz_r")
            if st.button("Amazon用リライト実行"):
                if api_key and amz_curr:
                    with st.spinner("最新モデルでリライト中..."):
                        prompt = f"Amazon専門ライターとして{genre}（{genre_advice}）を{tone}で。データ：現状({amz_curr}),補足({amz_supp}),レビュー({amz_rev})。必ずJSON形式：{{'result_1': '箇条書き5点', 'result_2': '紹介文'}}"
                        st.session_state.amz_out = _call_gemini_safe(api_key, prompt)

        with col2:
            if "amz_out" in st.session_state and st.session_state.amz_out:
                st.subheader("✅ 箇条書き")
                st.code(st.session_state.amz_out.get("result_1", ""))
                st.subheader("✅ 紹介文")
                st.write(st.session_state.amz_out.get("result_2", ""))

    with tab_rak:
        st.markdown(f'<div class="status-box">楽天：{genre}（{tone}）</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            rak_curr = st.text_area("1. 現在の文章", height=150, key="rak_c")
            rak_kw = st.text_area("2. 盛り込みたいキーワード", height=100, key="rak_k")
            rak_ben = st.text_area("3. ベネフィット", height=100, key="rak_b")
            if st.button("楽天用リライト実行"):
                if api_key and rak_curr:
                    with st.spinner("最新モデルでリライト中..."):
                        prompt = f"楽天コンサルとして{genre}（{genre_advice}）を{tone}で。データ：現状({rak_curr}),KW({rak_kw}),体験({rak_ben})。必ずJSON形式：{{'result_1': 'キャッチコピー', 'result_2': '紹介文'}}"
                        st.session_state.rak_out = _call_gemini_safe(api_key, prompt)

        with col2:
            if "rak_out" in st.session_state and st.session_state.rak_out:
                st.subheader("✅ キャッチコピー")
                st.code(st.session_state.rak_out.get("result_1", ""))
                st.subheader("✅ 紹介文")
                st.write(st.session_state.rak_out.get("result_2", ""))

if __name__ == "__main__":
    main()import streamlit as st
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
