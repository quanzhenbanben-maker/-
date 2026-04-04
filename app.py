import streamlit as st
import pandas as pd
import sqlite3
import os
import requests
import re
from dotenv import load_dotenv
from openai import OpenAI  
import googlemaps
import folium
from streamlit_folium import st_folium



load_dotenv() #.envを読み込み

HOTPEPPER_API_KEY   = os.getenv('HOTPEPPER_API_KEY',   '').strip()
OPENAI_API_KEY      = os.getenv('OPENAI_API_KEY',      '').strip()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '').strip()

# ============================================================
# [A担当] STEP1: APIクライアントの初期化
# ============================================================
# 初期化：OpenAIというサービスにアクセスするための「自分専用の窓口」を作る
client = OpenAI(api_key=OPENAI_API_KEY)

# 初期化：Google Maps APIの各機能（ジオコーディングなど）を使うための窓口
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# ホットペッパーには公式ライブラリがないことが多いため、
# requests という標準的な通信ライブラリを使います。
def fetch_hotpepper(shop_id):
    url = "http://webservice.recruit.co.jp/hotpepper/gourmet/v1/"
    params = {
        "key": HOTPEPPER_API_KEY,
        "id": shop_id,
        "format": "json"
    }
    response = requests.get(url, params=params)
    return response.json()

# ============================================================
# [B担当] STEP1: ベクトル検索用ライブラリの初期化
# ============================================================


# ============================================================
# ページ設定（最初に書かないとエラーが出た！）
# ============================================================
st.set_page_config(
    page_title="飲み会幹事コンシェルジュ",
    page_icon="🍺",
    layout="wide"
)

