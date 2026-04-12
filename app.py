# ============================================
# 【1】ライブラリの読み込み
# ここでは、アプリに必要なライブラリを読み込みます。
# - io: アップロードファイルの再読み込み用
# - numpy: 欠損値(np.nan)などに使用
# - pandas: 表データの処理
# - streamlit: アプリ表示
# ============================================
import io
from typing import Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ============================================
# 【2】画面全体の基本設定
# Streamlitアプリのタイトルとレイアウトを設定します。
# ============================================
st.set_page_config(page_title="競馬 指数・期待値アプリ", layout="wide")


# ============================================
# 【3】必要な列名・任意列名・表示名の定義
# ============================================
REQUIRED_COLUMNS = [
    "horse_number", 
    "horse_name",
    "win_odds",
    "place_odds",
    "score_performance",
    "score_bias",
    "score_pace",
    "score_fit",
]

OPTIONAL_COLUMNS = ["memo"]

DISPLAY_NAME_MAP = {
    "horse_number": "馬番",
    "horse_name": "馬名",
    "win_odds": "単勝オッズ",
    "place_odds": "複勝オッズ",
    "score_performance": "競争成績",
    "score_bias": "トラックバイアス",
    "score_pace": "ペース恩恵",
    "score_fit": "適性",
    "memo": "メモ",
    "contrib_performance": "成績寄与",
    "contrib_bias": "バイアス寄与",
    "contrib_pace": "ペース寄与",
    "contrib_fit": "適性寄与",
    "total_index": "総合指数",
    "win_prob": "単勝率",
    "place_prob": "複勝率",
    "ev_win": "単勝期待値",
    "ev_place": "複勝期待値",
    "judge_win": "単勝判定",
    "judge_place": "複勝判定",
    "race_std": "指数標準偏差",
    "gap_1_2": "1位-2位差",
    "gap_1_3": "1位-3位差",
    "gap_3_4": "3位-4位差",
    "race_type": "レース分類",
    "kensen_level": "混戦度",
}


# ============================================
# 【4】表示名に変換する関数
# ============================================
def rename_for_display(df: pd.DataFrame) -> pd.DataFrame:
    rename_dict = {k: v for k, v in DISPLAY_NAME_MAP.items() if k in df.columns}
    return df.rename(columns=rename_dict)


# ============================================
# 【5】テンプレートデータを作る関数
# ============================================
def make_template_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "horse_name": "サンプルホースA",
                "win_odds": 3.8,
                "place_odds": 1.8,
                "score_performance": 8.5,
                "score_bias": 6.0,
                "score_pace": 7.0,
                "score_fit": 7.5,
                "memo": "",
            },
            {
                "horse_name": "サンプルホースB",
                "win_odds": 6.2,
                "place_odds": 2.4,
                "score_performance": 7.5,
                "score_bias": 7.5,
                "score_pace": 6.0,
                "score_fit": 6.5,
                "memo": "",
            },
            {
                "horse_name": "サンプルホースC",
                "win_odds": 10.5,
                "place_odds": 3.5,
                "score_performance": 6.0,
                "score_bias": 5.0,
                "score_pace": 8.0,
                "score_fit": 5.5,
                "memo": "",
            },
        ]
    )


# ============================================
# 【6】CSVダウンロード用のバイト列に変換する関数
# ============================================
def to_csv_download_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


# ============================================
# 【7】アップロードファイルを読み込む関数
# ============================================
def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        file_bytes = uploaded_file.read()
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(file_bytes), encoding="cp932")

    if file_name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)

    raise ValueError("対応ファイル形式は .csv または .xlsx のみです。")


# ============================================
# 【8】必要な列をそろえる関数
# ============================================
def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df["horse_name"] = df["horse_name"].fillna("").astype(str)
    df["memo"] = df["memo"].fillna("").astype(str)

    return df[REQUIRED_COLUMNS + OPTIONAL_COLUMNS]


