from __future__ import annotations

import itertools
import math
import re
from collections import Counter
from pathlib import Path

import jieba
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from snownlp import SnowNLP
from wordcloud import WordCloud


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_XLSX = BASE_DIR / "data" / "xhs" / "excel" / "xhs_cleaned_2026-03-11.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "xhs" / "analysis"
STOPWORDS_FILE = BASE_DIR / "docs" / "hit_stopwords.txt"
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]

TOP_N = 30
MIN_TOKEN_LEN = 2
TEXT_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")

BASE_STOPWORDS = {
    "我们", "你们", "他们", "自己", "就是", "一个", "一些", "这个", "那个", "真的", "感觉", "觉得",
    "可以", "还是", "已经", "没有", "不是", "什么", "怎么", "因为", "所以", "然后", "如果",
    "而且", "但是", "比较", "非常", "有点", "一下", "一下子", "其实", "现在", "时候", "这样",
    "那样", "这里", "那里", "里面", "外面", "出来", "进去", "看到", "知道", "希望", "喜欢",
    "评论", "姐妹", "哈哈", "啊啊", "太太", "呜呜", "真的好", "一下吧", "一下下", "一下哦",
    "女书", "江永女书", "小红书", "博主", "帖子", "内容", "感觉好", "很多", "这种", "那个", "这个",
    "老师", "请问", "谢谢", "有没有", "求", "蹲", "作者", "好看", "太", "好", "就", "也", "还",
    "你好", "大家", "意思", "好像", "之前", "今天", "时候", "确实", "发现", "东西", "啊", "了",
    "的", "我", "你", "他", "她", "一定", "特别", "可能", "应该", "去", "漂亮",
    "不能", "图片", "厉害", "快乐", "现在", "还是",
    "啊啊啊", "两个", "了解", "那种", "感谢", "不会", "姐姐", "这么", "这是", "一点",
    "一直", "起来", "不过",
}


def get_font_path() -> str:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError("No Chinese font file found in system fonts.")


