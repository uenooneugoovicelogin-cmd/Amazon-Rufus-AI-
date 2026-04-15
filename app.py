import streamlit as st
import google.generativeai as genai
import json

# --- ページ設定 ---
st.set_page_config(page_title="プロ仕様｜モール別AIリライトツール", layout="wide")

def _inject_css() -> None:
    st.markdown("""
    <style>
      :root {
        --bg: #f8f9fa;
        --card: #ffffff;
        --text: #1a1a1a;
        --accent: #007185;
      }
      .stApp { background-color: var(--bg); }
      textarea { background-color: #ffffff !important; border-radius: 8px !important; }
      div.stButton > button {
        background-color: #ffd814 !important;
        border: 1px solid #fcd200 !important;
        color: #111 !important;
        width: 100%;
        font-weight: bold !important;
      }
      .status-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #e7f3f3;
        border-left: 5px solid #007185;
        margin-bottom: 20px;
      }
    </style>
    """, unsafe_allow_html=True)

def get_genre_instruction(genre):
    """ジャンルごとにAIへの追加指示（隠しプロンプト）を生成する"""
    instructions = {
        "スポーツ": "運動性能、耐久性、吸汗速乾性などの機能面を強調し、アクティブな使用シーンを想起させてください。",
        "アウトドア": "過酷な環境での信頼性、携帯性、設営のしやすさなど、実用性を重視した表現にしてください。",
        "大人コスチューム": "イベントでの写真映え、生地の質感、セット内容の充実度を強調してください。",
        "子供コスチューム": "肌への優しさ、着脱のしやすさ、安全性、そして子供が喜ぶデザイン性を強調してください。",
        "ベビー": "安全基準（PSC、食品衛生法等）、肌触り、衛生面を最優先し、保護者の安心感に寄り添ってください。",
        "ペット": "ペットの快適性と健康、飼い主のお手入れのしやすさを中心に構成してください。",
        "園芸": "育てやすさ、耐久性、サイズ感、そして緑のある暮らしの豊かさを表現してください。",
        "手芸・ハンドメイド": "素材の品質、加工のしやすさ、仕上がりの美しさ、創作の楽しさを強調してください。",
        "介護": "利用者の自立支援、介助者の負担軽減、安全性、信頼感を最優先し、誠実なトーンで作成してください。",
        "ハロウィン雑貨": "パーティーの盛り上がり、装飾のインパクト、季節限定のワクワク感を演出してください。",
        "クリスマス雑貨": "温かみのある雰囲気、家族や恋人との時間、ギフトとしての魅力を強調してください。",
        "推し活": "収納力、透明度、持ち運びのしやすさ、大切なグッズを守る性能を強調してください。",
        "生活雑貨・日用品": "日常のちょっとした不便を解消する点や、コスパ、長く使える耐久性を強調してください。",
        "革財布": "本革の質感、エイジング（経年変化）、縫製の丁寧さ、高級感とギフト適性を訴求してください。",
        "スリッパ・サンダル": "履き心地、クッション性、滑り止め、通気性など、足元の快適さを重視してください。",
        "ファッション": "シルエットの美しさ、着回し力、トレンド感、着用時の高揚感を表現してください。",
        "時計ベルト": "素材の耐久性、装着感、手持ちの時計との相性、着せ替えの楽しさを強調してください。"
    }
    return instructions.get(genre, "商品の利便性と品質を客観的に説明してください。")

def _call_gemini(api_key: str, model_id: str, prompt_text: str):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=f"models/{model_id}")
    response = model.generate_content(prompt_text)
    try:
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception:
        return {"result_1": "生成エラー", "result_2": response.text}