# ============================================
# 【9】入力チェック関数
# ============================================
def validate_input(df: pd.DataFrame) -> Tuple[bool, list[str]]:
    errors = []
    work = df.copy()

    work["horse_name"] = work["horse_name"].fillna("").astype(str).str.strip()
    work["memo"] = work["memo"].fillna("").astype(str)

    if work["horse_name"].eq("").any():
        errors.append("馬名が空欄の行があります。")

    numeric_cols = [
        "win_odds",
        "place_odds",
        "score_performance",
        "score_bias",
        "score_pace",
        "score_fit",
    ]

    for col in numeric_cols:
        work[col] = pd.to_numeric(work[col], errors="coerce")
        if work[col].isna().any():
            errors.append(f"{DISPLAY_NAME_MAP[col]} に数値でない値または空欄があります。")

    if (pd.to_numeric(work["win_odds"], errors="coerce") <= 0).any():
        errors.append("単勝オッズは 0 より大きい値を入力してください。")

    if (pd.to_numeric(work["place_odds"], errors="coerce") <= 0).any():
        errors.append("複勝オッズは 0 より大きい値を入力してください。")

    score_cols = ["score_performance", "score_bias", "score_pace", "score_fit"]
    for col in score_cols:
        s = pd.to_numeric(work[col], errors="coerce")
        if ((s < 0) | (s > 10)).any():
            errors.append(f"{DISPLAY_NAME_MAP[col]} は 0〜10 の範囲で入力してください。")

    if len(work) < 2:
        errors.append("最低2頭以上入力してください。")

    return len(errors) == 0, errors


# ============================================
# 【10】期待値に応じた判定文言を返す関数
# ============================================
def judge_ev(ev: float, threshold: float) -> str:
    if ev >= 1.50:
        return "強く買い"
    if ev >= threshold:
        return "買い"
    return "見送り"


# ============================================
# 【11】頭数に応じた複勝率補正係数を返す関数
# ============================================
def calc_place_multiplier(num_horses: int) -> float:
    if num_horses <= 7:
        return 1.6
    if num_horses <= 11:
        return 2.2
    return 2.8


