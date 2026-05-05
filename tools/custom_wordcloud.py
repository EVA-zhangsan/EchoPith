from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter, ImageOps
from wordcloud import WordCloud


ROOT_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT_DIR / "data" / "xhs" / "analysis" / "top30_words.csv"
MASK_PATH = ROOT_DIR / "assets" / "wordcloud_mask.png"
FONT_PATH = ROOT_DIR / "assets" / "wordcloud_font.otf"
OUTPUT_PATH = ROOT_DIR / "data" / "xhs" / "analysis" / "beautiful_wordcloud.png"

PALETTE = [
    "#6E3B2A",
    "#8C4F3D",
    "#A86448",
    "#B88646",
    "#C79A5B",
    "#7B2F2F",
    "#A63D40",
]


def load_word_frequencies(csv_path: Path) -> dict[str, int]:
    data_frame = pd.read_csv(csv_path)
    if data_frame.shape[1] < 2:
        raise ValueError(f"CSV must contain at least two columns: {csv_path}")

    first_two_columns = data_frame.iloc[:, :2].copy()
    first_two_columns.columns = ["keyword", "frequency"]
    first_two_columns["keyword"] = first_two_columns["keyword"].astype(str).str.strip()
    first_two_columns["frequency"] = pd.to_numeric(first_two_columns["frequency"], errors="coerce")

    clean_rows = first_two_columns.dropna(subset=["keyword", "frequency"])
    clean_rows = clean_rows[clean_rows["keyword"] != ""]
    clean_rows["frequency"] = clean_rows["frequency"].astype(int)
    clean_rows = clean_rows[clean_rows["frequency"] > 0]

    if clean_rows.empty:
        raise ValueError(f"No valid keyword/frequency rows found in {csv_path}")

    return dict(zip(clean_rows["keyword"], clean_rows["frequency"], strict=False))


def build_mask(mask_path: Path) -> np.ndarray:
    image = Image.open(mask_path).convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.GaussianBlur(radius=1.2))

    gray_array = np.array(image)
    threshold = 235
    binary_array = np.where(gray_array >= threshold, 255, 0).astype(np.uint8)

    white_ratio = float(np.mean(binary_array == 255))
    if white_ratio < 0.35:
        binary_array = np.where(binary_array == 255, 0, 255).astype(np.uint8)

    return binary_array


def elegant_color_func(
    word: str,
    font_size: int,
    position: tuple[int, int],
    orientation: int | None,
    random_state: random.Random | None = None,
    **_: object,
) -> str:
    if random_state is None:
        return random.choice(PALETTE)
    return random_state.choice(PALETTE)


def create_wordcloud(
    data_dict: dict[str, int],
    img_array: np.ndarray,
    font_path: Path,
    max_words: int,
    margin: int,
    prefer_horizontal: float,
    relative_scaling: float,
    min_font_size: int,
    repeat: bool,
) -> WordCloud:
    wordcloud = WordCloud(
        font_path=str(font_path),
        mask=img_array,
        background_color="rgba(255, 255, 255, 0)",
        mode="RGBA",
        width=2000,
        height=2000,
        max_words=max_words,
        collocations=False,
        repeat=repeat,
        margin=margin,
        prefer_horizontal=prefer_horizontal,
        relative_scaling=relative_scaling,
        min_font_size=min_font_size,
        random_state=42,
    ).generate_from_frequencies(data_dict)

    return wordcloud.recolor(color_func=elegant_color_func, random_state=random.Random(42))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a custom wordcloud from CSV frequencies.")
    parser.add_argument("--csv", type=Path, default=CSV_PATH, help="Path to the frequency CSV file.")
    parser.add_argument("--mask", type=Path, default=MASK_PATH, help="Path to the mask image.")
    parser.add_argument("--font", type=Path, default=FONT_PATH, help="Path to the font file.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Path to save the output PNG.")
    parser.add_argument("--debug-mask-output", type=Path, help="Optional path to save the processed binary mask.")
    parser.add_argument("--max-words", type=int, default=100, help="Maximum number of words to draw.")
    parser.add_argument("--margin", type=int, default=4, help="Margin between words.")
    parser.add_argument("--prefer-horizontal", type=float, default=0.92, help="Preference for horizontal words.")
    parser.add_argument("--relative-scaling", type=float, default=0.18, help="Relative scaling factor for word sizes.")
    parser.add_argument("--min-font-size", type=int, default=10, help="Minimum font size.")
    parser.add_argument("--repeat", action="store_true", help="Repeat words to fill the mask densely.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = args.csv if args.csv.is_absolute() else ROOT_DIR / args.csv
    mask_path = args.mask if args.mask.is_absolute() else ROOT_DIR / args.mask
    font_path = args.font if args.font.is_absolute() else ROOT_DIR / args.font
    output_path = args.output if args.output.is_absolute() else ROOT_DIR / args.output
    debug_mask_output = None
    if args.debug_mask_output:
        debug_mask_output = args.debug_mask_output if args.debug_mask_output.is_absolute() else ROOT_DIR / args.debug_mask_output

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    if not mask_path.exists():
        raise FileNotFoundError(f"Mask image not found: {mask_path}")
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")

    data_dict = load_word_frequencies(csv_path)
    img_array = build_mask(mask_path)
    if debug_mask_output is not None:
        debug_mask_output.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(img_array).save(debug_mask_output)
    wordcloud = create_wordcloud(
        data_dict=data_dict,
        img_array=img_array,
        font_path=font_path,
        max_words=args.max_words,
        margin=args.margin,
        prefer_horizontal=args.prefer_horizontal,
        relative_scaling=args.relative_scaling,
        min_font_size=args.min_font_size,
        repeat=args.repeat,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wordcloud.to_file(str(output_path))
    print(f"Saved custom word cloud to: {output_path}")


if __name__ == "__main__":
    main()