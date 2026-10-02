from __future__ import annotations

from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_benchmark_v2.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_text_similarity.csv"
)

# Final Step 12 semantic-similarity model for this prototype.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

BATCH_SIZE = 32


def main() -> None:
    print("=" * 78)
    print("CIVICBRAIN STEP 12 — SENTENCE TRANSFORMER TEXT SIMILARITY")
    print("=" * 78)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Benchmark V2 file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "pair_id",
        "description_1",
        "description_2",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {column}" for column in missing)
        )

    df["description_1"] = (
        df["description_1"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df["description_2"] = (
        df["description_2"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    empty_text = (
        (df["description_1"] == "")
        | (df["description_2"] == "")
    ).sum()

    print(f"Benchmark pairs loaded     : {len(df)}")
    print(f"Pairs with missing text    : {empty_text}")

    if empty_text:
        raise ValueError(
            "Text similarity cannot be calculated for pairs with "
            "missing complaint text."
        )

    print()
    print(f"Loading model              : {MODEL_NAME}")

    model = SentenceTransformer(MODEL_NAME)

    print("Model loaded               : OK")
    print(
        f"Similarity function        : "
        f"{model.similarity_fn_name}"
    )

    print()
    print("Generating embeddings...")

    embeddings_1 = model.encode(
        df["description_1"].tolist(),
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_tensor=True,
    )

    embeddings_2 = model.encode(
        df["description_2"].tolist(),
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_tensor=True,
    )

    print("Embeddings generated       : OK")

    # Sentence Transformers uses cosine similarity by default for
    # SentenceTransformer.similarity().
    similarities = model.similarity(
        embeddings_1,
        embeddings_2,
    )

    # Pairwise diagonal entries are the score for each corresponding pair.
    scores = similarities.diagonal().detach().cpu().numpy()

    if len(scores) != len(df):
        raise RuntimeError(
            f"Expected {len(df)} similarity scores, got {len(scores)}."
        )

    output = df.copy()

    output["text_similarity"] = scores.astype(float)

    output["model_name"] = MODEL_NAME
    output["similarity_metric"] = "cosine"

    # Keep useful fields for downstream evaluation.
    preferred_columns = [
        "pair_id",
        "pair_type",
        "complaint_id_1",
        "complaint_id_2",
        "category_1",
        "category_2",
        "category_match",
        "description_1",
        "description_2",
        "distance_meters",
        "time_difference_hours",
        "actual_duplicate",
        "text_similarity",
        "model_name",
        "similarity_metric",
        "label_source",
        "label_notes",
    ]

    output = output[
        [column for column in preferred_columns if column in output.columns]
    ]

    output["text_similarity"] = output[
        "text_similarity"
    ].round(6)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Validation / summary
    # ------------------------------------------------------------

    similarity = output["text_similarity"]

    print()
    print("TEXT-SIMILARITY SUMMARY")
    print("-" * 78)
    print(f"Pairs scored                : {len(output)}")
    print(f"Minimum cosine similarity   : {similarity.min():.6f}")
    print(f"Q1 (25%)                    : {similarity.quantile(0.25):.6f}")
    print(f"Median                      : {similarity.median():.6f}")
    print(f"Mean                        : {similarity.mean():.6f}")
    print(f"Q3 (75%)                    : {similarity.quantile(0.75):.6f}")
    print(f"Maximum cosine similarity  : {similarity.max():.6f}")

    positive = output[
        output["actual_duplicate"] == 1
    ]["text_similarity"]

    negative = output[
        output["actual_duplicate"] == 0
    ]["text_similarity"]

    print()
    print("LABEL-GROUP SUMMARY")
    print("-" * 78)
    print(f"Positive pairs              : {len(positive)}")
    print(f"Positive mean similarity    : {positive.mean():.6f}")
    print(f"Positive median similarity  : {positive.median():.6f}")
    print(f"Negative pairs              : {len(negative)}")
    print(f"Negative mean similarity    : {negative.mean():.6f}")
    print(f"Negative median similarity  : {negative.median():.6f}")

    # Overlap indicator. This is descriptive only and does NOT select
    # the final duplicate threshold.
    overlap = (
        positive.min() <= negative.max()
    )

    print()
    print(
        "Similarity-group overlap   : "
        f"{'YES' if overlap else 'NO'}"
    )

    print()
    print(f"Output file                 : {OUTPUT_FILE}")

    print()
    print("IMPORTANT")
    print("-" * 78)
    print(
        "text_similarity is a semantic feature only."
    )
    print(
        "No duplicate threshold or final duplicate decision is applied here."
    )
    print(
        "The final duplicate decision will later combine text similarity "
        "with distance and recency and will be evaluated on the benchmark."
    )

    print()
    print("=" * 78)
    print("TEXT SIMILARITY GENERATION COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