# ============================================================
# カスタムCSS
# ============================================================
st.markdown("""
<style>
.tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    background: #F5F5F5;
    color: #444;
    border: 1px solid #E8E8E8;
    margin: 2px;
}
.review-box {
    background: #FAFAFA;
    border-radius: 8px;
    padding: 12px;
    margin-top: 8px;
    font-size: 13px;
}
.review-meta {
    font-size: 11px;
    color: #AAA;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# DB接続
# ============================================================
def load_shops():  #全店舗データを読み込む
    try:
        conn = sqlite3.connect('nomikai_kanji.db')
        df = pd.read_sql_query("SELECT * FROM shops", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def load_comments(shop_id): #特定の店舗のレビューを読み込む
    try:
        conn = sqlite3.connect('nomikai_kanji.db')
        df = pd.read_sql_query(
            "SELECT * FROM comments WHERE shop_id = ? ORDER BY created_at DESC", 
                      # WHERE shop_id = ? ：特定の店舗のレビューだけに絞り込む
                      # created_at DESC :投稿日時が新しい順に並べる
            conn, params=(shop_id,)
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def save_comment(shop_id, nickname, visited_at, amount, headcount,      # レビューを保存する
                 rating, review, purpose, noise_level):
    conn = sqlite3.connect('nomikai_kanji.db')
    conn.execute("""
        INSERT OR REPLACE INTO comments
        (shop_id, nickname, visited_at, amount_per_person, headcount,
         rating, review, purpose, noise_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (shop_id, nickname, visited_at, amount, headcount,
          rating, review, purpose, noise_level))
    conn.commit()
    conn.close()

# ============================================================
# [A担当] 店舗取得・保存関数
# ============================================================
def fetch_hotpepper_by_url(url):
    # 1. URLから店舗IDを抜き出す
    match = re.search(r'str(J\d+)/', url)
    if not match:
        return None
    shop_id = match.group(1)
    
    # 2. データを取得
    data = fetch_hotpepper(shop_id)
    
    # データが空、またはお店が見つからない場合の安全策
    if not data or data['results']['results_available'] == 0:
        return None
    
    # 3. 0番目のお店情報を変数 s に入れる（アクセスしやすくするため）
    s = data['results']['shop'][0]
    
    # 4. 画像の項目に合わせて辞書を作成して返す
    return {
        "id": s.get('id'),
        "name": s.get('name'),
        "address": s.get('address'),
        "catch": s.get('catch'),
        "desc": s.get('genre', {}).get('catch'), # 説明文としてジャンルのキャッチを使用
        "lat": s.get('lat'),
        "lng": s.get('lng'),
        "google_rating": 0.0, 
        "google_reviews": [], # ← これを追加しておくと⑤の時に便利
        "summary": "",         # ← これを追加しておくと③の時に便利
        "hotpepper_url": url,
        "photo_url": s.get('photo', {}).get('pc', {}).get('l'),
        "budget_night": s.get('budget', {}).get('average'),
        "is_nomihodai": 1 if "あり" in s.get('free_drink', '') else 0,
        "genre": s.get('genre', {}).get('name'),
        "access": s.get('access'),
        "has_private_room": 1 if "あり" in s.get('private_room', '') else 0,
        "is_smoking": 1 if "全面禁煙" not in s.get('non_smoking', '') else 0,
        "is_barrier_free": 1 if "あり" in s.get('barrier_free', '') else 0
    }

def enrich_shop_data(shop):
    """
    ホットペッパーで取得したデータに、Google Mapsの情報を追加する
    """
    # 1. Google Mapsで店名を検索
    places_result = gmaps.places(query=f"{shop['name']} {shop['address']}")
    
    if places_result['status'] == 'OK' and len(places_result['results']) > 0:
            place = places_result['results'][0]
            place_id = place['place_id']
            
            # --- 緯度・経度をGoogleのものに更新 ---
            shop['lat'] = place['geometry']['location']['lat']
            shop['lng'] = place['geometry']['location']['lng']
            
            details = gmaps.place(place_id=place_id, fields=['rating', 'user_ratings_total', 'reviews'])
            
            if 'result' in details:
                r = details['result']
                shop['google_rating'] = r.get('rating', 0.0)
                # 今後使うために口コミも保存
                shop['google_reviews'] = r.get('reviews', [])
            
    return shop


def save_shop_to_db(shop):
    # 1. 戻り値用の変数を共通化する
    target_id = None
    
    # 2. 接続はここだけで行う
    conn = sqlite3.connect('nomikai_kanji.db')
    cursor = conn.cursor()

    try:
        # すでに同じホットペッパーURLがあるか確認
        cursor.execute("SELECT id FROM shops WHERE hotpepper_url = ?", (shop.get('hotpepper_url'),))
        existing_shop = cursor.fetchone()
        
        # 既存IDがあればそれを使う、なければNone
        shop_id = existing_shop[0] if existing_shop else None

        # SQL文（INSERT OR REPLACE）
        sql = """
        INSERT OR REPLACE INTO shops (
            id, name, address, catch, photo_url, budget_night, 
            genre, access, hotpepper_url, lat, lng,
            has_private_room, is_nomihodai, is_smoking, is_barrier_free,
            google_rating, summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            shop_id,
            shop.get('name'),
            shop.get('address'),
            shop.get('catch'),
            shop.get('photo_url'),
            shop.get('budget_night', 0),
            shop.get('genre'),
            shop.get('access'),
            shop.get('hotpepper_url'),
            shop.get('lat'),
            shop.get('lng'),
            shop.get('has_private_room', 0),
            shop.get('is_nomihodai', 0),
            shop.get('is_smoking', 0),
            shop.get('is_barrier_free', 0),
            shop.get('google_rating', 0.0),
            shop.get('summary', '')
        )

        cursor.execute(sql, values)
        conn.commit()

        # 3. 確定したIDをセット（ここが重要！）
        # 上書きした場合は shop_id、新規なら cursor.lastrowid を代入
        if shop_id:
            target_id = shop_id
        else:
            target_id = cursor.lastrowid
            
    except Exception as e:
        st.error(f"DB保存時にエラーが発生しました: {e}")
        target_id = None
    finally:
        conn.close()
    
    # 4. 最後に target_id を返す
    return target_id

def generate_summary(reviews_text):
    """
    Googleの口コミをAIで要約する
    """
    if not reviews_text or len(reviews_text) < 10:
        return "口コミデータが不足しているため、詳細な分析ができません。"

    
    prompt = f"""
    「あなたはプロの飲み会幹事です。提供された複数の口コミから、以下の4点を各項目15文字以内で、合計60文字程度でまとめてください。
    【雰囲気】（例：ガヤガヤ、静か、個室感）
    【推し】（(例: 刺身が絶品/ビールが速い)）
    【懸念】（悪い口コミや注意点(例: トイレが1つ/席が狭い)）
    【総評】（(例: 接待よりは身内向け)

出力形式：
【雰囲気】〇〇 / 【推し】〇〇 / 【懸念】：〇〇 / 【総評】：〇〇」
    {reviews_text}
    """

    try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            # 50文字の文章だけを返す
            return response.choices[0].message.content.strip()
    except:
        return "分析エラー"

def get_embedding(text):
    """
    検索クエリをベクトル化する
    """
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def get_google_reviews(shop_name, address):
    """
    店名と住所からGoogle Mapsの口コミを取得する
    """
    # 1. Place IDを探す
    search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": f"{shop_name} {address}",
        "inputtype": "textquery",
        "fields": "place_id",
        "key": GOOGLE_MAPS_API_KEY
    }
    res = requests.get(search_url, params=params).json()
    
    if not res.get("candidates"):
        return ""

    place_id = res["candidates"][0]["place_id"]

    # 2. 口コミ（Reviews）を取得する
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "reviews",
        "language": "ja",
        "key": GOOGLE_MAPS_API_KEY
    }
    details_res = requests.get(details_url, params=params).json()
    
    reviews = details_res.get("result", {}).get("reviews", [])
    
    # 全ての口コミを1つのテキストにまとめる
    combined_reviews = ""
    for r in reviews:
        combined_reviews += f"【評価:{r['rating']}点】\n{r['text']}\n\n"
        
    return combined_reviews


# ============================================================
# [B担当] 検索ロジック
# ============================================================

def hybrid_search(query, shops_df, budget=None, area=None,
                  room=None, nomihodai=False,
                  non_smoking=False, smoking_ok=False, genre=None):
    pass #pass は「中身は空だけどエラーにしない」という意味。実装するときに pass を削除して中身を書いてって


def get_walk_minutes(area, shops_df):
    pass #pass は「中身は空だけどエラーにしない」という意味。実装するときに pass を削除して中身を書いてって


# ============================================================
# [C担当] レビュー投稿ダイアログ
# ============================================================
@st.dialog("✏️ レビューを投稿する", width="large")
def review_dialog():

    if 'rv_step' not in st.session_state:
        st.session_state.rv_step = 1
    if 'rv_shop_id' not in st.session_state:
        st.session_state.rv_shop_id = None
    if 'rv_shop_name' not in st.session_state:
        st.session_state.rv_shop_name = None

    # ステップ表示
    steps = ["店舗を選ぶ", "レビュー入力", "完了"]
    cols = st.columns(len(steps))
    for i, (col, label) in enumerate(zip(cols, steps), start=1):
        if i < st.session_state.rv_step:
            col.markdown(f"<div style='text-align:center;color:#22C55E;font-size:12px'>✅ {label}</div>", unsafe_allow_html=True)
        elif i == st.session_state.rv_step:
            col.markdown(f"<div style='text-align:center;font-weight:700;font-size:12px'>● {label}</div>", unsafe_allow_html=True)
        else:
            col.markdown(f"<div style='text-align:center;color:#BBB;font-size:12px'>○ {label}</div>", unsafe_allow_html=True)

    st.divider()

    # ============================================================
    # STEP 1: 店舗を選ぶ
    # ※ カードから開いた場合はSTEP2に直接ジャンプ済み
    # ============================================================
    if st.session_state.rv_step == 1:
        st.caption("レビューを書きたいお店を検索してください")

        search_word = st.text_input("🔍 店名で検索", placeholder="例：鳥一筋、銀座 あさみ")

        try:
            conn     = sqlite3.connect('nomikai_kanji.db')
            shops_df = pd.read_sql_query("SELECT id, name FROM shops ORDER BY name", conn)
            conn.close()
        except Exception:
            shops_df = pd.DataFrame(columns=['id', 'name'])

        if shops_df.empty:
            st.warning("登録済みの店舗がありません。先に店舗を登録してください。")
        else:
            if search_word:
                filtered_df = shops_df[shops_df['name'].str.contains(search_word, na=False)]
            else:
                filtered_df = shops_df

            if filtered_df.empty:
                st.warning(f"「{search_word}」に一致する店舗が見つかりませんでした。")
            else:
                selected_name = st.selectbox("店舗を選んでください", filtered_df['name'].tolist())
                selected_id   = int(filtered_df[filtered_df['name'] == selected_name]['id'].values[0])

                if st.button("この店舗にレビューを書く →", type="primary", use_container_width=True):
                    st.session_state.rv_shop_id   = selected_id
                    st.session_state.rv_shop_name = selected_name
                    st.session_state.rv_step      = 2

    # ============================================================
    # STEP 2: レビュー入力
    # ============================================================
    elif st.session_state.rv_step == 2:
        st.info(f"**{st.session_state.rv_shop_name}** にレビューを投稿します")
        st.divider()

        col_back, _ = st.columns([1, 3])
        with col_back:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.rv_step = 1

        nickname = st.text_input("👤 あだ名 *", placeholder="例：さとう")
        rating = st.select_slider(
            "⭐ 総合評価 *",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: "★" * x + "☆" * (5 - x)
        )
        review = st.text_area(
            "📝 レビュー本文 *",
            placeholder="誰といった？食事の提供スピードは？トイレは清潔？会食向き？など、自由に！",
            height=120
        )
        purpose = st.radio(
            "🎯 目的 *",
            ["接待", "会食", "会社の飲み会", "プライベート"],
            horizontal=True
        )
        noise_level = st.radio(
            "🔊 雰囲気 *",
            ["静か", "ふつう", "うるさい"],
            horizontal=True
        )
        amount = st.number_input(
            "💰 一人あたりの金額 *（円）",
            min_value=0, max_value=100000, step=500, value=5000
        )
        with st.expander("任意項目を入力する"):
            visited_at = st.date_input("📅 訪問日", value=None)
            headcount  = st.number_input("👥 人数", min_value=1, max_value=100, step=1, value=4)

        st.divider()

        if st.button("🚀 レビューを投稿する", type="primary", use_container_width=True):
            if not nickname:
                st.warning("あだ名を入力してください")
            elif not review:
                st.warning("レビュー本文を入力してください")
            else:
                with st.spinner("保存中..."):
                    save_comment(
                        shop_id     = st.session_state.rv_shop_id,
                        nickname    = nickname,
                        visited_at  = visited_at,
                        amount      = amount,
                        headcount   = headcount,
                        rating      = rating,
                        review      = review,
                        purpose     = purpose,
                        noise_level = noise_level
                    )
                st.session_state.rv_step = 3

    # ============================================================
    # STEP 3: 完了
    # ============================================================
    elif st.session_state.rv_step == 3:
        st.markdown(f"""
        <div style="text-align:center; padding:32px 0">
            <div style="font-size:48px">🎉</div>
            <div style="font-size:18px; font-weight:700; margin-top:12px">レビューを投稿しました！</div>
            <div style="font-size:13px; color:#888; margin-top:8px; line-height:1.8">
                {st.session_state.get('rv_shop_name', '')} へのレビューが追加されました。
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("閉じる", use_container_width=True):
                st.session_state.rv_step      = 1
                st.session_state.rv_shop_id   = None
                st.session_state.rv_shop_name = None
        with col2:
            if st.button("続けて投稿する", type="primary", use_container_width=True):
                st.session_state.rv_step      = 1
                st.session_state.rv_shop_id   = None
                st.session_state.rv_shop_name = None


# ============================================================
# [C担当] 店舗登録　画面デザイン（画面の上に重なって表示される小さなウィンドウ、ダイアログを使用）
# ============================================================
@st.dialog("🏮 店舗を登録する", width="large")
def register_dialog():

    # st.session_state : 画面をまたいで値を保持する仕組み
    # 1=URL入力 / 2=内容確認 / 3=レビュー入力 / 4=完了
    if 'reg_step' not in st.session_state:  #毎回1にリセットしてしまうと、STEP2に進んでもすぐSTEP1に戻ってしまう。最初の1回だけ初期値を設定するこの書き方が必要
        st.session_state.reg_step = 1
    if 'reg_shop_data' not in st.session_state: #取得した店舗情報（名前・住所・予算など）を一時保存。STEP1で取得してSTEP2・3で表示する
        st.session_state.reg_shop_data = None
    if 'reg_shop_id' not in st.session_state: #DBに保存された店舗のIDを保持。レビューを保存するときにどの店舗へのレビューかを紐付ける。
        st.session_state.reg_shop_id = None
    if 'reg_is_existing' not in st.session_state: #すでに登録済みの店舗かを保持。既存店舗なら True、新規店舗なら False が入り、STEP2をスキップするかどうかの分岐になる
        st.session_state.reg_is_existing = False

    # ステップ表示（既存店舗の場合はSTEP2の内容確認をスキップ）
    if st.session_state.reg_is_existing:
        steps = ["URL入力", "レビュー入力", "完了"]
        step_map = {1: 1, 3: 2, 4: 3}  # reg_step → 表示上のステップ番号
    else:
        steps = ["URL入力", "内容確認", "レビュー入力", "完了"]
        step_map = {1: 1, 2: 2, 3: 3, 4: 4}

    current_display = step_map.get(st.session_state.reg_step, 1)
    cols = st.columns(len(steps))
    for i, (col, label) in enumerate(zip(cols, steps), start=1):
        if i < current_display:
            col.markdown(f"<div style='text-align:center;color:#22C55E;font-size:12px'>✅ {label}</div>", unsafe_allow_html=True)
        elif i == current_display:
            col.markdown(f"<div style='text-align:center;font-weight:700;font-size:12px'>● {label}</div>", unsafe_allow_html=True)
        else:
            col.markdown(f"<div style='text-align:center;color:#BBB;font-size:12px'>○ {label}</div>", unsafe_allow_html=True)

    st.divider()

    # ============================================================
    # STEP 1: URL入力
    # ============================================================
    if st.session_state.reg_step == 1:
        st.caption("ホットペッパーの店舗URLを貼り付けるだけで自動取得します")

        url = st.text_input(
            "ホットペッパーのURL *",
            placeholder="https://www.hotpepper.jp/strJ..."
        )
        
        if st.button("情報を取得する →", type="primary", use_container_width=True):
            if not url:
                st.warning("URLを入力してください")
            else:
                with st.spinner("確認中..."):

                    # 既存チェック（DBにURLが存在するか）
                    try:
                        conn = sqlite3.connect('nomikai_kanji.db')
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT id, name FROM shops WHERE hotpepper_url = ?", (url,)
                        )
                        existing = cursor.fetchone()
                        conn.close()
                    except Exception:
                        existing = None

                    if existing:
                        # 既存店舗 → レビュー入力に直接ジャンプ
                        st.session_state.reg_shop_id     = existing[0]
                        st.session_state.reg_shop_data   = {"name": existing[1]}
                        st.session_state.reg_step        = 3
                        st.session_state.reg_is_existing = True
                    else:
                        # 1. 入力されたURLから、ホットペッパーのデータを取ってくる
                        shop_info = fetch_hotpepper_by_url(url)
                        
                        if shop_info:
                            # 2. 取得に成功したら、そのデータを保存してSTEP2（確認画面）へ
                            shop_info = enrich_shop_data(shop_info)
                            st.session_state.reg_shop_data = shop_info
                            st.session_state.reg_step = 2
                            # 口コミ取得
                            reviews_text = get_google_reviews(shop_info['name'], shop_info['address'])
                            
                            # AI分析結果を直接 summary に入れる
                            shop_info['summary'] = generate_summary(reviews_text)
                            
                            st.session_state.reg_shop_data = shop_info
                            st.session_state.reg_step = 2
                
                        else:
                            # 3. 万が一、変なURLだったりお店が見つからなかった場合
                            st.error("お店の情報を取得できませんでした。URLが正しいか確認してください。")

    # ============================================================
    # STEP 2: 内容確認（新規店舗のみ）
    # ============================================================
    elif st.session_state.reg_step == 2:
        shop = st.session_state.reg_shop_data
        st.success(f"✅ 取得完了：{shop['name']}")

        with st.container(border=True):
            if shop.get('photo_url'):
                st.image(shop['photo_url'], use_container_width=True)

            st.markdown(f"### {shop['name']}")
            st.caption(f"📍 {shop['address']}")

            c1, c2, c3, c4 = st.columns(4)

            # --- 予算表示のクレンジング処理 ---
            budget_val = shop.get('budget_night')
            
 
            match = re.search(r'\d+', re.sub(r',', '', str(budget_val))) if budget_val else None
            
            if match:
                # 最初に見つかった数字の塊を取得
                numeric_str = match.group()
                budget_disp = f"¥{int(numeric_str):,}〜"
                # DB保存用にも数値をセット
                st.session_state.reg_shop_data['budget_night'] = int(numeric_str)
            elif budget_val:
                # 数字はないが文字がある場合
                budget_disp = budget_val
            else:
                budget_disp = "未取得"

            c1.metric("夜の予算", budget_disp)
            c2.metric("Google評価", f"⭐ {shop['google_rating']}" if shop.get('google_rating') else "未取得")
            c3.metric("個室",       "あり" if shop.get('has_private_room') else "なし")
            c4.metric("飲み放題",   "あり" if shop.get('is_nomihodai')    else "なし")

            tags = []
            if shop.get('genre'):             tags.append(f"🍽 {shop['genre']}")
            if shop.get('is_smoking') == 0:   tags.append("🚭 全席禁煙")
            if shop.get('is_barrier_free'):   tags.append("♿ バリアフリー")
            st.markdown(
                " ".join([f'<span class="tag">{t}</span>' for t in tags]),
                unsafe_allow_html=True
            )

        col_back, col_next = st.columns([1, 2])
        with col_back:
            if st.button("← 戻る", use_container_width=True):
                st.session_state.reg_step = 1
          
        with col_next:
            if st.button("レビューを書く →", type="primary", use_container_width=True):
                st.session_state.reg_step = 3
         

    # ============================================================
    # STEP 3: レビュー入力
    # ============================================================
    elif st.session_state.reg_step == 3:
        shop = st.session_state.reg_shop_data

        # 既存・新規でメッセージを出し分け
        if st.session_state.reg_is_existing:
            st.info(f"⚠️ **{shop['name']}** はすでに登録済みです。\nそのままレビューを投稿できます。")
        else:
            st.markdown(f"**{shop['name']}** のレビューを書いてください")
            st.caption("店舗登録と同時にレビューも残しましょう！")

        st.divider()

        nickname = st.text_input("👤 あだ名 *", placeholder="例：さとう")

        rating = st.select_slider(
            "⭐ 総合評価 *",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: "★" * x + "☆" * (5 - x)
        )

        review = st.text_area(
            "📝 レビュー本文 *",
            placeholder="誰といった？食事の提供スピードは？トイレは清潔？会食向き？など、自由に！",
            height=120
        )

        purpose = st.radio(
            "🎯 目的 *",
            ["接待", "会食", "会社の飲み会", "プライベート"],
            horizontal=True
        )

        noise_level = st.radio(
            "🔊 雰囲気 *",
            ["静か", "ふつう", "うるさい"],
            horizontal=True
        )

        amount = st.number_input(
            "💰 一人あたりの金額 *（円）",
            min_value=0,
            max_value=100000,
            step=500,
            value=5000
        )

        with st.expander("任意項目を入力する"):
            visited_at = st.date_input("📅 訪問日", value=None)
            headcount  = st.number_input(
                "👥 人数",
                min_value=1,
                max_value=100,
                step=1,
                value=4
            )

        st.divider()

        col_back, col_save = st.columns([1, 2])
        with col_back:
            if st.button("← 戻る", use_container_width=True):
                # 既存店舗はSTEP1に戻る、新規はSTEP2に戻る
                if st.session_state.reg_is_existing:
                    st.session_state.reg_step = 1
                else:
                    st.session_state.reg_step = 2

        with col_save:
            btn_label = "🚀 レビューを投稿する" if st.session_state.reg_is_existing else "🚀 登録してレビューを投稿する"
            if st.button(btn_label, type="primary", use_container_width=True):
                if not nickname:
                    st.warning("あだ名を入力してください")
                elif not review:
                    st.warning("レビュー本文を入力してください")
                else:
                    with st.spinner("保存中..."):
                        # --- 1. 金額の掃除 ---
                        amount_str = str(amount)
                        numeric_amount = re.sub(r'\D', '', amount_str)
                        amount_int = int(numeric_amount) if numeric_amount else 0

                        # --- 2. 保存先の shop_id を決定する ---
                        if st.session_state.reg_is_existing:
                            # 既存店舗なら、保持していたIDを使う
                            target_shop_id = st.session_state.reg_shop_id
                        else:
                            # 新規店舗なら、まず店舗をDBに保存して新しいIDを取得
                            raw_budget = str(st.session_state.reg_shop_data.get('budget_night', '0'))
                            match = re.search(r'\d+', re.sub(r',', '', raw_budget))
                            
                            if match:
                                st.session_state.reg_shop_data['budget_night'] = int(match.group())
                            else:
                                st.session_state.reg_shop_data['budget_night'] = 0

                            # 店舗保存！
                            target_shop_id = save_shop_to_db(st.session_state.reg_shop_data)

                        # --- 3. 決定したIDでレビューを保存 ---
                        if target_shop_id:
                            save_comment(
                                shop_id     = target_shop_id, # ここを共通の変数にする
                                nickname    = nickname,
                                visited_at  = visited_at,
                                amount      = amount_int,
                                headcount   = headcount,
                                rating      = rating,
                                review      = review,
                                purpose     = purpose,
                                noise_level = noise_level
                            )
                            # 保存が終わったら完了画面（STEP 4）へ
                            st.session_state.reg_step = 4
                            st.rerun()
                        else:
                            st.error("店舗の保存に失敗したため、レビューを保存できませんでした。")

    # ============================================================
    # STEP 4: 完了
    # ============================================================
    elif st.session_state.reg_step == 4:
        if st.session_state.reg_is_existing:
            title = "レビューを投稿しました！"
            sub   = "レビューが追加されました。"
        else:
            title = "登録完了！"
            sub   = "店舗とレビューを保存しました。<br>検索結果に表示されるようになります。"

        st.markdown(f"""
        <div style="text-align:center; padding:32px 0">
            <div style="font-size:48px">🎉</div>
            <div style="font-size:18px; font-weight:700; margin-top:12px">{title}</div>
            <div style="font-size:13px; color:#888; margin-top:8px; line-height:1.8">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("閉じる", use_container_width=True):
                st.session_state.reg_step        = 1
                st.session_state.reg_shop_data   = None
                st.session_state.reg_shop_id     = None
                st.session_state.reg_is_existing = False
        with col2:
            if st.button("続けて登録する", type="primary", use_container_width=True):
                st.session_state.reg_step        = 1
                st.session_state.reg_shop_data   = None
                st.session_state.reg_shop_id     = None
                st.session_state.reg_is_existing = False


# ============================================================
# [C担当] メインのヒーローエリアデザイン 、横いっぱいにしてみた
# ============================================================
col_hero, col_img = st.columns([1, 1])

with col_hero:
    st.markdown("""
    <div style="padding: 32px 0 24px">
        <div style="font-size:36px; font-weight:900; line-height:1.3; margin-bottom:12px">
            幹事の強い味方、<br>ここにあります。
        </div>
        <div style="font-size:14px; color:#666; line-height:1.8; margin-bottom:24px">
            社内データベースを活用した飲食店検索・管理ツール。<br>
            最適なお店を数秒で見つけましょう。
        </div>
    </div>
    """, unsafe_allow_html=True)

    hero_col1, hero_col2 , hero_col3 = st.columns([1, 1, 1])
    with hero_col1:
        search_hero = st.button(
            "🔍 お店を探す",
            use_container_width=True,
            type="primary"
        )
    with hero_col2:
        register_hero = st.button(
            "＋ 店舗を登録する",
            use_container_width=True
        )
    with hero_col3:
        review_hero = st.button(
            "✏️ レビューを書く",
            use_container_width=True
        )

with col_img:
    st.image(
        "Gemini_Generated_Image_u7jbhtu7jbhtu7jb.png",
        use_container_width=True
    )

st.divider()

# ============================================================
# [C担当] 検索バーデザイン
# ============================================================
# 余白
st.markdown("<div style='margin: 25px 0'></div>", unsafe_allow_html=True)

# 枠で囲ってわかりやすくしてみた
with st.container(border=True):
    search_col, btn_col = st.columns([6, 1])
    with search_col:
        query = st.text_input(
            "",
            placeholder="例：新宿　個室　居酒屋",
            label_visibility="collapsed"
     )
        st.caption("⚡ キーワードを入力してください")
    with btn_col:
        search_btn = st.button("🔍 検索", use_container_width=True, type="primary")

# 余白
st.markdown("<div style='margin: 50px 0'></div>", unsafe_allow_html=True)

# ============================================================
# ダイアログの呼び出し（left_col/right_colの前に書く!!）
# ============================================================
if register_hero or st.session_state.get('show_register'):
    st.session_state['show_register'] = False
    register_dialog()
 
if review_hero or st.session_state.get('show_review'):
    st.session_state['show_review'] = False
    review_dialog()


# ============================================================
# [B担当] 検索・フィルター処理
# ============================================================
# 検索ボタンまたは絞り込みボタンが押されたときに呼ぶ




# ============================================================
# [C担当] 絞り込み条件 + 店舗カード（左右レイアウト）
# ============================================================

left_col, right_col = st.columns([1, 3])
with left_col:
    with st.container(border=True):  # 外枠で囲む
        # 本当は背景色も変えたかったけどstreamlitは厳しいので諦め…
        st.markdown("**絞り込み条件**")
        area = st.text_input("📍 エリア・駅名", placeholder="例：新橋、渋谷 など")
        budget = st.slider(
            "¥ 最大予算（夜・一人あたり）",
            min_value=3000, max_value=15000,
            value=10000, step=500, format="¥%d"
        )
        st.markdown("**🎯 目的**")
        purpose_options = ["接待", "会食", "会社の飲み会", "プライベート"]
        purposes = [p for p in purpose_options
                    if st.checkbox(p, key=f"purpose_{p}")]
        st.markdown("**🚪 個室・人数**")
        room = st.radio(
            "",
            ["こだわらない", "小人数（〜4名）", "大人数（5名〜）"],
            label_visibility="collapsed"
        )
        nomihodai   = st.checkbox("🍺 飲み放題あり限定")
        st.markdown("**🚬 喫煙**")
        non_smoking = st.checkbox("全席禁煙のみ")
        smoking_ok  = st.checkbox("喫煙可のみ")
        genre = st.selectbox("🍽 ジャンル", [
            "すべて", "居酒屋", "ダイニングバー・バル", "創作料理",
            "和食", "洋食", "イタリアン・フレンチ", "中華",
            "焼肉・ホルモン", "アジア・エスニック料理", "各国料理",
            "カラオケ・パーティ", "バー・カクテル", "ラーメン",
            "お好み焼き・もんじゃ", "カフェ・スイーツ", "その他グルメ",
        ])
        filter_btn = st.button(
            "この条件で絞り込む",
            use_container_width=True,
            type="primary"
        )
        st.divider()
        if st.button("＋ 店舗を登録する", use_container_width=True, key="register_sidebar"):
            st.session_state['show_register'] = True


with right_col:
    # ============================================================
    # [C担当] 店舗カード表示デザイン
    # ============================================================
    shops_df = load_shops()

    if shops_df.empty:
        st.info("まだ店舗が登録されていません。「店舗を登録する」ボタンから登録してください。")
    else:
        result_col, sort_col = st.columns([3, 1])
        with result_col:
            st.markdown(f"**{len(shops_df)}件**のお店が見つかりました")
        with sort_col:
            sort = st.selectbox(
                "",
                ["Google評価順", "予算が安い順", "レビューが多い順"],
                label_visibility="collapsed"
            )

   
    # ============================================================
    # [C担当] 地図を入れるなら（検索結果の最上部にまとめて表示させる）
    # ============================================================


    map_df = shops_df.dropna(subset=['lat', 'lng'])

    if not map_df.empty:
        center_lat = map_df['lat'].mean()
        center_lng = map_df['lng'].mean()

        m = folium.Map(location=[center_lat, center_lng], zoom_start=14)

        for _, row in map_df.iterrows():
            # レビューを取得
            comments_df_map = load_comments(int(row['id']))
            review_html = ""
            if not comments_df_map.empty:
                r = comments_df_map.iloc[0]
                stars = "★" * int(r['rating']) + "☆" * (5 - int(r['rating']))
                review_html = f"""
                <hr style="margin:6px 0">
                <div style="font-size:12px">
                    💬 <b>{r['nickname']}</b> {stars}<br>
                    {r['review'][:50]}{'...' if len(r['review']) > 50 else ''}
                </div>
                """

            popup_html = f"""
            <div style="font-size:13px; min-width:150px">
                <b>{row['name']}</b><br>
                📍 {row.get('address', '')}<br>
                ⭐ {row.get('google_rating', '')}　¥{row.get('budget_night', '')}〜
                {review_html}
                <hr style="margin:6px 0">
                <a href="{row.get('hotpepper_url', '')}" target="_blank">
                    ホットペッパーで見る →
                </a>
            </div>
            """
            folium.Marker(
                location=[row['lat'], row['lng']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=row['name'],
                icon=folium.Icon(color='red', icon='cutlery', prefix='fa')
            ).add_to(m)
    
        st_folium(m, use_container_width=True, height=350)
    else:
        st.caption("📍 店舗が登録されると地図が表示されます")
   

    #============================================================
    # [B担当] ソート処理を実装する(Google評価順", "予算が安い順", "レビューが多い順)
    #============================================================





    for _, shop in shops_df.iterrows():
        with st.container(border=True):
            img_col, info_col = st.columns([0.5, 2])

            with img_col:
                # 左空白・画像・右空白の3列で中央揃え
                    _, center, _ = st.columns([0.2, 4, 0.2])
                    with center:
                        if shop.get('photo_url'):
                            st.image(shop['photo_url'], width=200)
                        else:
                            st.markdown("""
                            <div style="height:90px; background:#F0F0F0; border-radius:8px;
                                        display:flex; align-items:center; justify-content:center;
                                        color:#BBB; font-size:12px">
                                🏮 画像なし
                            </div>
                            """, unsafe_allow_html=True)

            with info_col:
                name_col, rating_col = st.columns([3, 1])
                with name_col:
                    st.markdown(f"### {shop['name']}")
                    if shop.get('address'):
                        st.caption(f"📍 {shop['address']}")
                with rating_col:
                    if shop.get('google_rating'):
                        st.metric("Google評価", f"⭐ {shop['google_rating']}")
            
                # 口コミ分析・タグ・金額を右寄せで表示
                ambiance = shop.get('summary', '')#AIによる室内の雰囲気分析
                if ambiance:
                    st.caption(f"**口コミ分析:** {ambiance}")

                #============================================================
                # [B担当] 徒歩分数の表示
                #============================================================
                




                tags = []
                if shop.get('has_private_room'):
                   cap = f"〜{shop['private_capacity']}名" if shop.get('private_capacity') else ""
                   tags.append(f"🚪 完全個室{cap}")
                if shop.get('is_nomihodai'):
                    tags.append("🍺 飲み放題")
                if shop.get('is_smoking') == 0:
                    tags.append("🚭 全席禁煙")
                if shop.get('is_barrier_free'):
                    tags.append("♿ バリアフリー")
                if shop.get('genre'):
                    tags.append(f"🍽 {shop['genre']}")

                st.markdown(
                    " ".join([f'<span class="tag">{t}</span>' for t in tags]),
                    unsafe_allow_html=True
                )

                price_col, btn_col = st.columns([2, 1])
                with price_col:
                    if shop.get('budget_night'):
                        # 予算データを取り出す（空なら '0' にしておく）
                        raw_budget = str(shop.get('budget_night', '0'))

                        # 数字だけを抜き出す（例：「平均：8000円」→「8000」）
                        numeric_budget = re.sub(r'\D', '', raw_budget)

                        if numeric_budget:
                            # 数字があればカンマ区切りで表示
                            disp_budget = f"¥{int(numeric_budget):,}〜"
                        else:
                            # 数字が全くなければ、元の文字をそのまま出すか「未設定」とする
                            disp_budget = raw_budget if raw_budget != '0' else "予算情報なし"

                        st.markdown(f"**{disp_budget}**")
                with btn_col:
                    if shop.get('hotpepper_url'):
                        st.link_button(
                            "ホットペッパーで見る →",
                            shop['hotpepper_url'],
                            use_container_width=True
                        )

            st.divider()
            comments_df = load_comments(int(shop['id']))

            rev_header, rev_count = st.columns([3, 1])
            with rev_header:
                st.markdown("💬 **社内レビュー**")
            with rev_count:
                if not comments_df.empty:
                    st.caption(f"{len(comments_df)}件")
                else:
                    st.caption("まだレビューなし")

            #　レビューコメントの表示について
            if not comments_df.empty:
                for _, row in comments_df.iterrows():  # 全件ループ
                    stars = "★" * int(row['rating']) + "☆" * (5 - int(row['rating']))
                    st.markdown(f"""
                    <div class="review-box">
                        <div>
                            <strong>{row['nickname']}</strong>
                            &nbsp;<span style="background:#F0F0F0; padding:1px 7px;
                            border-radius:10px; font-size:11px">{row.get('purpose','')}</span>                                &nbsp;<span style="color:#F4A444">{stars}</span>
                            </div>
                        <div style="margin-top:6px">{row['review']}</div>
                        <div class="review-meta">
                            ¥{int(row['amount_per_person']):,}/人 ·
                            {row.get('headcount','') or ''}名で利用 ·
                            {str(row.get('created_at',''))[:10]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            #============================================================
            # [C担当] レビュー投稿ダイアログの呼び出し（実装済み）
            #============================================================
            if st.button(
                "＋ レビューを書く" if not comments_df.empty else "＋ 最初のレビューを書く",
                key=f"review_btn_{shop['id']}",
                use_container_width=True
            ):
                st.session_state['rv_shop_id']   = int(shop['id'])
                st.session_state['rv_shop_name'] = shop['name']   
                st.session_state['rv_step']      = 2
                st.session_state['show_review']  = True
 