def load_stopwords() -> set[str]:
    stopwords = set(BASE_STOPWORDS)
    if STOPWORDS_FILE.exists():
        stopwords.update(
            line.strip() for line in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    return stopwords


def normalize_text(text: object) -> str:
    if pd.isna(text):
        return ""
    normalized = str(text)
    normalized = TEXT_PATTERN.sub(" ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return normalized


def tokenize_comments(comments: list[str], stopwords: set[str]) -> tuple[list[list[str]], Counter]:
    tokenized_comments: list[list[str]] = []
    counter: Counter = Counter()

    for comment in comments:
        tokens: list[str] = []
        for token in jieba.lcut(comment):
            cleaned = token.strip().lower()
            if not cleaned:
                continue
            if cleaned in stopwords:
                continue
            if len(cleaned) < MIN_TOKEN_LEN:
                continue
            if cleaned.isdigit():
                continue
            tokens.append(cleaned)
        if tokens:
            tokenized_comments.append(tokens)
            counter.update(tokens)

    return tokenized_comments, counter


def build_cooccurrence_network(tokenized_comments: list[list[str]], top_words: list[str]) -> nx.Graph:
    graph = nx.Graph()
    top_word_set = set(top_words)

    for word in top_words:
        graph.add_node(word)

    for tokens in tokenized_comments:
        filtered = sorted(set(token for token in tokens if token in top_word_set))
        for left, right in itertools.combinations(filtered, 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1
            else:
                graph.add_edge(left, right, weight=1)

    return graph


def plot_top_words(word_counter: Counter, output_path: Path, font_path: str) -> None:
    top_items = word_counter.most_common(TOP_N)
    words = [item[0] for item in top_items]
    counts = [item[1] for item in top_items]

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.figure(figsize=(14, 8))
    # 使用黄色到红色的渐变配色，数量越大颜色越偏红
    cmap = plt.get_cmap("YlOrRd")
    try:
        norm = plt.Normalize(min(counts), max(counts))
        bar_colors = [cmap(norm(c)) for c in counts[::-1]]
    except Exception:
        bar_colors = "#E07A5F"
    plt.barh(words[::-1], counts[::-1], color=bar_colors, edgecolor="#7A3F2B", linewidth=0.6)
    plt.title("女书评论高频词 Top 30")
    plt.xlabel("词频")
    plt.ylabel("词语")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_wordcloud(word_counter: Counter, output_path: Path, font_path: str) -> None:
    wordcloud = WordCloud(
        width=1400,
        height=900,
        background_color="white",
        font_path=font_path,
        max_words=TOP_N,
        collocations=False,
    ).generate_from_frequencies(dict(word_counter.most_common(TOP_N)))

    plt.figure(figsize=(14, 9))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_network(graph: nx.Graph, word_counter: Counter, output_path: Path) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(16, 12), facecolor="#FFF9E8")
    ax.set_facecolor("#FFF5CC")

    if graph.number_of_edges() == 0:
        nx.draw_networkx(graph, ax=ax, node_color="#F4C542", edge_color="#C6A969")
        ax.set_title("女书评论高频词共现网络", fontsize=22, fontweight="bold", color="#8A5A00", pad=18)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return

    positions = nx.spring_layout(graph, weight="weight", k=1.2, iterations=200, seed=42)
    node_sizes = [word_counter[node] * 95 for node in graph.nodes]
    node_colors = [plt.cm.YlOrBr(0.28 + min(word_counter[node], 80) / 120) for node in graph.nodes]
    edge_widths = [1.2 + math.log1p(data["weight"]) * 2.4 for _, _, data in graph.edges(data=True)]

    nx.draw_networkx_nodes(
        graph,
        positions,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors="#9B6B00",
        linewidths=1.4,
        alpha=0.96,
        ax=ax,
    )
    nx.draw_networkx_edges(graph, positions, width=edge_widths, edge_color="#C9A227", alpha=0.45, ax=ax)

    for node, (x_pos, y_pos) in positions.items():
        font_size = min(20, 12 + word_counter[node] * 0.16)
        label = ax.text(
            x_pos,
            y_pos,
            node,
            fontsize=font_size,
            fontweight="bold",
            ha="center",
            va="center",
            color="#6B4500",
            family="Microsoft YaHei",
            zorder=5,
        )
        label.set_path_effects([
            path_effects.Stroke(linewidth=4.2, foreground="#FFFDF4", alpha=0.98),
            path_effects.Normal(),
        ])

    ax.set_title("女书评论高频词共现网络", fontsize=22, fontweight="bold", color="#8A5A00", pad=18)
    ax.text(
        0.5,
        1.01,
        "暖黄色高亮主题 | 气泡越大代表词频越高 | 连线越粗代表共现越强",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=12,
        color="#A16C00",
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def compute_sentiment_scores(comments: list[str]) -> list[float]:
    scores: list[float] = []
    for comment in comments:
        if not comment:
            continue
        try:
            scores.append(SnowNLP(comment).sentiments)
        except Exception:
            continue
    return scores


def plot_sentiment_distribution(scores: list[float], output_path: Path) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(13, 8), facecolor="#F8FBFF")
    ax.set_facecolor("#FFFDF8")

    gradient = [[0.0, 0.15], [0.65, 0.95]]
    ax.imshow(
        gradient,
        extent=(0, 1, 0, 1),
        transform=ax.transAxes,
        cmap="Pastel1",
        alpha=0.24,
        aspect="auto",
        zorder=0,
    )

    counts, bins, patches = ax.hist(scores, bins=20, edgecolor="#FFFFFF", linewidth=1.3, alpha=0.92, zorder=3)
    pastel_colors = ["#A9DEF9", "#E4C1F9", "#D0F4DE", "#FCF6BD", "#FFCFD2"]
    for index, patch in enumerate(patches):
        patch.set_facecolor(pastel_colors[index % len(pastel_colors)])

    mean_score = sum(scores) / len(scores) if scores else 0
    median_score = sorted(scores)[len(scores) // 2] if scores else 0

    ax.axvspan(0, 0.4, color="#FFD6D6", alpha=0.28, zorder=1)
    ax.axvspan(0.4, 0.6, color="#FFF1B8", alpha=0.24, zorder=1)
    ax.axvspan(0.6, 1.0, color="#D8F3DC", alpha=0.24, zorder=1)
    ax.axvline(mean_score, color="#FF6B6B", linestyle="--", linewidth=2.1, label=f"平均值 {mean_score:.3f}", zorder=4)
    ax.axvline(median_score, color="#4D96FF", linestyle=":", linewidth=2.3, label=f"中位数 {median_score:.3f}", zorder=4)

    zone_label_height = max(counts) * 0.88 if len(counts) else 0
    ax.text(0.12, zone_label_height, "低分区", color="#C44536", fontsize=15, fontweight="bold")
    ax.text(0.46, zone_label_height, "中性区", color="#B08900", fontsize=15, fontweight="bold")
    ax.text(0.75, zone_label_height, "高分区", color="#2D6A4F", fontsize=15, fontweight="bold")

    ax.scatter(scores, [0.45] * len(scores), s=14, color="#7B2CBF", alpha=0.08, zorder=2)
    ax.text(
        0.5,
        1.01,
        "浅色主题 | 分数区间底色高亮 | 均值与中位数双参考线",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=16,
        color="#6D6875",
    )
    ax.set_xlabel("情感得分（0-1）", fontsize=19, fontweight="bold", color="#4A4E69")
    ax.set_ylabel("评论数量", fontsize=19, fontweight="bold", color="#4A4E69")
    ax.tick_params(axis="both", labelsize=16)
    ax.grid(axis="y", linestyle="--", alpha=0.18)
    ax.legend(frameon=False, fontsize=16, loc="upper left")
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    if not INPUT_XLSX.exists():
        raise FileNotFoundError(f"Input workbook not found: {INPUT_XLSX}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    font_path = get_font_path()
    stopwords = load_stopwords()

    comments_df = pd.read_excel(INPUT_XLSX, sheet_name="comments_clean")
    comments_df["content"] = comments_df["content"].map(normalize_text)
    comments_df = comments_df.dropna(subset=["content"])
    comments_df = comments_df[comments_df["content"].str.len() > 0]

    comments = comments_df["content"].tolist()
    tokenized_comments, word_counter = tokenize_comments(comments, stopwords)
    top_words = [word for word, _ in word_counter.most_common(TOP_N)]

    top_words_df = pd.DataFrame(word_counter.most_common(TOP_N), columns=["word", "frequency"])
    top_words_df.to_csv(OUTPUT_DIR / "top30_words.csv", index=False, encoding="utf-8-sig")

    plot_top_words(word_counter, OUTPUT_DIR / "top30_words_bar.png", font_path)
    plot_wordcloud(word_counter, OUTPUT_DIR / "wordcloud.png", font_path)

    network = build_cooccurrence_network(tokenized_comments, top_words)
    plot_network(network, word_counter, OUTPUT_DIR / "cooccurrence_network.png")

    sentiment_scores = compute_sentiment_scores(comments)
    pd.DataFrame({"content": comments[: len(sentiment_scores)], "sentiment_score": sentiment_scores}).to_csv(
        OUTPUT_DIR / "sentiment_scores.csv", index=False, encoding="utf-8-sig"
    )
    plot_sentiment_distribution(sentiment_scores, OUTPUT_DIR / "sentiment_histogram.png")

    print(f"OUTPUT_DIR={OUTPUT_DIR}")
    print(f"COMMENTS_USED={len(comments)}")
    print(f"TOP_WORDS={top_words[:10]}")
    print(f"SENTIMENT_SCORES={len(sentiment_scores)}")


if __name__ == "__main__":
    main()