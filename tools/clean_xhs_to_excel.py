from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = BASE_DIR / "data" / "xhs" / "csv"
EXCEL_DIR = BASE_DIR / "data" / "xhs" / "excel"
CONTENTS_CSV = CSV_DIR / "search_contents_2026-03-11.csv"
COMMENTS_CSV = CSV_DIR / "search_comments_2026-03-11.csv"
OUTPUT_XLSX = EXCEL_DIR / "xhs_cleaned_2026-03-11.xlsx"

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE,
)
BRACKET_EMOJI_PATTERN = re.compile(r"\[[^\[\]]{1,12}\]")
WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_text(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    if not isinstance(value, str):
        return value
    cleaned = URL_PATTERN.sub(" ", value)
    cleaned = EMOJI_PATTERN.sub(" ", cleaned)
    cleaned = BRACKET_EMOJI_PATTERN.sub(" ", cleaned)
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned).strip(" ,;|/")
    return cleaned if cleaned else pd.NA


def clean_dataframe(df: pd.DataFrame, text_columns: list[str], dedupe_subset: list[str]) -> tuple[pd.DataFrame, dict[str, int]]:
    stats: dict[str, int] = {"original_rows": len(df)}
    df = df.copy()
    df = df.dropna(axis=0, how="all")
    stats["after_drop_all_empty"] = len(df)

    for column in text_columns:
        if column in df.columns:
            df[column] = df[column].map(clean_text)

    df = df.replace(r"^\s*$", pd.NA, regex=True)
    df = df.dropna(axis=0, how="all")
    stats["after_text_clean"] = len(df)

    existing_dedupe_columns = [column for column in dedupe_subset if column in df.columns]
    if existing_dedupe_columns:
        df = df.drop_duplicates(subset=existing_dedupe_columns, keep="first")
    else:
        df = df.drop_duplicates(keep="first")
    stats["after_deduplicate"] = len(df)
    return df, stats


def main() -> None:
    EXCEL_DIR.mkdir(parents=True, exist_ok=True)

    contents = pd.read_csv(CONTENTS_CSV, encoding="utf-8-sig")
    comments = pd.read_csv(COMMENTS_CSV, encoding="utf-8-sig")

    contents = contents[
        [
            "note_id",
            "type",
            "title",
            "desc",
            "time",
            "user_id",
            "nickname",
            "liked_count",
            "collected_count",
            "comment_count",
            "share_count",
            "ip_location",
            "tag_list",
            "source_keyword",
        ]
    ]
    comments = comments[
        [
            "comment_id",
            "create_time",
            "ip_location",
            "note_id",
            "content",
            "user_id",
            "nickname",
            "sub_comment_count",
            "parent_comment_id",
            "like_count",
        ]
    ]

    contents, content_stats = clean_dataframe(
        contents,
        text_columns=["title", "desc", "nickname", "ip_location", "tag_list", "source_keyword"],
        dedupe_subset=["note_id"],
    )
    comments, comment_stats = clean_dataframe(
        comments,
        text_columns=["content", "nickname", "ip_location"],
        dedupe_subset=["comment_id"],
    )

    contents = contents.dropna(subset=["note_id", "title"], how="any")
    comments = comments.dropna(subset=["comment_id", "note_id", "content"], how="any")

    summary = pd.DataFrame(
        [
            {"sheet": "contents_clean", **content_stats, "final_rows": len(contents)},
            {"sheet": "comments_clean", **comment_stats, "final_rows": len(comments)},
        ]
    )

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="summary", index=False)
        contents.to_excel(writer, sheet_name="contents_clean", index=False)
        comments.to_excel(writer, sheet_name="comments_clean", index=False)

    print(f"OUTPUT={OUTPUT_XLSX}")
    print(f"CONTENTS_FINAL={len(contents)}")
    print(f"COMMENTS_FINAL={len(comments)}")


if __name__ == "__main__":
    main()