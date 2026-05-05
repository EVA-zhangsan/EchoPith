from __future__ import annotations

import colorsys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from snownlp import SnowNLP


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_XLSX = BASE_DIR / "data" / "xhs" / "excel" / "xhs_cleaned_2026-03-11.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "xhs" / "analysis"
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def get_font_name() -> str:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            if candidate.name.lower().startswith("msyh"):
                return "Microsoft YaHei"
            if candidate.name.lower().startswith("simhei"):
                return "SimHei"
            if candidate.name.lower().startswith("simsun"):
                return "SimSun"
    return "Microsoft YaHei"


def classify_sentiment(score: float) -> str:
    if score > 0.6:
        return "正面情绪"
    if score < 0.4:
        return "负面情绪"
    return "中性情绪"


def darken_color(color: str, factor: float = 0.72) -> tuple[float, float, float]:
    color_rgb = plt.matplotlib.colors.to_rgb(color)
    hue, lightness, saturation = colorsys.rgb_to_hls(*color_rgb)
    lightness = max(0, min(1, lightness * factor))
    return colorsys.hls_to_rgb(hue, lightness, saturation)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    plt.rcParams["font.sans-serif"] = [get_font_name(), "SimHei", "SimSun"]
    plt.rcParams["axes.unicode_minus"] = False

    comments_df = pd.read_excel(INPUT_XLSX, sheet_name="comments_clean")
    comments_df = comments_df.dropna(subset=["content"])
    comments_df["content"] = comments_df["content"].astype(str).str.strip()
    comments_df = comments_df[comments_df["content"].str.len() > 0].copy()

    comments_df["sentiment_score"] = comments_df["content"].map(lambda text: SnowNLP(text).sentiments)
    comments_df["sentiment_label"] = comments_df["sentiment_score"].map(classify_sentiment)

    label_order = ["正面情绪", "中性情绪", "负面情绪"]
    score_ranges = {
        "正面情绪": "0.60 - 1.00",
        "中性情绪": "0.40 - 0.60",
        "负面情绪": "0.00 - 0.40",
    }
    counts = comments_df["sentiment_label"].value_counts().reindex(label_order, fill_value=0)
    percentages = counts / counts.sum() * 100
    avg_scores = comments_df.groupby("sentiment_label")["sentiment_score"].mean().reindex(label_order).fillna(0)
    dominant_label = counts.idxmax()

    colors = ["#F7D794", "#D6EAF8", "#FAD7C3"]
    side_colors = [darken_color(color, 0.58) for color in colors]
    explode = [0.06, 0.03, 0.08]

    fig, ax = plt.subplots(figsize=(12, 9), facecolor="none")
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    for depth in range(5, 0, -1):
        ax.pie(
            counts,
            radius=1,
            center=(0, -depth * 0.045),
            startangle=105,
            colors=side_colors,
            explode=explode,
            wedgeprops={"linewidth": 0, "edgecolor": "none"},
        )

    wedges, texts, autotexts = ax.pie(
        counts,
        labels=[f"{label}\n{counts[label]} 条" for label in label_order],
        autopct="%1.1f%%",
        pctdistance=0.72,
        labeldistance=1.08,
        startangle=105,
        colors=colors,
        explode=explode,
        shadow=True,
        wedgeprops={"linewidth": 1.2, "edgecolor": "#FFFDF7"},
        textprops={"fontsize": 18, "fontweight": "bold", "color": "#4A403A"},
    )

    for autotext in autotexts:
        autotext.set_color("#FFFFFF")
        autotext.set_fontsize(20)
        autotext.set_fontweight("bold")

    ax.text(
        0,
        0,
        f"总评论\n{len(comments_df)} 条\n均分 {comments_df['sentiment_score'].mean():.3f}",
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color="#5C4B3C",
        bbox={"boxstyle": "round,pad=0.8", "facecolor": "#FFF7D6", "edgecolor": "#E7C97A", "alpha": 0.92},
    )

    ax.text(
        0.5,
        1.01,
        "分层伪 3D 饼图 | 外圈展示数量 | 右侧补充统计摘要",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=14,
        color="#8D8176",
    )

    ax.text(
        1.09,
        0.82,
        "情感分类统计",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=18,
        fontweight="bold",
        color="#6B4F1D",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#FFF3CD", "edgecolor": "#F4C95D", "alpha": 0.95},
    )
    ax.text(
        1.09,
        0.74,
        f"主导情绪：{dominant_label}",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=13,
        color="#7A5C2E",
    )

    row_positions = [0.62, 0.44, 0.26]
    for index, label in enumerate(label_order):
        y_pos = row_positions[index]
        ax.scatter(
            [1.11],
            [y_pos + 0.035],
            transform=ax.transAxes,
            s=220,
            color=colors[index],
            edgecolors=side_colors[index],
            linewidths=1.5,
            clip_on=False,
            zorder=6,
        )
        ax.text(
            1.17,
            y_pos + 0.055,
            label,
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=16,
            fontweight="bold",
            color="#4F463E",
        )
        ax.text(
            1.17,
            y_pos + 0.005,
            f"占比 {percentages[label]:.2f}%   样本 {counts[label]}   均分 {avg_scores[label]:.3f}",
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=13.5,
            color="#655B52",
        )
        ax.text(
            1.17,
            y_pos - 0.045,
            f"情感区间 {score_ranges[label]}",
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=12.5,
            color="#8A7F73",
        )
        ax.plot(
            [1.11, 1.48],
            [y_pos - 0.085, y_pos - 0.085],
            transform=ax.transAxes,
            color="#E7D8C8",
            linewidth=1.0,
            clip_on=False,
        )
    ax.set_aspect("equal")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "sentiment_pie.png", dpi=300, bbox_inches="tight", transparent=True)
    plt.close(fig)

    negative_samples = comments_df[
        (comments_df["sentiment_score"] < 0.4) & (comments_df["content"].str.len() > 10)
    ].sort_values(by=["sentiment_score", "content"], ascending=[True, True]).head(5)

    comments_df[["content", "sentiment_score", "sentiment_label"]].to_csv(
        OUTPUT_DIR / "sentiment_pie_scores.csv", index=False, encoding="utf-8-sig"
    )

    print("SENTIMENT_PERCENTAGES")
    for label in label_order:
        print(f"{label}={counts[label]} ({percentages[label]:.2f}%)")

    print("NEGATIVE_SAMPLES")
    for index, row in enumerate(negative_samples.itertuples(index=False), start=1):
        print(f"{index}. [{row.sentiment_score:.4f}] {row.content}")


if __name__ == "__main__":
    main()