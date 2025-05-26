import os
import re
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# 1. Text Cleaning Function
def clean_text(text):
    text = re.sub(r'<[^>]+>', ' ', text)   # Remove HTML tags
    text = re.sub(r'\[[^\]]*\]', ' ', text)  # Remove [1], [12], etc.
    text = re.sub(r'\s+', ' ', text)   # Replace all whitespace with single space
    return text.strip()

# 2. Load and clean .txt articles
def load_articles(folder="wikipedia-articles"):
    print("Looking in folder:", os.path.abspath(folder))
    print("Files found:", os.listdir(folder))
    texts = []
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            with open(os.path.join(folder, filename), "r", encoding="utf-8") as f:
                raw = f.read()
                texts.append(clean_text(raw))
    return texts

all_texts = load_articles()
print(f"Loaded {len(all_texts)} articles.")

# 3. Chunk by character count
def chunk_text_by_chars(text, chunk_chars=800):
    return [
        text[i:i+chunk_chars]
        for i in range(0, len(text), chunk_chars)
    ]

chunks = []
for text in all_texts:
    chunks.extend(chunk_text_by_chars(text, chunk_chars=800))

print(f"Total chunks: {len(chunks)}")
print("Sample chunk lengths (in characters):", [len(c) for c in chunks[:5]])
print("Largest chunk:", max(len(c) for c in chunks), "chars")

# 4. Embed each chunk locally
model = SentenceTransformer("all-MiniLM-L6-v2")
def embed(text):
    vec = model.encode([text])[0]
    return vec / np.linalg.norm(vec)

vectors = np.vstack([embed(chunk) for chunk in chunks])
print(f"Vectors shape: {vectors.shape}")

# 5. Create & save FAISS index
dimension = vectors.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(vectors)
print("FAISS index is ready! Number of vectors:", index.ntotal)

faiss.write_index(index, "wiki.index")
with open("chunks.pkl", "wb") as f:
    pickle.dump(chunks, f)

# 6. RAG Q&A step
index = faiss.read_index("wiki.index")
with open("chunks.pkl", "rb") as f:
    chunks = pickle.load(f)

def embed_query(text):
    vec = model.encode([text])[0]
    return vec / np.linalg.norm(vec)

# --- Ask your question here ---
question = "for which football clubs did Christiano Ronaldo played?"  # Change as needed

q_vec = embed_query(question).reshape(1, -1)

# Retrieve top 3 relevant, then trim
k = 3
scores, ids = index.search(q_vec, k)
retrieved = [chunks[i] for i in ids[0]]

max_passage_chars = 1000
retrieved_trimmed = [chunk[:max_passage_chars] for chunk in retrieved]

print("\n--- Retrieved Passages ---")
for i, chunk in enumerate(retrieved_trimmed, 1):
    print(f"\nPassage {i} (length {len(chunk)} chars):\n{chunk[:200]}...\n")

from openai import OpenAI
client = OpenAI(api_key="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")
prompt = f'''You are a helpful assistant.
Answer the user's question using ONLY the information in the passages.
If the passages are irrelevant, say you don't know.

Question:
{question}

Passages:
''' + "\n\n---\n".join(retrieved_trimmed)

print("\nPrompt length (characters):", len(prompt))
approx_tokens = len(prompt) // 4
print(f"Approximate prompt token count: {approx_tokens}")
if approx_tokens > 7000:
    print("Warning: Prompt is still very long! Lower 'chunk_chars', 'k', or 'max_passage_chars'.")

answer = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2
).choices[0].message.content

print("\n=== AGENT ANSWER ===\n", answer)
