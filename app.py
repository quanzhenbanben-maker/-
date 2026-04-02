import streamlit as st
import pandas as pd
import sqlite3
import os
import requests
import re
from dotenv import load_dotenv

load_dotenv() #.envを読み込み

HOTPEPPER_API_KEY   = os.getenv('HOTPEPPER_API_KEY',   '').strip()
OPENAI_API_KEY      = os.getenv('OPENAI_API_KEY',      '').strip()
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '').strip()

# ============================================================
# [A担当] STEP1: APIクライアントの初期化
# ============================================================

 
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
        INSERT INTO comments
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
    pass  #pass は「中身は空だけどエラーにしない」という意味。実装するときに pass を削除して中身を書いてって


def save_shop_to_db(shop):
    pass #pass は「中身は空だけどエラーにしない」という意味。実装するときに pass を削除して中身を書いてって



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
                        # 新規店舗 → ダミーデータ（Aが実装するまで）
                        st.session_state.reg_shop_data = {
                            "name":             "銀座 鮨処 あさみ",
                            "address":          "東京都中央区銀座5-1-1",
                            "budget_night":     8000,
                            "google_rating":    4.3,
                            "has_private_room": True,
                            "private_capacity": 6,
                            "is_nomihodai":     True,
                            "is_smoking":       0,
                            "is_barrier_free":  True,
                            "genre":            "和食・日本料理",
                            "photo_url":        None,
                            "hotpepper_url":    url,
                        }
                        st.session_state.reg_step        = 2
                        st.session_state.reg_is_existing = False

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
            c1.metric("夜の予算",   f"¥{shop['budget_night']:,}" if shop.get('budget_night')   else "未取得")
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
                        if st.session_state.reg_is_existing:
                            # 既存店舗 → レビューだけ保存
                            save_comment(
                                shop_id     = st.session_state.reg_shop_id,
                                nickname    = nickname,
                                visited_at  = visited_at,
                                amount      = amount,
                                headcount   = headcount,
                                rating      = rating,
                                review      = review,
                                purpose     = purpose,
                                noise_level = noise_level
                            )
                        else:
                            # ============================================================
                            # [A担当] 新規店舗をDBに保存してレビューも登録する
                            # 1. save_shop_to_db(shop) を呼んでshop_idを取得
                            # 2. save_comment() でレビューを保存
                            # 実装したら下記のpassを削除すること
                            # ============================================================
                            pass
                            
                    st.session_state.reg_step = 4

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
# [C担当] メインのヒーローエリアデザイン
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

    hero_col1, hero_col2 = st.columns([1, 1])
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

with col_img:
    st.image(
        "Gemini_Generated_Image_u7jbhtu7jbhtu7jb.png",
        use_container_width=True
    )

st.divider()

# ============================================================
# [C担当] 検索バーデザイン
# ============================================================
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

# ============================================================
# [C担当] サイドバー：絞り込み条件　デザイン
# ============================================================
with st.sidebar:
    st.header("絞り込み条件")

    area = st.text_input("📍 エリア・駅名", placeholder="例：新橋、渋谷 など")

    budget = st.slider(
        "¥ 最大予算（夜・一人あたり）",
        min_value=3000,
        max_value=15000,
        value=10000,
        step=500,
        format="¥%d"
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

    nomihodai = st.checkbox("🍺 飲み放題あり限定")

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

    if st.button("＋ 店舗を登録する", use_container_width=True):
        st.session_state['show_register'] = True

# ============================================================
# ダイアログの呼び出し（サイドバーのwithブロックの外）
# ============================================================
if register_hero or st.session_state.get('show_register'):
    st.session_state['show_register'] = False
    register_dialog()

# ============================================================
# [B担当] 検索・フィルター処理
# ============================================================
# 検索ボタンまたは絞り込みボタンが押されたときに呼ぶ






# ============================================================
# [C担当] 店舗カード表示デザイン
# ============================================================
st.divider()

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
    # [C担当] 地図を入れるなら（検索結果の最上部にまとめて表示させる？）
    # ============================================================
    
   

    #============================================================
    # [B担当] ソート処理を実装する(Google評価順", "予算が安い順", "レビューが多い順)
    #============================================================





    for _, shop in shops_df.iterrows():
        with st.container(border=True):
            img_col, info_col = st.columns([1, 3])

            with img_col:
                if shop.get('photo_url'):
                    st.image(shop['photo_url'], use_container_width=True)
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
                with rating_col:
                    if shop.get('google_rating'):
                        st.metric("Google評価", f"⭐ {shop['google_rating']}")
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
                        st.markdown(f"**¥{int(shop['budget_night']):,}〜**")
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

            if not comments_df.empty:
                row = comments_df.iloc[0]
                stars = "★" * int(row['rating']) + "☆" * (5 - int(row['rating']))
                st.markdown(f"""
                <div class="review-box">
                    <div>
                        <strong>{row['nickname']}</strong>
                        &nbsp;<span style="background:#F0F0F0; padding:1px 7px;
                        border-radius:10px; font-size:11px">{row.get('purpose','')}</span>
                        &nbsp;<span style="color:#F4A444">{stars}</span>
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
            # [C担当] レビュー投稿ダイアログの呼び出しを実装する
            #============================================================



            if st.button(
                "＋ レビューを書く" if not comments_df.empty else "＋ 最初のレビューを書く",
                key=f"review_btn_{shop['id']}",
                use_container_width=True
            ):
                st.session_state['review_target'] = int(shop['id'])