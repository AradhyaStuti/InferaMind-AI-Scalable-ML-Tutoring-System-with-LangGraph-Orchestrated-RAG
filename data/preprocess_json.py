import requests
import json
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import joblib

def create_embedding(text_list):
    if isinstance(text_list, str):
        text_list = [text_list]
    payload = {"model": "bge-m3", "input": text_list}

    try:
        r = requests.post("http://localhost:11434/api/embed", json=payload, timeout=30)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Embedding request failed: {e}")

    data = r.json()
    embeddings = data.get("embeddings")
    if embeddings is None:
        raise ValueError(f"Response JSON missing 'embeddings': {data}")
    return embeddings

FILE_PATH = "jsons.json"  

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = json.load(f)

chunks = content.get("chunks", [])
if not chunks:
    raise RuntimeError("No 'chunks' found in jsons.json or it's empty.")

texts = [c.get("text", "") for c in chunks]
embeddings = create_embedding(texts)

if len(embeddings) != len(texts):
    raise ValueError(f"Embeddings count ({len(embeddings)}) != chunks count ({len(texts)})")

my_dicts = []
for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
    chunk['chunk_id'] = idx
    chunk['embedding'] = list(emb)
    my_dicts.append(chunk)

df = pd.DataFrame.from_records(my_dicts)

joblib.dump(df, "embeddings.joblib")
print(f"Loaded {len(df)} chunks.")
print(df.head())

incoming_query = input("Ask a question: ").strip()
question_embedding = create_embedding([incoming_query])[0]

emb_matrix = np.vstack(df['embedding'].values).astype(float)

similarities = cosine_similarity(emb_matrix, [question_embedding]).flatten()
print("Top similarity scores (first 10):", similarities[:10])

top_results = 3
top_idx = similarities.argsort()[::-1][:top_results]
print("Top indices:", top_idx)

result_df = df.iloc[top_idx].copy()
cols_to_show = [c for c in ('text', 'number', 'title') if c in result_df.columns]
print(result_df[cols_to_show] if cols_to_show else result_df[['text']])


