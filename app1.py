import io
from typing import Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="競馬期待値アプリ", layout="wide")

# =========================
# 定数
# =========================
DEFAULT_WEIGHTS = {
    "score_performance": 0.60,
    "score_bias": 0.15,
    "score_pace": 0.15,
    "score_fit": 0.10,
}

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


# =========================
# 補助関数
# =========================
def rename_for_display(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={k: v for k, v in DISPLAY_NAME_MAP.items() if k in df.columns})


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


def to_csv_download_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        file_bytes = uploaded_file.read()  # ← これが重要

        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
        except:
            return pd.read_csv(io.BytesIO(file_bytes), encoding="cp932")

    if file_name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)

    raise ValueError("対応ファイル形式は .csv または .xlsx のみです。")

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan

    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[REQUIRED_COLUMNS + OPTIONAL_COLUMNS]


def validate_input(df: pd.DataFrame) -> Tuple[bool, list[str]]:
    errors = []
    work = df.copy()

    # 文字列整形
    work["horse_name"] = work["horse_name"].astype(str).str.strip()

    # 必須チェック
    if work["horse_name"].replace("nan", "").eq("").any():
        errors.append("馬名が空欄の行があります。")

    # 数値変換
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

    # オッズ > 0
    if "win_odds" in work.columns and (pd.to_numeric(work["win_odds"], errors="coerce") <= 0).any():
        errors.append("単勝オッズは 0 より大きい値を入力してください。")
    if "place_odds" in work.columns and (pd.to_numeric(work["place_odds"], errors="coerce") <= 0).any():
        errors.append("複勝オッズは 0 より大きい値を入力してください。")

    # スコア 0〜10
    score_cols = ["score_performance", "score_bias", "score_pace", "score_fit"]
    for col in score_cols:
        s = pd.to_numeric(work[col], errors="coerce")
        if ((s < 0) | (s > 10)).any():
            errors.append(f"{DISPLAY_NAME_MAP[col]} は 0〜10 の範囲で入力してください。")

    # 馬数
    if len(work) < 2:
        errors.append("最低2頭以上入力してください。")

    return len(errors) == 0, errors


def judge_ev(ev: float, threshold: float) -> str:
    if ev >= 1.50:
        return "強く買い"
    if ev >= threshold:
        return "買い"
    return "見送り"


def calc_place_multiplier(num_horses: int) -> float:
    """
    仮の複勝率補正式。
    将来的に要調整。
    """
    if num_horses <= 7:
        return 1.6
    if num_horses <= 11:
        return 2.2
    return 2.8


def calculate_scores(
    df: pd.DataFrame,
    weight_performance: float,
    weight_bias: float,
    weight_pace: float,
    weight_fit: float,
    alpha: float,
    ev_threshold: float,
) -> pd.DataFrame:
    result = df.copy()

    # 数値化
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

    # 寄与度
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

    # 単勝率
    min_index = result["total_index"].min()
    result["adjusted_score"] = (result["total_index"] - min_index) + alpha

    total_adjusted = result["adjusted_score"].sum()
    if total_adjusted <= 0:
        result["win_prob"] = 1.0 / len(result)
    else:
        result["win_prob"] = result["adjusted_score"] / total_adjusted

    # 複勝率
    multiplier = calc_place_multiplier(len(result))
    result["place_prob"] = (result["win_prob"] * multiplier).clip(upper=0.95)

    # 期待値
    result["ev_win"] = result["win_prob"] * result["win_odds"]
    result["ev_place"] = result["place_prob"] * result["place_odds"]

    # 判定
    result["judge_win"] = result["ev_win"].apply(lambda x: judge_ev(x, ev_threshold))
    result["judge_place"] = result["ev_place"].apply(lambda x: judge_ev(x, ev_threshold))

    # 表示用パーセント
    result["win_prob"] = result["win_prob"] * 100
    result["place_prob"] = result["place_prob"] * 100

    # 並び
    result = result.sort_values(by="ev_win", ascending=False).reset_index(drop=True)

    return result


# =========================
# UI
# =========================
st.title("競馬 指数・期待値アプリ")
st.caption("Excel/CSVを読み込み、アプリ上で修正しながら単勝・複勝の期待値を計算します。")

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

    st.subheader("計算パラメータ")
    alpha = st.number_input("α（最低評価馬の下駄）", min_value=0.01, max_value=5.0, value=0.5, step=0.01)
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

st.subheader("入力データ")

edited_df = st.data_editor(
    input_df,
    num_rows="dynamic",
    use_container_width=True,
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
    hide_index=True,
)

is_valid, error_messages = validate_input(edited_df)

if not is_valid:
    st.error("入力内容に問題があります。以下を修正してください。")
    for msg in error_messages:
        st.write(f"- {msg}")
    st.stop()

result_df = calculate_scores(
    edited_df,
    weight_performance=weight_performance,
    weight_bias=weight_bias,
    weight_pace=weight_pace,
    weight_fit=weight_fit,
    alpha=alpha,
    ev_threshold=ev_threshold,
)

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

st.markdown("---")
st.caption(
    "※ 複勝率は簡易補正式で算出しています。将来的にバックテストや統計解析で改善する前提です。"
)

st.markdown("## 🏆 注目馬（単勝EV順）")

top_df = result_df.sort_values("ev_win", ascending=False).head(5)

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
<div style="background:{bg_color}; border-left:8px solid {border_color}; border-radius:12px; padding:16px 18px; margin-bottom:12px; box-shadow:0 2px 8px rgba(0,0,0,0.08);">
  <div style="font-size:28px; font-weight:700; color:#111827; margin-bottom:10px;">
    {row['horse_name']}
  </div>
  <div style="display:flex; gap:24px; flex-wrap:wrap; margin-bottom:8px;">
    <div style="font-size:16px; color:#374151;">
      総合指数: <span style="font-weight:700;">{row['total_index']:.2f}</span>
    </div>
    <div style="font-size:16px; color:#374151;">
      単勝率: <span style="font-weight:700;">{row['win_prob']:.1f}%</span>
    </div>
  </div>
  <div style="font-size:22px; font-weight:800; color:#111827; margin-bottom:6px;">
    単勝期待値: {row['ev_win']:.2f}
  </div>
  <div style="font-size:18px; font-weight:700; color:{border_color};">
    {badge}
  </div>
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)