def main():
    _inject_css()
    st.title("📦 モール別 AI特化型 商品紹介文ジェネレーター")
    
    with st.sidebar:
        st.header("🔑 認証・設定")
        api_key = st.text_input("Gemini API Key", type="password")
        model_id = st.selectbox("使用モデル", ["gemini-1.5-flash", "gemini-2.0-flash"])
        
        st.divider()
        st.header("🎨 カテゴリ・トーン設定")
        # ご指定のジャンルリスト
        genre_list = [
            "スポーツ", "アウトドア", "大人コスチューム", "子供コスチューム", "ベビー", "ペット", 
            "園芸", "手芸・ハンドメイド", "介護", "ハロウィン雑貨", "クリスマス雑貨", "推し活", 
            "生活雑貨・日用品", "革財布", "スリッパ・サンダル", "ファッション", "時計ベルト"
        ]
        genre = st.selectbox("商品ジャンル", genre_list)
        tone = st.radio("文章のトーン", ["誠実・信頼（推奨）", "情熱的・賑やか", "簡潔・ロジカル"])
        
        # ジャンルごとの個別指示を内部で取得
        genre_advice = get_genre_instruction(genre)

    tab_amz, tab_rak = st.tabs(["Amazon Rufus対策", "楽天 AI/SEO対策"])

    # ==========================================
    # Amazon タブ
    # ==========================================
    with tab_amz:
        st.markdown(f'<div class="status-box">Amazon Rufus対策：ジャンル「{genre}」に最適化し、客観的な事実とQ&Aに対応した文章を生成します。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            amz_curr = st.text_area("1. 現在の文章（箇条書き・説明文）", height=150, key="amz_c")
            amz_supp = st.text_area("2. 補足スペック・Q&A情報", height=100, key="amz_s")
            amz_rev = st.text_area("3. カスタマーレビュー（不満点・好評点）", height=100, key="amz_r")
            
            if st.button("Amazon用リライト実行"):
                if not api_key or not amz_curr:
                    st.error("APIキーと現在の文章を入力してください。")
                else:
                    with st.spinner("生成中..."):
                        prompt = f"""あなたはAmazon専門コピーライターです。
ジャンル：{genre}（{genre_advice}）、トーン：{tone} で作成してください。

【重要ルール】
・不当表示を避け、信頼性を最優先。
・箇条書きは冒頭の【】にメリットを書き、続く文章で事実（根拠）を述べる。
・Rufusが比較回答しやすいよう「具体的な数値」や「用途」を盛り込む。

【データ】
現状：{amz_curr}
補足：{amz_supp}
レビュー：{amz_rev}

JSON：{{"result_1": "修正後の箇条書き5点", "result_2": "紹介文"}}"""
                        st.session_state.amz_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "amz_out" in st.session_state:
                st.subheader("✅ 最適化済み：箇条書き")
                st.code(st.session_state.amz_out.get("result_1", ""))
                st.subheader("✅ 最適化済み：紹介文")
                st.write(st.session_state.amz_out.get("result_2", ""))

    # ==========================================
    # 楽天 タブ
    # ==========================================
    with tab_rak:
        st.markdown(f'<div class="status-box">楽天SEO対策：ジャンル「{genre}」に最適化し、キーワード網羅と感情的な訴求を両立させます。</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            rak_curr = st.text_area("1. 現在の商品説明文", height=150, key="rak_c")
            rak_kw = st.text_area("2. 盛り込みたいキーワード", height=100, key="rak_k")
            rak_ben = st.text_area("3. ベネフィット・感動体験", height=100, key="rak_b")
            
            if st.button("楽天用リライト実行"):
                if not api_key or not rak_curr:
                    st.error("APIキーと現在の文章を入力してください。")
                else:
                    with st.spinner("生成中..."):
                        prompt = f"""あなたは楽天ECコンサルタントです。
ジャンル：{genre}（{genre_advice}）、トーン：{tone} で作成してください。

【重要ルール】
・「スマホユーザー」がスクロールしながら読んでも頭に入るリズム。
・指定キーワードを自然に、かつ強力に盛り込む。
・その商品を買った後の「生活の変化」を魅力的に描写する。

【データ】
現状：{rak_curr}
キーワード：{rak_kw}
体験：{rak_ben}

JSON：{{"result_1": "キャッチコピー案", "result_2": "紹介文"}}"""
                        st.session_state.rak_out = _call_gemini(api_key, model_id, prompt)

        with col2:
            if "rak_out" in st.session_state:
                st.subheader("✅ 魅力的なキャッチコピー")
                st.code(st.session_state.rak_out.get("result_1", ""))
                st.subheader("✅ 購買意欲を高める紹介文")
                st.write(st.session_state.rak_out.get("result_2", ""))

if __name__ == "__main__":
    main()
