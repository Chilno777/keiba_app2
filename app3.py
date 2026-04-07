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
# - REQUIRED_COLUMNS: 入力に必須な列
# - OPTIONAL_COLUMNS: 任意列
# - DISPLAY_NAME_MAP: 画面で日本語表示するための対応表
# ============================================
REQUIRED_COLUMNS = [
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
}


# ============================================
# 【4】表示名に変換する関数
# DataFrameの英語列名を、画面表示用の日本語列名に変換します。
# ============================================
def rename_for_display(df: pd.DataFrame) -> pd.DataFrame:
    rename_dict = {k: v for k, v in DISPLAY_NAME_MAP.items() if k in df.columns}
    return df.rename(columns=rename_dict)


# ============================================
# 【5】テンプレートデータを作る関数
# ファイル未アップロード時に表示するサンプルデータです。
# テンプレートCSVのダウンロードにも使います。
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
# 結果をCSVとしてダウンロードできるようにします。
# utf-8-sig にしてExcelでも文字化けしにくくします。
# ============================================
def to_csv_download_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


# ============================================
# 【7】アップロードファイルを読み込む関数
# - CSV: UTF-8で読んで失敗したらCP932で再読み込み
# - Excel: そのまま読み込み
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
# アップロードファイルに足りない列があれば追加し、
# horse_name と memo の型を文字列に固定します。
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
# - 馬名の空欄チェック
# - 数値列の型チェック
# - オッズが0以下でないか
# - スコアが0〜10に収まっているか
# - 最低2頭以上いるか
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
# - 1.50以上: 強く買い
# - 閾値以上: 買い
# - それ未満: 見送り
# ============================================
def judge_ev(ev: float, threshold: float) -> str:
    if ev >= 1.50:
        return "強く買い"
    if ev >= threshold:
        return "買い"
    return "見送り"


# ============================================
# 【11】頭数に応じた複勝率補正係数を返す関数
# 現状は簡易式です。将来的に改善対象です。
# ============================================
def calc_place_multiplier(num_horses: int) -> float:
    if num_horses <= 7:
        return 1.6
    if num_horses <= 11:
        return 2.2
    return 2.8