# ============================================
# 【12】指数・勝率・期待値を計算する関数
# ここを k + epsilon 方式にしています。
#
# 1. 指数でメイン確率を作る
# 2. 全馬均等の「紛れ確率」を作る
# 3. その2つを epsilon で混ぜる
# ============================================
def calculate_scores(
    df: pd.DataFrame,
    weight_performance: float,
    weight_bias: float,
    weight_pace: float,
    weight_fit: float,
    beta: float,
    epsilon: float,
    ev_threshold: float,
) -> pd.DataFrame:
    result = df.copy()

    result["horse_name"] = result["horse_name"].fillna("").astype(str)
    result["memo"] = result["memo"].fillna("").astype(str)

    numeric_cols = [
        "win_odds",
        "place_odds",
        "score_performance",
        "score_bias",
        "score_pace",
        "score_fit",
    ]
    for col in numeric_cols:
        result[col] = pd.to_numeric(result[col], errors="coerce")

    # 各項目の寄与度
    result["contrib_performance"] = result["score_performance"] * weight_performance
    result["contrib_bias"] = result["score_bias"] * weight_bias
    result["contrib_pace"] = result["score_pace"] * weight_pace
    result["contrib_fit"] = result["score_fit"] * weight_fit

    # 総合指数
    result["total_index"] = (
        result["contrib_performance"]
        + result["contrib_bias"]
        + result["contrib_pace"]
        + result["contrib_fit"]
    )

    # --------------------------------------------
    # メイン確率（能力）
    # 指数をレース内で標準化してから softmax
    # beta を大きくすると上位馬に勝率が寄る
    # --------------------------------------------
    mean_index = result["total_index"].mean()
    std_index = result["total_index"].std(ddof=0)

    # std=0 のときのエラー回避
    if std_index < 1e-8:
        z_score = np.zeros(len(result))
    else:
        z_score = (result["total_index"] - mean_index) / std_index

    exp_score = np.exp(beta * z_score)
    prob_main = exp_score / exp_score.sum()

    # --------------------------------------------
    # 紛れ確率（全馬均等）
    # epsilon を大きくすると、下位馬にも少し勝率が残る
    # --------------------------------------------
    prob_noise = np.ones(len(result)) / len(result)

    # --------------------------------------------
    # 合成確率
    # epsilon = 0 なら完全能力重視
    # epsilon > 0 なら紛れを加味
    # --------------------------------------------
    result["win_prob"] = (1 - epsilon) * prob_main + epsilon * prob_noise
   
    # 複勝率
    multiplier = calc_place_multiplier(len(result))
    result["place_prob"] = (result["win_prob"] * multiplier).clip(upper=0.95)

    # 期待値
    result["ev_win"] = result["win_prob"] * result["win_odds"]
    result["ev_place"] = result["place_prob"] * result["place_odds"]

    # 判定
    result["judge_win"] = result["ev_win"].apply(lambda x: judge_ev(x, ev_threshold))
    result["judge_place"] = result["ev_place"].apply(lambda x: judge_ev(x, ev_threshold))

    # パーセント表示用
    result["win_prob"] = result["win_prob"] * 100
    result["place_prob"] = result["place_prob"] * 100

    # =========================
    # 混戦度計算
    # =========================
    sorted_idx = result["total_index"].sort_values(ascending=False).reset_index(drop=True)

    race_std = float(sorted_idx.std(ddof=0))
    gap_1_2 = float(sorted_idx.iloc[0] - sorted_idx.iloc[1]) if len(sorted_idx) >= 2 else 0.0
    gap_1_3 = float(sorted_idx.iloc[0] - sorted_idx.iloc[2]) if len(sorted_idx) >= 3 else 0.0
    gap_3_4 = float(sorted_idx.iloc[2] - sorted_idx.iloc[3]) if len(sorted_idx) >= 4 else 0.0

    STD_CLOSE = 0.35
    GAP12_STRONG = 0.25
    GAP13_CLOSE = 0.30
    GAP34_SEPARATE = 0.20

    if gap_1_3 < GAP13_CLOSE and gap_3_4 >= GAP34_SEPARATE:
        race_type = "上位集中"
        kensen_level = "中"
    elif race_std < STD_CLOSE and gap_3_4 < GAP34_SEPARATE:
        race_type = "全体混戦"
        kensen_level = "高"
    elif gap_1_2 >= GAP12_STRONG:
        race_type = "単勝向き"
        kensen_level = "低"
    else:
        race_type = "中間型"
        kensen_level = "中"

    result["race_std"] = race_std
    result["gap_1_2"] = gap_1_2
    result["gap_1_3"] = gap_1_3
    result["gap_3_4"] = gap_3_4
    result["race_type"] = race_type
    result["kensen_level"] = kensen_level

    # 並び順は指数順
    result = result.sort_values(by="total_index", ascending=False).reset_index(drop=True)

    return result


# ============================================
# 【13】アプリタイトル・説明文
# ============================================
st.title("競馬 指数・期待値アプリ")
st.caption("Excel/CSVを読み込み、アプリ上で修正しながら単勝・複勝の期待値を計算します。")


