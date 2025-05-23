from sentence_transformers import SentenceTransformer, util
from fuzzywuzzy import fuzz

model = SentenceTransformer("all-MiniLM-L6-v2")

def compute_semantic_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity between sentence embeddings."""
    emb1 = model.encode(text1, convert_to_tensor=True)
    emb2 = model.encode(text2, convert_to_tensor=True)
    return util.pytorch_cos_sim(emb1, emb2).item()

def compute_fuzzy_ratio(text1: str, text2: str) -> float:
    """Compute fuzzy string matching score."""
    return fuzz.token_set_ratio(text1, text2) / 100.0

def is_match(text1: str, text2: str, threshold: float = 0.8) -> tuple[bool, float]:
    """
    Return whether texts are similar enough to be considered a match.
    Returns a tuple: (match: bool, avg_score: float)
    """
    semantic = compute_semantic_similarity(text1, text2)
    fuzzy = compute_fuzzy_ratio(text1, text2)
    score = (semantic + fuzzy) / 2
    return score >= threshold, round(score, 3)

# if __name__ == "__main__":
#     import sys
#     if len(sys.argv) < 3:
#         print("Usage: python script.py 'text1' 'text2' [threshold]")
#         sys.exit(1)

#     text1 = sys.argv[1]
#     text2 = sys.argv[2]
#     threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8

#     match, score = is_match(text1, text2, threshold)
#     print(f"Match: {match}, Score: {score}")