# ============================================
# 【12】指数・勝率・期待値を計算する関数
# このアプリの中核ロジックです。
#
# ここでやっていること
# 1. 入力値を数値化
# 2. 各項目の寄与度を計算
# 3. 総合指数を計算
# 4. 指数から勝率に変換
#    ※ここは「k乗方式」を採用
# 5. 複勝率を簡易計算
# 6. 単勝/複勝期待値を計算
# 7. 判定を付ける
# 8. 指数順に並べ替える
# ============================================
def calculate_scores(
    df: pd.DataFrame,
    weight_performance: float,
    weight_bias: float,
    weight_pace: float,
    weight_fit: float,
    prob_power_k: float,
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
    # 勝率変換（k乗方式）
    # total_index をそのまま確率化するのではなく、
    # k乗して上位と下位の差を広げます。
    # 例: k=2.0 なら、上位馬に勝率が寄りやすくなります。
    # --------------------------------------------
    base_score = result["total_index"].clip(lower=0.1)
    powered_score = base_score ** prob_power_k
    result["win_prob"] = powered_score / powered_score.sum()

    # 複勝率
    multiplier = calc_place_multiplier(len(result))
    result["place_prob"] = (result["win_prob"] * multiplier).clip(upper=0.95)

    # 期待値
    result["ev_win"] = result["win_prob"] * result["win_odds"]
    result["ev_place"] = result["place_prob"] * result["place_odds"]

    # 判定
    result["judge_win"] = result["ev_win"].apply(lambda x: judge_ev(x, ev_threshold))
    result["judge_place"] = result["ev_place"].apply(lambda x: judge_ev(x, ev_threshold))

    # パーセント表示用に100倍
    result["win_prob"] = result["win_prob"] * 100
    result["place_prob"] = result["place_prob"] * 100

    # --------------------------------------------
    # 並び順は「指数順」
    # ここを変えれば、表示順の軸を変えられます。
    # --------------------------------------------
    result = result.sort_values(by="total_index", ascending=False).reset_index(drop=True)

    return result


# ============================================
# 【13】アプリタイトル・説明文
# ============================================
st.title("競馬 指数・期待値アプリ")
st.caption("Excel/CSVを読み込み、アプリ上で修正しながら単勝・複勝の期待値を計算します。")


# ============================================
# 【14】サイドバー設定
# - 重みの入力
# - 勝率変換の強さ(k)
# - 購入閾値
# - テンプレートCSVダウンロード
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
    prob_power_k = st.number_input(
        "k（指数差をどれだけ強調するか）",
        min_value=0.5,
        max_value=5.0,
        value=2.0,
        step=0.1,
    )
    st.caption("k を大きくすると、上位馬に勝率が寄りやすくなります。")

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
# ファイルがあれば読み込み、なければサンプルデータを表示します。
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
# memo列の型エラー回避のため、文字列化しておきます。
# ============================================
input_df["horse_name"] = input_df["horse_name"].fillna("").astype(str)
input_df["memo"] = input_df["memo"].fillna("").astype(str)


# ============================================
# 【17】入力テーブル表示
# ここでアプリ上でデータを編集できます。
# ============================================
st.subheader("入力データ")

edited_df = st.data_editor(
    input_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
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
# 編集後も horse_name と memo を文字列に固定します。
# ============================================
edited_df["horse_name"] = edited_df["horse_name"].fillna("").astype(str)
edited_df["memo"] = edited_df["memo"].fillna("").astype(str)


# ============================================
# 【19】入力チェック実行
# 問題があればここで止めて、エラーメッセージを表示します。
# ============================================
is_valid, error_messages = validate_input(edited_df)

if not is_valid:
    st.error("入力内容に問題があります。以下を修正してください。")
    for msg in error_messages:
        st.write(f"- {msg}")
    st.stop()


# ============================================
# 【20】指数・勝率・期待値の計算実行
# calculate_scores を呼び出して結果を作ります。
# ============================================
result_df = calculate_scores(
    edited_df,
    weight_performance=weight_performance,
    weight_bias=weight_bias,
    weight_pace=weight_pace,
    weight_fit=weight_fit,
    prob_power_k=prob_power_k,
    ev_threshold=ev_threshold,
)


# ============================================
# 【21】注目馬カード表示
# ここでは「指数順」で上位5頭をカード表示しています。
# 以前は期待値順でしたが、今は指数順を主軸にしています。
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
      {row['horse_name']}
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
# 寄与度・指数・勝率・期待値・判定を一覧で見られます。
# ============================================
st.subheader("計算結果")

display_cols = [
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
# 左: 単勝の買い候補
# 右: 複勝の買い候補
# ここでは期待値閾値以上のものだけを表示します。
# ============================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("単勝 買い候補")
    buy_win_df = result_df[result_df["ev_win"] >= ev_threshold][
        ["horse_name", "total_index", "win_prob", "ev_win", "judge_win"]
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
# 計算後の全結果をCSVで保存できます。
# ============================================
st.subheader("ダウンロード")

download_cols = [
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

st.download_button(
    "計算結果CSVをダウンロード",
    data=csv_bytes,
    file_name="keiba_result.csv",
    mime="text/csv",
)


# ============================================
# 【25】補足説明
# 現状の簡易仕様についての注意書きです。
# ============================================
st.markdown("---")
st.caption("※ 複勝率は簡易補正式で算出しています。将来的にバックテストや統計解析で改善する前提です。")
st.caption("※ 勝率は現在、指数を k 乗して確率化する簡易ロジックです。今後、実績データに基づいて改善していく前提です。")