# ============================================
# 【14】サイドバー設定
# - 重み
# - k
# - epsilon
# - 閾値
# ============================================
with st.sidebar:
    st.header("設定")

    st.subheader("重み")
    weight_performance = st.number_input("競争成績", min_value=0.0, max_value=1.0, value=0.60, step=0.01)
    weight_bias = st.number_input("トラックバイアス", min_value=0.0, max_value=1.0, value=0.15, step=0.01)
    weight_pace = st.number_input("ペース恩恵", min_value=0.0, max_value=1.0, value=0.15, step=0.01)
    weight_fit = st.number_input("適性", min_value=0.0, max_value=1.0, value=0.10, step=0.01)

    weight_sum = weight_performance + weight_bias + weight_pace + weight_fit
    st.write(f"重み合計: **{weight_sum:.2f}**")
    if abs(weight_sum - 1.0) > 1e-9:
        st.warning("重み合計が1.00ではありません。現在の値のまま計算はできますが、1.00推奨です。")

    st.subheader("勝率変換")
    beta = st.number_input(
        "beta（標準化指数差をどれだけ強調するか）",
        min_value=0.1,
        max_value=5.0,
        value=1.5,
        step=0.1,
    )
    st.caption("beta を大きくすると、上位馬に勝率が寄りやすくなります。")
    epsilon = st.number_input(
        "epsilon（紛れをどれだけ入れるか）",
        min_value=0.0,
        max_value=0.5,
        value=0.15,
        step=0.01,
    )
    st.caption("epsilon を大きくすると、下位馬にも少し勝率が残りやすくなります。")

    st.subheader("期待値設定")
    ev_threshold = st.number_input("購入閾値", min_value=0.5, max_value=5.0, value=1.35, step=0.01)

    st.markdown("---")
    st.subheader("テンプレート")
    template_df = make_template_df()
    st.download_button(
        "入力テンプレートCSVをダウンロード",
        data=to_csv_download_bytes(template_df),
        file_name="keiba_template.csv",
        mime="text/csv",
    )


# ============================================
# 【15】ファイルアップロード部分
# ============================================
uploaded_file = st.file_uploader("Excel または CSV をアップロード", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        raw_df = read_uploaded_file(uploaded_file)
        input_df = ensure_columns(raw_df)
        st.success("ファイルを読み込みました。必要に応じて表を修正してください。")
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {e}")
        st.stop()
else:
    st.info("ファイルが未アップロードのため、サンプルデータを表示しています。")
    input_df = make_template_df()


# ============================================
# 【16】data_editor に渡す前の型固定
# ============================================
input_df["horse_name"] = input_df["horse_name"].fillna("").astype(str)
input_df["memo"] = input_df["memo"].fillna("").astype(str)


# ============================================
# 【17】入力テーブル表示
# ============================================
st.subheader("入力データ")

edited_df = st.data_editor(
    input_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "horse_number": st.column_config.NumberColumn("馬番", min_value=1, step=1),
        "horse_name": st.column_config.TextColumn("馬名", required=True),
        "win_odds": st.column_config.NumberColumn("単勝オッズ", min_value=0.01, step=0.1),
        "place_odds": st.column_config.NumberColumn("複勝オッズ", min_value=0.01, step=0.1),
        "score_performance": st.column_config.NumberColumn("競争成績", min_value=0.0, max_value=10.0, step=0.1),
        "score_bias": st.column_config.NumberColumn("トラックバイアス", min_value=0.0, max_value=10.0, step=0.1),
        "score_pace": st.column_config.NumberColumn("ペース恩恵", min_value=0.0, max_value=10.0, step=0.1),
        "score_fit": st.column_config.NumberColumn("適性", min_value=0.0, max_value=10.0, step=0.1),
        "memo": st.column_config.TextColumn("メモ"),
    },
)


# ============================================
# 【18】編集後の型固定
# ============================================
edited_df["horse_name"] = edited_df["horse_name"].fillna("").astype(str)
edited_df["memo"] = edited_df["memo"].fillna("").astype(str)


# ============================================
# 【19】入力チェック実行
# ============================================
is_valid, error_messages = validate_input(edited_df)

if not is_valid:
    st.error("入力内容に問題があります。以下を修正してください。")
    for msg in error_messages:
        st.write(f"- {msg}")
    st.stop()


# ============================================
# 【20】指数・勝率・期待値の計算実行
# ============================================
result_df = calculate_scores(
    edited_df,
    weight_performance=weight_performance,
    weight_bias=weight_bias,
    weight_pace=weight_pace,
    weight_fit=weight_fit,
    beta=beta,
    epsilon=epsilon,
    ev_threshold=ev_threshold,
)

