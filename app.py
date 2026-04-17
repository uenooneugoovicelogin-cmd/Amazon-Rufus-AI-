import streamlit as st
import google.generativeai as genai
import json
import streamlit.components.v1 as components

# --- ページ設定 ---
st.set_page_config(page_title="🛡️ モール別AI対策ツール", layout="wide")

# CSS: ダークモード対策とデザイン調整
def _inject_custom_style():
    st.markdown("""
    <style>
      /* 全体背景とメインエリアのカードデザイン */
      [data-testid="stAppViewContainer"] { background-color: #f8fafc; }
      div[data-testid="stVerticalBlock"] > div.stColumn {
        background: #ffffff; padding: 25px !important; border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;
      }
      /* 入力・出力エリアの文字色を強制（白飛び防止） */
      textarea { color: #0f172a !important; background-color: #f1f5f9 !important; border: 1px solid #cbd5e1 !important; }
      /* サイドバーのデザイン */
      [data-testid="stSidebar"] { background-color: #0f172a !important; color: white !important; }
      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: white !important; font-weight: 600; }
      /* 実行ボタンの装飾 */
      .stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
        color: white !important; font-weight: bold !important; width: 100%; border-radius: 8px !important;
      }
      /* カウントバッジ */
      .count-badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; margin-bottom: 6px; }
      .badge-ok { background-color: #dcfce7; color: #166534; }
      .badge-ng { background-color: #fee2e2; color: #991b1b; }
    </style>
    """, unsafe_allow_html=True)

# ブラウザ側で確実にコピーを実行する関数
def st_copy_button(text_to_copy, label):
    # 文字列内の改行や引用符を安全に処理
    safe_text = text_to_copy.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$').replace('\n', '\\n')
    html_id = f"btn_{hash(label)}"
    html_code = f"""
    <button id="{html_id}" style="
        background-color: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe;
        padding: 8px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; width: 100%; margin-bottom: 10px;
    ">{label} をコピー</button>
    <script>
    document.getElementById('{html_id}').onclick = function() {{
        navigator.clipboard.writeText(`{safe_text}`).then(() => {{
            const b = document.getElementById('{html_id}');
            const oldText = b.innerText;
            b.innerText = "✅ コピー完了！";
            b.style.backgroundColor = "#dcfce7";
            setTimeout(() => {{ b.innerText = oldText; b.style.backgroundColor = "#eff6ff"; }}, 1500);
        }});
    }};
    </script>
    """
    components.html(html_code, height=50)

def _call_gemini(api_key, model_name, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        res_text = response.text
        if "
http://googleusercontent.com/immersive_entry_chip/0

---

### 今回の修正ポイント
1.  **構文エラーの修正**: `SyntaxError: unterminated string literal` を防ぐため、JavaScript部分を1行にまとめず、Pythonのトリプルクォート（`"""`）を正しく使って安全に保護しました。
2.  **コピーボタンの独立化**: 各ボタンが互いに干渉しないよう、内部で固有のIDを振るようにしました。これにより「別の箇条書きがコピーされる」といったミスを防ぎます。
3.  **文字数カウントの維持**: 箇条書きが100文字を超えた際に赤く表示される機能 はそのまま残してあります。

これでアプリが正常に起動し、コピーボタンも「✅ コピー完了！」と表示されてクリップボードに入るはずです。お試しください！
