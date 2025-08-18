import os
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer
import numpy as np
from typing import List, Tuple, Optional, Iterable
# Set environment variable to avoid tokenizers warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

class TextChunker:
    """
    Split long texts by *token length* so each chunk stays inside the model limit.
    Defaults tuned for short queries vs. passages: ~200 tokens with overlap.
    """

    def __init__(self, tokenizer_name: str, target_len: int = 256, overlap: int = 40, debug: bool = False):
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        self.debug = debug

        # Conservative hard cap for BERT-family backbones
        self.model_max = 512

        # Leave buffer for special tokens (CLS/SEP etc.)
        self.target_len = min(target_len, self.model_max - 20)
        self.overlap = max(0, min(overlap, self.target_len - 1))

        if self.debug:
            print(f"[Chunker] target_len={self.target_len}, overlap={self.overlap}")

    def split(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []

        ids = self.tokenizer.encode(text, add_special_tokens=False)
        if self.debug:
            print(f"[Chunker] tokens_total={len(ids)}")

        # Short text → single chunk
        if len(ids) <= self.target_len:
            return [text]

        stride = self.target_len - self.overlap
        chunks: List[str] = []
        for start in range(0, len(ids), stride):
            window = ids[start:start + self.target_len]
            if not window:
                break
            chunk_text = self.tokenizer.decode(window, skip_special_tokens=True)
            # Guard for empty/whitespace-only decodes
            if chunk_text and chunk_text.strip():
                chunks.append(chunk_text)

        if self.debug:
            print(f"[Chunker] chunks_created={len(chunks)} (stride={stride})")
        return chunks


class TextEmbedding:
    """
    Encode text into normalized embeddings, designed for retrieval.

    Key points:
    - target_len ~256, overlap ~40 to avoid semantic dilution for short queries.
    - normalize_embeddings=True so Cosine/L2(IP) are consistent.
    - Optional title prepend to anchor passages.
    """

    def __init__(
        self,
        model_name: str = MODEL,
        target_len: int = 256,
        overlap: int = 40,
        debug: bool = False
    ):
        self.debug = debug
        self.model = SentenceTransformer(model_name)
        # Use the same tokenizer name as the ST model
        self.chunker = TextChunker(model_name, target_len=target_len, overlap=overlap, debug=debug)

        if self.debug:
            print(f"[Embedding] model={model_name} | target_len={target_len} | overlap={overlap}")

    def _prepend_title(self, title: Optional[str], chunk: str) -> str:
        if title and title.strip():
            return f"{title.strip()}\n\n{chunk}"
        return chunk

    def embed_query(self, query: str) -> List[float]:
        """
        Encode a single query; returns a normalized float32 list.
        """
        if not query or not query.strip():
            return []

        vec = self.model.encode(
            [query],
            batch_size=1,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0].astype(np.float32)
        if self.debug:
            print(f"[Embedding] query_dim={vec.shape[0]}")
        return vec.tolist()

    def embed_passage(
        self,
        text: str,
        title: Optional[str] = None,
        batch_size: int = 16
    ) -> List[Tuple[List[float], str]]:
        """
        Split a long passage into chunks and encode each one.
        Returns list of (vector, chunk_text).
        """
        chunks = self.chunker.split(text)
        if not chunks:
            if self.debug:
                print("[Embedding] No chunks produced")
            return []

        # Prepend title for better anchoring
        enriched: List[str] = [self._prepend_title(title, ch) for ch in chunks]

        # Batch encode for speed; returns np.ndarray (n_chunks, dim)
        embs = self.model.encode(
            enriched,
            batch_size=max(1, batch_size),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False
        ).astype(np.float32)

        if self.debug:
            print(f"[Embedding] chunks_encoded={len(enriched)} | dim={embs.shape[1]}")

        out: List[Tuple[List[float], str]] = []
        for i, ch in enumerate(enriched):
            out.append((embs[i].tolist(), ch))
        return out

    def embed_iter(
        self,
        items: Iterable[Tuple[str, Optional[str]]],
        batch_size: int = 16
    ) -> Iterable[List[Tuple[List[float], str]]]:
        """
        Encode many passages streamed as (text, title). Yields per-item chunk lists.
        Useful cuando estás ingiriendo feeds: procesa uno y seguí.
        """
        for text, title in items:
            yield self.embed_passage(text, title=title, batch_size=batch_size)