# レース診断UI
st.subheader("レース診断")

st.write(f"混戦度: {result_df['kensen_level'].iloc[0]}")
st.write(f"レース分類: {result_df['race_type'].iloc[0]}")
st.write(f"指数標準偏差: {result_df['race_std'].iloc[0]:.2f}")
st.write(f"1位-2位差: {result_df['gap_1_2'].iloc[0]:.2f}")
st.write(f"1位-3位差: {result_df['gap_1_3'].iloc[0]:.2f}")
st.write(f"3位-4位差: {result_df['gap_3_4'].iloc[0]:.2f}")

# ============================================
# 【21】注目馬カード表示
# ============================================
st.markdown("## 🏆 注目馬（指数順）")

top_df = result_df.sort_values("total_index", ascending=False).head(5)

for _, row in top_df.iterrows():
    ev = row["ev_win"]

    if ev >= 1.50:
        badge = "🔥 強く買い"
        border_color = "#16a34a"
        bg_color = "#f0fdf4"
    elif ev >= ev_threshold:
        badge = "👍 買い"
        border_color = "#22c55e"
        bg_color = "#f7fee7"
    else:
        badge = "❌ 見送り"
        border_color = "#ef4444"
        bg_color = "#fef2f2"

    card_html = f"""
<div style="background:{bg_color}; border-left:8px solid {border_color}; border-radius:14px; padding:18px 20px; margin-bottom:14px; box-shadow:0 2px 10px rgba(0,0,0,0.08);">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
    <div style="font-size:30px; font-weight:800; color:#111827;">
      {int(row['horse_number'])}番 {row['horse_name']}
    </div>
    <div style="font-size:18px; font-weight:700; color:{border_color};">
      {badge}
    </div>
  </div>
  <div style="margin-top:12px; display:flex; gap:28px; flex-wrap:wrap;">
    <div style="font-size:16px; color:#374151;">総合指数: <span style="font-weight:700; color:#111827;">{row['total_index']:.2f}</span></div>
    <div style="font-size:16px; color:#374151;">単勝率: <span style="font-weight:700; color:#111827;">{row['win_prob']:.1f}%</span></div>
    <div style="font-size:20px; color:#111827;">単勝期待値: <span style="font-weight:800;">{row['ev_win']:.2f}</span></div>
  </div>
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)


# ============================================
# 【22】計算結果テーブル表示
# 勝率合計も確認できるようにしています。
# ============================================
st.subheader("計算結果")

st.info(f"単勝率合計: {result_df['win_prob'].sum():.1f}%")

display_cols = [
    "horse_number",
    "horse_name",
    "contrib_performance",
    "contrib_bias",
    "contrib_pace",
    "contrib_fit",
    "total_index",
    "win_prob",
    "place_prob",
    "ev_win",
    "ev_place",
    "judge_win",
    "judge_place",
    "memo",
    "race_std",
    "gap_1_2",
    "gap_1_3",
    "gap_3_4",
    "race_type",
    "kensen_level",
]

display_df = result_df[display_cols].copy()
display_df = rename_for_display(display_df)

st.dataframe(
    display_df.style.format(
        {
            "成績寄与": "{:.2f}",
            "バイアス寄与": "{:.2f}",
            "ペース寄与": "{:.2f}",
            "適性寄与": "{:.2f}",
            "総合指数": "{:.2f}",
            "単勝率": "{:.1f}%",
            "複勝率": "{:.1f}%",
            "単勝期待値": "{:.2f}",
            "複勝期待値": "{:.2f}",
        }
    ),
    use_container_width=True,
)


# ============================================
# 【23】買い候補一覧
# ============================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("単勝 買い候補")
    buy_win_df = result_df[result_df["ev_win"] >= ev_threshold][
        ["horse_number", "horse_name", "total_index", "win_prob", "ev_win", "judge_win"]
    ].copy()
    buy_win_df = rename_for_display(buy_win_df)

    if len(buy_win_df) == 0:
        st.write("該当なし")
    else:
        st.dataframe(
            buy_win_df.style.format(
                {
                    "総合指数": "{:.2f}",
                    "単勝率": "{:.1f}%",
                    "単勝期待値": "{:.2f}",
                }
            ),
            use_container_width=True,
        )

with col2:
    st.subheader("複勝 買い候補")
    buy_place_df = result_df[result_df["ev_place"] >= ev_threshold][
        ["horse_name", "total_index", "place_prob", "ev_place", "judge_place"]
    ].copy()
    buy_place_df = rename_for_display(buy_place_df)

    if len(buy_place_df) == 0:
        st.write("該当なし")
    else:
        st.dataframe(
            buy_place_df.style.format(
                {
                    "総合指数": "{:.2f}",
                    "複勝率": "{:.1f}%",
                    "複勝期待値": "{:.2f}",
                }
            ),
            use_container_width=True,
        )


# ============================================
# 【24】計算結果CSVダウンロード
# ============================================
st.subheader("ダウンロード")

download_cols = [
    "horse_number",
    "horse_name",
    "win_odds",
    "place_odds",
    "score_performance",
    "score_bias",
    "score_pace",
    "score_fit",
    "memo",
    "contrib_performance",
    "contrib_bias",
    "contrib_pace",
    "contrib_fit",
    "total_index",
    "win_prob",
    "place_prob",
    "ev_win",
    "ev_place",
    "judge_win",
    "judge_place",
]

download_df = result_df[download_cols].copy()
csv_bytes = to_csv_download_bytes(download_df)

# アップロードファイル名を取得（拡張子除く）
if uploaded_file is not None:
    base_name = uploaded_file.name.rsplit(".", 1)[0]
else:
    base_name = "keiba"

# beta / epsilon をファイル名に追加（小数点は見やすく整形）
file_name = f"{base_name}_b{beta:.2f}_e{epsilon:.2f}_result.csv"

st.download_button(
    "計算結果CSVをダウンロード",
    data=csv_bytes,
    file_name=file_name,
    mime="text/csv",
)


# ============================================
# 【25】補足説明
# ============================================
st.markdown("---")
st.caption("※ 複勝率は簡易補正式で算出しています。将来的にバックテストや統計解析で改善する前提です。")
st.caption("※ 勝率は現在、指数を k 乗して作るメイン確率と、全馬均等の紛れ確率を epsilon で混ぜる簡易ロジックです。")


# ============================================
# 【26】beta と epsilon を探すための補助UI
# - 上位5頭の勝率配分を見やすく表示
# - 今の設定がどんな性格かを表示
# ============================================
st.markdown("## 🎛️ beta と epsilon の調整チェック")

if beta < 1.0:
    beta_comment = "beta は低めです。勝率はかなりなだらかになります。"
elif beta < 2.0:
    beta_comment = "beta は中くらいです。上位馬を適度に評価します。"
else:
    beta_comment = "beta は高めです。上位馬にかなり勝率が寄ります。"

if epsilon < 0.08:
    e_comment = "epsilon は低めです。かなり能力重視です。"
elif epsilon < 0.18:
    e_comment = "epsilon は中くらいです。少し紛れを考慮しています。"
else:
    e_comment = "epsilon は高めです。展開や紛れを強めに見ています。"

st.write(f"- {beta_comment}")
st.write(f"- {e_comment}")

top_prob_df = result_df[["horse_name", "total_index", "win_prob", "ev_win"]].head(5).copy()
top_prob_df = top_prob_df.rename(
    columns={
        "horse_name": "馬名",
        "total_index": "総合指数",
        "win_prob": "単勝率",
        "ev_win": "単勝期待値",
    }
)

st.dataframe(
    top_prob_df.style.format(
        {
            "総合指数": "{:.2f}",
            "単勝率": "{:.1f}%",
            "単勝期待値": "{:.2f}",
        }
    ),
    use_container_width=True,
)