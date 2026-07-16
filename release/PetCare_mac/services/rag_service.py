"""
RAG 知识库引擎 — 兽医专业知识检索增强生成

提供:
  1. 知识库索引构建（PDF → 文本块 → 向量 → FAISS）
  2. 语义检索 + 关键词混合检索
  3. 知识增强 Prompt 构建
  4. DeepSeek LLM 对接
"""

import os
import json
import re
import pickle
import numpy as np
from config import Config
from services.deepseek_service import get_deepseek


class VetKnowledgeBase:
    """兽医专业知识库 — 向量存储 + 检索"""

    def __init__(self):
        self.data_dir = Config.RAG_DATA_DIR
        self.embedding_model_name = Config.RAG_EMBEDDING_MODEL
        self.chunk_size = Config.RAG_CHUNK_SIZE
        self.chunk_overlap = Config.RAG_CHUNK_OVERLAP
        self.top_k = Config.RAG_TOP_K
        self.similarity_threshold = Config.RAG_SIMILARITY_THRESHOLD

        self._embedding_model = None
        self._index = None
        self._chunks = []
        self._chunk_meta = []
        self._keyword_index = {}

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            os.makedirs(Config.RAG_MODEL_CACHE_DIR, exist_ok=True)
            os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", Config.RAG_MODEL_CACHE_DIR)
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(
                self.embedding_model_name,
                cache_folder=Config.RAG_MODEL_CACHE_DIR,
            )
        return self._embedding_model

    @property
    def is_ready(self) -> bool:
        return os.path.exists(os.path.join(self.data_dir, "faiss_index.bin"))

    def _get_index_path(self):
        return os.path.join(self.data_dir, "faiss_index.bin")

    def _get_chunks_path(self):
        return os.path.join(self.data_dir, "chunks.pkl")

    def _get_meta_path(self):
        return os.path.join(self.data_dir, "chunk_meta.pkl")

    def _get_kwindex_path(self):
        return os.path.join(self.data_dir, "keyword_index.pkl")

    def parse_pdf(self, pdf_path: str) -> list[dict]:
        """解析 PDF 并按兽医专业语义切分为文本块"""
        import fitz

        pages = []
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                pages.append({
                    "page": page_num + 1,
                    "text": text.strip(),
                    "pdf_source": os.path.basename(pdf_path),
                })
        doc.close()
        return pages

    def _split_into_chunks(self, pages: list[dict]) -> list[dict]:
        """
        按兽医文档结构智能切分
        分隔优先级: 章标题 > 节标题 > 段落 > 固定长度回退
        """
        full_text = ""
        page_map = []
        source_map = {}
        for p in pages:
            start_pos = len(full_text)
            full_text += p["text"] + "\n"
            end_pos = len(full_text)
            page_map.append((start_pos, end_pos, p["page"]))
            source_map[(start_pos, end_pos)] = p.get("pdf_source", "") or p.get("source", "")

        chapter_pattern = re.compile(
            r'(?:^|\n)\s*(?:Chapter\s+\d+|'
            r'CHAPTER\s+\d+|'
            r'第[一二三四五六七八九十百千\d]+[章节篇])',
            re.IGNORECASE,
        )
        section_pattern = re.compile(
            r'(?:^|\n)\s*\d+\.[\d]+(?:\.[\d]+)?\s+[A-Z]',
        )

        separators = set()
        for match in chapter_pattern.finditer(full_text):
            if match.start() > 0:
                separators.add(match.start())
        for match in section_pattern.finditer(full_text):
            if match.start() > 0:
                separators.add(match.start())
        separators = sorted(separators)

        min_chars_between = 400
        filtered = []
        last = -min_chars_between
        for pos in separators:
            if pos - last >= min_chars_between:
                filtered.append(pos)
                last = pos
            elif len(filtered) > 0 and pos - last < min_chars_between:
                pass
            else:
                filtered.append(pos)
                last = pos

        chunks = []
        if filtered:
            for i, pos in enumerate(filtered):
                start = pos
                end = filtered[i + 1] if i + 1 < len(filtered) else len(full_text)
                segment = full_text[start:end].strip()
                if len(segment) < 20:
                    continue
                sub_chunks = self._split_long_segment(segment, start, page_map)
                chunks.extend(sub_chunks)
        else:
            sub_chunks = self._split_long_segment(full_text, 0, page_map)
            chunks.extend(sub_chunks)

        return chunks, source_map

    def _split_long_segment(self, text: str, offset: int, page_map: list) -> list[dict]:
        """对长文本做滑动窗口切分，保持语义完整性，硬限制单块大小"""
        chunks = []
        paragraphs = re.split(r'\n\s*\n', text)
        max_chunk = self.chunk_size
        min_chunk = 150
        overlap_paras = 2

        para_starts = []
        pos = offset
        for para in paragraphs:
            para_starts.append(pos)
            pos += len(para) + 2

        i = 0
        while i < len(paragraphs):
            para = paragraphs[i].strip()
            if not para:
                i += 1
                continue

            if len(para) > max_chunk:
                sub = self._split_long_line(para, max_chunk, min_chunk)
                page_num = self._find_page(page_map, para_starts[i])
                for s in sub:
                    chunks.append({"text": s, "page": page_num, "start_char": para_starts[i]})
                i += 1
                continue

            current_chunk = para
            current_start = para_starts[i]
            j = i + 1
            while j < len(paragraphs):
                next_para = paragraphs[j].strip()
                if not next_para:
                    j += 1
                    continue
                if len(next_para) > max_chunk:
                    break
                if len(current_chunk) + len(next_para) + 2 <= max_chunk:
                    current_chunk += "\n\n" + next_para
                    j += 1
                else:
                    break

            if len(current_chunk.strip()) >= min_chunk or j == i + 1:
                page_num = self._find_page(page_map, current_start)
                chunks.append({
                    "text": current_chunk.strip(),
                    "page": page_num,
                    "start_char": current_start,
                })

            if j <= i:
                i += 1
            else:
                overlap_idx = max(i + 1, j - overlap_paras)
                i = overlap_idx
                if i >= len(paragraphs):
                    break

        return chunks

    def _split_long_line(self, text: str, max_chunk: int, min_chunk: int) -> list[str]:
        """将单段超长文本按句子边界滑动窗口切分"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 1:
            result = []
            for i in range(0, len(text), max_chunk - self.chunk_overlap):
                result.append(text[i:i + max_chunk])
            return result

        result = []
        current = ""
        for sent in sentences:
            if not current:
                current = sent
            elif len(current) + len(sent) + 1 <= max_chunk:
                current += " " + sent
            else:
                if len(current) >= min_chunk:
                    result.append(current)
                current = sent

        if current and len(current) >= min_chunk:
            result.append(current)
        elif current and result:
            result[-1] += " " + current

        return result if result else [text[:max_chunk]]

    def _find_page(self, page_map: list, char_pos: int) -> int:
        for start, end, page in page_map:
            if start <= char_pos < end:
                return page
        return page_map[-1][2] if page_map else 1

    def _find_source(self, source_map: dict, char_pos: int) -> str:
        for (start, end), src in source_map.items():
            if start <= char_pos < end:
                return src
        return list(source_map.values())[-1] if source_map else ""

    def build_index(self, pdf_path: str, progress_callback=None) -> dict:
        """完整索引构建流程: PDF解析 → 切块 → 向量化 → 存储"""
        return self.build_index_from_multiple([pdf_path], progress_callback)

    def build_index_from_multiple(self, pdf_paths: list[str], progress_callback=None) -> dict:
        """多 PDF 批量索引构建，所有文档合并到一个索引中"""
        os.makedirs(self.data_dir, exist_ok=True)

        all_pages = []
        for pdf_path in pdf_paths:
            if progress_callback:
                progress_callback("step", f"解析: {os.path.basename(pdf_path)}")
            pages = self.parse_pdf(pdf_path)
            all_pages.extend(pages)

        if not all_pages:
            return {"error": "所有 PDF 解析失败或为空", "chunks": 0}

        if progress_callback:
            progress_callback("step", f"全部解析完成，共 {len(all_pages)} 页，正在智能切分...")
        raw_chunks, source_map = self._split_into_chunks(all_pages)

        self._chunks = []
        self._chunk_meta = []
        seen = set()
        for rc in raw_chunks:
            text = rc["text"]
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            if len(text) < 40:
                continue
            h = hash(text[:200])
            if h in seen:
                continue
            seen.add(h)

            title = ""
            lines = text.split("\n")
            for line in lines[:3]:
                line = line.strip()
                if len(line) < 80 and (
                    re.match(r'第[一二三四五六七八九十百千\d]+[章节]', line)
                    or re.match(r'Chapter\s+\d+', line)
                    or re.match(r'CHAPTER\s+\d+', line)
                    or re.match(r'\d+[\.\、]', line)
                ):
                    title = line
                    break

            source = self._find_source(source_map, rc["start_char"])
            self._chunks.append(text)
            self._chunk_meta.append({
                "id": len(self._chunks) - 1,
                "page": rc["page"],
                "char_count": len(text),
                "title": title,
                "source": source,
            })

        if progress_callback:
            progress_callback("step", f"切分完成，共 {len(self._chunks)} 个文本块，正在向量化...")

        if not self._chunks:
            return {"error": "文档切分后无有效文本块", "chunks": 0}

        embeddings = self.embedding_model.encode(
            self._chunks,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        if progress_callback:
            progress_callback("step", "向量化完成，正在构建 FAISS 索引...")

        import faiss
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings.astype(np.float32))

        faiss.write_index(self._index, self._get_index_path())
        with open(self._get_chunks_path(), "wb") as f:
            pickle.dump(self._chunks, f)
        with open(self._get_meta_path(), "wb") as f:
            pickle.dump(self._chunk_meta, f)

        self._build_keyword_index()
        with open(self._get_kwindex_path(), "wb") as f:
            pickle.dump(self._keyword_index, f)

        sources = set(m.get("source", "") for m in self._chunk_meta)
        return {
            "success": True,
            "files": len(pdf_paths),
            "pages": len(all_pages),
            "chunks": len(self._chunks),
            "embedding_dim": dim,
            "sources": sorted(sources),
            "index_path": self._get_index_path(),
        }

    def _build_keyword_index(self):
        """构建 BM25 关键词倒排索引"""
        from collections import defaultdict
        self._keyword_index = defaultdict(list)

        for idx, text in enumerate(self._chunks):
            words = set(self._tokenize(text))
            for word in words:
                self._keyword_index[word].append(idx)

    def _tokenize(self, text: str) -> list[str]:
        tokens = []
        for chunk in re.split(r'[，,。；;：:\s\n]+', text):
            chunk = chunk.strip()
            if not chunk:
                continue
            if len(chunk) <= 8:
                tokens.append(chunk)
                continue
            for i in range(len(chunk) - 1):
                bigram = chunk[i:i + 2]
                if not re.search(r'[^\u4e00-\u9fff]', bigram):
                    tokens.append(bigram)
            if len(chunk) <= 12:
                tokens.append(chunk)
            else:
                for i in range(0, len(chunk), 6):
                    tokens.append(chunk[i:i + 6])
        return tokens

    def load(self) -> bool:
        """加载已构建的索引"""
        try:
            import faiss
            self._index = faiss.read_index(self._get_index_path())
            with open(self._get_chunks_path(), "rb") as f:
                self._chunks = pickle.load(f)
            with open(self._get_meta_path(), "rb") as f:
                self._chunk_meta = pickle.load(f)
            if os.path.exists(self._get_kwindex_path()):
                with open(self._get_kwindex_path(), "rb") as f:
                    self._keyword_index = pickle.load(f)
            else:
                self._build_keyword_index()
            return True
        except Exception:
            return False

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """混合检索: 向量语义 + 关键词匹配"""
        if top_k is None:
            top_k = self.top_k

        if self._index is None:
            return []

        query_vec = self.embedding_model.encode(
            [query],
            normalize_embeddings=True,
        ).astype(np.float32)

        vector_k = min(top_k * 3, len(self._chunks))
        scores, indices = self._index.search(query_vec, vector_k)

        keyword_scores = {}
        query_tokens = set(self._tokenize(query))
        for token in query_tokens:
            for chunk_idx in self._keyword_index.get(token, []):
                keyword_scores[chunk_idx] = keyword_scores.get(chunk_idx, 0) + 1

        max_kw = max(keyword_scores.values()) if keyword_scores else 1
        for idx, count in keyword_scores.items():
            keyword_scores[idx] = count / max_kw

        combined = {}
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._chunks):
                continue
            kw_weight = 0.3
            kw_bonus = keyword_scores.get(int(idx), 0) * kw_weight
            combined[int(idx)] = float(score) + kw_bonus

        sorted_results = sorted(combined.items(), key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in sorted_results[:top_k]:
            if score < self.similarity_threshold:
                continue
            meta = self._chunk_meta[idx] if idx < len(self._chunk_meta) else {}
            results.append({
                "id": idx,
                "score": round(score, 4),
                "text": self._chunks[idx],
                "page": meta.get("page", 0),
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
            })

        return results

    def retrieve_context(self, query: str, max_tokens: int = 3000) -> str:
        """检索并拼接为上下文文本，用于注入 LLM Prompt"""
        results = self.search(query)
        if not results:
            return ""

        context_parts = []
        token_estimate = 0

        for r in results:
            chunk_tokens = len(r["text"]) // 2
            if token_estimate + chunk_tokens > max_tokens:
                break

            header = ""
            if r["title"]:
                header = f"【{r['title']}】"
            context_parts.append(
                f"{header}[第{r['page']}页] {r['text']}"
            )
            token_estimate += chunk_tokens

        return "\n\n---\n\n".join(context_parts)

    def get_stats(self) -> dict:
        if not self.is_ready:
            return {"status": "not_indexed"}

        return {
            "status": "ready",
            "total_chunks": len(self._chunks),
            "total_pages": max((m.get("page", 0) for m in self._chunk_meta), default=0),
            "source": self._chunk_meta[0]["source"] if self._chunk_meta else "",
            "embedding_model": self.embedding_model_name,
        }


_kb_en = None
_kb_zh = None


def get_knowledge_base(lang: str = "en") -> VetKnowledgeBase:
    global _kb_en, _kb_zh
    if lang == "zh":
        if _kb_zh is None:
            _kb_zh = VetKnowledgeBase()
            _kb_zh.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "knowledge_base_zh")
            if _kb_zh.is_ready:
                _kb_zh.load()
        return _kb_zh
    else:
        if _kb_en is None:
            _kb_en = VetKnowledgeBase()
            _kb_en.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "knowledge_base_en")
            if _kb_en.is_ready:
                _kb_en.load()
        return _kb_en


def rag_is_ready(lang: str = "en") -> bool:
    kb = get_knowledge_base(lang)
    return kb.is_ready


def rag_chat(system_prompt: str, user_message: str, json_mode: bool = False, lang: str = "en") -> str:
    """检索增强对话: 自动从知识库检索相关内容注入 Prompt"""
    kb = get_knowledge_base(lang)
    context = ""

    if kb.is_ready:
        if not kb._chunks:
            kb.load()
        context = kb.retrieve_context(user_message, max_tokens=3000)

    if context:
        lang_hint = "以下是从兽医专业中文文献中检索到的相关知识" if lang == "zh" else "以下是从兽医专业文献中检索到的相关知识"
        augmented_system = (
            f"{system_prompt}\n\n"
            f"=== {lang_hint}，请参考这些知识来回答问题 ===\n\n"
            f"{context}\n\n"
            f"=== 知识参考结束 ===\n\n"
            f"请基于以上专业知识回答问题。如果知识与问题不相关，请如实说明。"
        )
    else:
        augmented_system = system_prompt

    ds = get_deepseek()
    return ds._chat(augmented_system, user_message, json_mode=json_mode)
