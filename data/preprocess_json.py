"""Embed transcript chunks from a JSON file and write/merge into embeddings.joblib.

Usage:
    python preprocess_json.py                                       # default course, jsons.json
    python preprocess_json.py --course dl-deep-learning-specialization --input dl_chunks.json
"""

import argparse
import json
import os
import sys

import joblib
import pandas as pd
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
DEFAULT_COURSE_ID = "ml-andrew-ng-c1"


def create_embedding(text_list):
    if isinstance(text_list, str):
        text_list = [text_list]
    payload = {"model": EMBED_MODEL, "input": text_list}

    r = requests.post(f"{OLLAMA_URL}/api/embed", json=payload, timeout=60)
    r.raise_for_status()

    embeddings = r.json().get("embeddings")
    if embeddings is None:
        raise ValueError("Response JSON missing 'embeddings'")
    return embeddings


def main():
    parser = argparse.ArgumentParser(description="Embed transcript chunks for one course.")
    parser.add_argument("--course", default=DEFAULT_COURSE_ID, help="Course id matching data/courses.json")
    parser.add_argument("--input", default="jsons.json", help="Input transcript JSON file")
    parser.add_argument("--output", default="embeddings.joblib", help="Output joblib")
    parser.add_argument("--replace", action="store_true",
                        help="Replace existing rows for this course (default: merge/append)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        content = json.load(f)

    chunks = content.get("chunks", [])
    if not chunks:
        raise RuntimeError(f"No 'chunks' found in {args.input}")

    texts = [c.get("text", "") for c in chunks]
    embeddings = create_embedding(texts)

    if len(embeddings) != len(texts):
        raise ValueError(f"Embeddings count ({len(embeddings)}) != chunks count ({len(texts)})")

    rows = []
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        chunk["chunk_id"] = idx
        chunk["embedding"] = list(emb)
        chunk["course_id"] = args.course
        rows.append(chunk)

    new_df = pd.DataFrame.from_records(rows)

    if os.path.exists(args.output) and not args.replace:
        existing = joblib.load(args.output)
        if "course_id" not in existing.columns:
            existing["course_id"] = DEFAULT_COURSE_ID
        existing = existing[existing["course_id"] != args.course]
        merged = pd.concat([existing, new_df], ignore_index=True)
    else:
        merged = new_df

    joblib.dump(merged, args.output)
    print(f"Wrote {args.output}: {len(merged)} total rows ({len(new_df)} new for course={args.course!r})")


if __name__ == "__main__":
    main()
