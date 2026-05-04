"""Embed transcript chunks from jsons.json and write embeddings.joblib."""

import json

import joblib
import pandas as pd
import requests


def create_embedding(text_list):
    if isinstance(text_list, str):
        text_list = [text_list]
    payload = {"model": "bge-m3", "input": text_list}

    r = requests.post("http://localhost:11434/api/embed", json=payload, timeout=30)
    r.raise_for_status()

    embeddings = r.json().get("embeddings")
    if embeddings is None:
        raise ValueError("Response JSON missing 'embeddings'")
    return embeddings


def main():
    with open("jsons.json", "r", encoding="utf-8") as f:
        content = json.load(f)

    chunks = content.get("chunks", [])
    if not chunks:
        raise RuntimeError("No 'chunks' found in jsons.json")

    texts = [c.get("text", "") for c in chunks]
    embeddings = create_embedding(texts)

    if len(embeddings) != len(texts):
        raise ValueError(f"Embeddings count ({len(embeddings)}) != chunks count ({len(texts)})")

    rows = []
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        chunk["chunk_id"] = idx
        chunk["embedding"] = list(emb)
        rows.append(chunk)

    df = pd.DataFrame.from_records(rows)
    joblib.dump(df, "embeddings.joblib")
    print(f"Wrote embeddings.joblib with {len(df)} chunks.")


if __name__ == "__main__":
    main()

