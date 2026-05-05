from __future__ import annotations

from multiprocessing import freeze_support
from pathlib import Path
import re

import jieba
import pandas as pd
import pyLDAvis
import pyLDAvis.gensim_models
from gensim import corpora
from gensim.models import CoherenceModel, LdaModel


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_XLSX = BASE_DIR / "data" / "xhs" / "excel" / "xhs_cleaned_2026-03-11.xlsx"
OUTPUT_DIR = BASE_DIR / "data" / "xhs" / "analysis"
STOPWORDS_FILE = BASE_DIR / "docs" / "hit_stopwords.txt"

TOPIC_CANDIDATES = [3, 4]
TOP_WORDS_PER_TOPIC = 10
RANDOM_STATE = 42
PASSES = 20
ITERATIONS = 400

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")

BASE_STOPWORDS = {
    "我们", "你们", "他们", "自己", "就是", "一个", "一些", "这个", "那个", "真的", "感觉", "觉得",
    "可以", "还是", "已经", "没有", "不是", "什么", "怎么", "因为", "所以", "然后", "如果",
    "而且", "但是", "比较", "非常", "有点", "一下", "一下子", "其实", "现在", "时候", "这样",
    "那样", "这里", "那里", "里面", "外面", "出来", "进去", "看到", "知道", "希望", "喜欢",
    "评论", "姐妹", "哈哈", "啊啊", "太太", "呜呜", "真的好", "一下吧", "一下下", "一下哦",
    "女书", "江永女书", "小红书", "博主", "帖子", "内容", "感觉好", "很多", "这种",
    "老师", "请问", "谢谢", "有没有", "求", "蹲", "作者", "好看", "太", "好", "就", "也", "还",
    "你好", "大家", "意思", "好像", "之前", "今天", "确实", "发现", "东西", "啊", "了",
    "的", "我", "你", "他", "她", "一定", "特别", "可能", "应该", "去", "漂亮",
    "不能", "图片", "厉害", "快乐", "啊啊啊", "两个", "了解", "那种", "感谢", "不会",
    "姐姐", "这么", "这是", "一点", "一直", "起来", "不过",
}


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
    normalized = URL_PATTERN.sub(" ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return normalized


def tokenize_comments(comments: list[str], stopwords: set[str]) -> list[list[str]]:
    tokenized_comments: list[list[str]] = []
    for comment in comments:
        tokens: list[str] = []
        for token in jieba.lcut(comment):
            cleaned = token.strip().lower()
            if not cleaned:
                continue
            if cleaned in stopwords:
                continue
            if len(cleaned) < 2:
                continue
            if cleaned.isdigit():
                continue
            tokens.append(cleaned)
        if tokens:
            tokenized_comments.append(tokens)
    return tokenized_comments


def build_corpus(texts: list[list[str]]) -> tuple[corpora.Dictionary, list[list[tuple[int, int]]], list[list[str]]]:
    dictionary = corpora.Dictionary(texts)
    dictionary.filter_extremes(no_below=5, no_above=0.35, keep_n=2000)

    filtered_texts: list[list[str]] = []
    corpus: list[list[tuple[int, int]]] = []
    for tokens in texts:
        bow = dictionary.doc2bow(tokens)
        if bow:
            filtered_texts.append(tokens)
            corpus.append(bow)
    return dictionary, corpus, filtered_texts


def select_best_model(
    texts: list[list[str]],
    dictionary: corpora.Dictionary,
    corpus: list[list[tuple[int, int]]],
) -> tuple[LdaModel, int, float]:
    best_model: LdaModel | None = None
    best_num_topics = 0
    best_coherence = -1.0

    for num_topics in TOPIC_CANDIDATES:
        model = LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            random_state=RANDOM_STATE,
            passes=PASSES,
            iterations=ITERATIONS,
            alpha="auto",
            eta="auto",
            per_word_topics=False,
        )
        coherence_model = CoherenceModel(model=model, texts=texts, dictionary=dictionary, coherence="c_v")
        coherence = coherence_model.get_coherence()
        if coherence > best_coherence:
            best_model = model
            best_num_topics = num_topics
            best_coherence = coherence

    if best_model is None:
        raise RuntimeError("Failed to train any LDA model.")
    return best_model, best_num_topics, best_coherence


def export_topics(model: LdaModel) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for topic_id, terms in model.show_topics(num_topics=model.num_topics, num_words=TOP_WORDS_PER_TOPIC, formatted=False):
        for rank, (term, weight) in enumerate(terms, start=1):
            rows.append(
                {
                    "topic_id": topic_id,
                    "rank": rank,
                    "term": term,
                    "weight": round(float(weight), 6),
                }
            )
    topics_df = pd.DataFrame(rows)
    topics_df.to_csv(OUTPUT_DIR / "lda_topics.csv", index=False, encoding="utf-8-sig")
    return topics_df


def save_visualization(model: LdaModel, corpus: list[list[tuple[int, int]]], dictionary: corpora.Dictionary) -> Path:
    visualization = pyLDAvis.gensim_models.prepare(
        model,
        corpus,
        dictionary,
        sort_topics=False,
        n_jobs=1,
    )
    output_html = OUTPUT_DIR / "lda_visualization.html"
    pyLDAvis.save_html(visualization, str(output_html))
    return output_html


if __name__ == "__main__":
    freeze_support()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    comments_df = pd.read_excel(INPUT_XLSX, sheet_name="comments_clean")
    comments_df["content"] = comments_df["content"].map(normalize_text)
    comments_df = comments_df.dropna(subset=["content"])
    comments_df = comments_df[comments_df["content"].str.len() > 0]

    comments = comments_df["content"].tolist()
    stopwords = load_stopwords()
    tokenized_comments = tokenize_comments(comments, stopwords)

    dictionary, corpus, filtered_texts = build_corpus(tokenized_comments)
    lda_model, best_num_topics, best_coherence = select_best_model(filtered_texts, dictionary, corpus)
    topics_df = export_topics(lda_model)
    output_html = save_visualization(lda_model, corpus, dictionary)

    print(f"OUTPUT_HTML={output_html}")
    print(f"NUM_TOPICS={best_num_topics}")
    print(f"COHERENCE={best_coherence:.4f}")
    for topic_id in range(best_num_topics):
        topic_terms = topics_df[topics_df["topic_id"] == topic_id]["term"].head(TOP_WORDS_PER_TOPIC).tolist()
        print(f"TOPIC_{topic_id + 1}={','.join(topic_terms)}")