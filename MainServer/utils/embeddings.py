import numpy as np
import requests
import os

def embed(text):
    r = requests.post(
        os.getenv("EMBEDDING_URL"),
        json={
            "model": os.getenv("EMBEDDING_MODEL"),
            "prompt": text
        }
    )
    return np.array(r.json()["embedding"])

def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))