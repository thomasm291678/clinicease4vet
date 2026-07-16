"""
知识库批量管道

英文知识库: 31个兽医章节PDF → 向量索引
中文知识库: DeepSeek翻译 → 向量索引

用法:
    python pipeline.py en      # 构建英文知识库
    python pipeline.py zh      # 翻译 + 构建中文知识库
    python pipeline.py both    # 先英文再中文
"""

import os
import sys
import glob
import time
import pickle
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PDF_SOURCE_DIR = r"data\pdf_source"
EN_DATA_DIR = os.path.join("data", "knowledge_base_en")
ZH_DATA_DIR = os.path.join("data", "knowledge_base_zh")
ZH_RAW_DIR = os.path.join("data", "zh_translated")
CHUNK_SIZE = 800
MAX_TRANSLATE_CHARS = 2000


def get_pdf_list():
    from pathlib import Path
    base = Path(PDF_SOURCE_DIR)
    pdfs = sorted(str(p) for p in base.rglob("*.pdf"))
    print(f"找到 {len(pdfs)} 个 PDF 文件")
    for p in pdfs:
        size_mb = os.path.getsize(p) / 1024 / 1024
        print(f"  {os.path.basename(p):<35s} {size_mb:.1f} MB")
    return pdfs


def build_english_kb(pdf_paths):
    from services.rag_service import VetKnowledgeBase
    from config import Config

    original_data_dir = Config.RAG_DATA_DIR
    Config.RAG_DATA_DIR = EN_DATA_DIR
    os.makedirs(EN_DATA_DIR, exist_ok=True)

    kb = VetKnowledgeBase()
    kb.data_dir = EN_DATA_DIR
    kb.chunk_size = CHUNK_SIZE

    def progress(msg_type, msg):
        if msg_type == "step":
            print(f"  → {msg}")

    print("\n构建英文知识库索引...")
    result = kb.build_index_from_multiple(pdf_paths, progress_callback=progress)

    if "error" in result:
        print(f"构建失败: {result['error']}")
        Config.RAG_DATA_DIR = original_data_dir
        return None

    print(f"\n英文知识库构建完成!")
    print(f"  文件数: {result['files']}")
    print(f"  总页数: {result['pages']}")
    print(f"  文本块: {result['chunks']}")
    print(f"  向量维度: {result['embedding_dim']}")
    print(f"  索引路径: {result['index_path']}")

    Config.RAG_DATA_DIR = original_data_dir
    return result


def extract_text_pages(pdf_path):
    import fitz
    pages = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) >= 80:
                pages.append({"page": page_num + 1, "text": text})
    doc.close()
    return pages


def smart_chunk(text, max_chars):
    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current = ""
    for sent in sentences:
        if not current:
            current = sent
        elif len(current) + len(sent) + 1 <= max_chars:
            current += " " + sent
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        if len(current) <= max_chars:
            chunks.append(current)
        else:
            for i in range(0, len(current), max_chars):
                chunks.append(current[i:i + max_chars])
    return chunks


def translate_chunk(ds, text, chunk_idx, total, filename):
    prompt = (
        "You are a professional veterinary medicine translator. "
        "Translate the following veterinary medicine textbook content into Simplified Chinese. "
        "Requirements:\n"
        "- Maintain all technical medical/veterinary terminology accuracy\n"
        "- Keep drug names, disease names, and anatomical terms precise\n"
        "- Preserve the original meaning and educational tone\n"
        "- Output ONLY the Chinese translation, no explanations\n\n"
        f"English text:\n{text}"
    )
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = ds._chat(prompt, f"Translate section {chunk_idx}/{total}")
            if result.startswith("[API错误]"):
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                print(f"  [失败] {filename} chunk {chunk_idx}: {result[:100]}")
                return text
            return result.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            return text
    return text


def build_chinese_kb(pdf_paths):
    from services.deepseek_service import get_deepseek
    from services.rag_service import VetKnowledgeBase
    from config import Config

    ds = get_deepseek()
    if not ds.is_configured():
        print("DeepSeek API 未配置")
        return None

    os.makedirs(ZH_RAW_DIR, exist_ok=True)

    total_pages = 0
    total_chunks = 0

    for file_idx, pdf_path in enumerate(pdf_paths):
        filename = os.path.basename(pdf_path)
        zh_txt_path = os.path.join(ZH_RAW_DIR, filename.rsplit(".", 1)[0] + ".txt")

        if os.path.exists(zh_txt_path):
            print(f"\n[{file_idx+1}/{len(pdf_paths)}] {filename} 已有翻译，跳过")
            with open(zh_txt_path, "r", encoding="utf-8") as f:
                translated = f.read()
            total_pages += 1
            total_chunks += translated.count("\n===CHUNK===\n") + 1
            continue

        print(f"\n[{file_idx+1}/{len(pdf_paths)}] {filename} 解析...")
        pages = extract_text_pages(pdf_path)
        print(f"  共 {len(pages)} 页有效文本")

        all_translated = []
        page_chunks_total = 0

        for page in pages:
            page_chunks = smart_chunk(page["text"], MAX_TRANSLATE_CHARS)
            page_chunks_total += len(page_chunks)

        chunk_count = 0
        for page in pages:
            page_chunks = smart_chunk(page["text"], MAX_TRANSLATE_CHARS)
            for ch in page_chunks:
                chunk_count += 1
                if chunk_count % 5 == 0 or chunk_count == 1:
                    print(f"  ……翻译 {chunk_count}/{page_chunks_total}", end="\r")

                translated = translate_chunk(
                    ds, ch, chunk_count, page_chunks_total, filename
                )
                all_translated.append(
                    f"[第{page['page']}页] {translated}"
                )
                time.sleep(0.3)

        full_translated = "\n===CHUNK===\n".join(all_translated)
        with open(zh_txt_path, "w", encoding="utf-8") as f:
            f.write(full_translated)

        total_pages += len(pages)
        total_chunks += page_chunks_total
        print(f"\n  ✓ {filename} 翻译完成 ({page_chunks_total} 段)")

    print(f"\n全部翻译完成! 共 {total_pages} 页, {total_chunks} 段")
    print(f"中文文本目录: {ZH_RAW_DIR}")

    print("\n构建中文知识库索引...")
    original_data_dir = Config.RAG_DATA_DIR
    Config.RAG_DATA_DIR = ZH_DATA_DIR
    os.makedirs(ZH_DATA_DIR, exist_ok=True)

    from services.rag_service import get_knowledge_base as get_en_kb
    kb_zh = VetKnowledgeBase()
    kb_zh.data_dir = ZH_DATA_DIR
    kb_zh.embedding_model_name = Config.RAG_EMBEDDING_MODEL
    kb_zh.chunk_size = CHUNK_SIZE

    zh_txt_files = sorted(glob.glob(os.path.join(ZH_RAW_DIR, "*.txt")))
    print(f"  中文文本文件: {len(zh_txt_files)} 个")

    zh_chunks = []
    zh_meta = []
    for txt_file in zh_txt_files:
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read()
        src_name = os.path.basename(txt_file).replace(".txt", ".pdf")
        sections = content.split("\n===CHUNK===\n")
        for i, section in enumerate(sections):
            section = section.strip()
            if len(section) < 40:
                continue
            page_match = re.search(r'\[第(\d+)页\]', section)
            page_num = int(page_match.group(1)) if page_match else 0
            zh_chunks.append(section)
            zh_meta.append({
                "id": len(zh_chunks) - 1,
                "page": page_num,
                "char_count": len(section),
                "title": "",
                "source": src_name,
            })

    print(f"  中文文本块: {len(zh_chunks)}")

    kb_zh._chunks = zh_chunks
    kb_zh._chunk_meta = zh_meta

    embeddings = kb_zh.embedding_model.encode(
        zh_chunks, show_progress_bar=False, normalize_embeddings=True
    )

    import faiss, pickle
    dim = embeddings.shape[1]
    kb_zh._index = faiss.IndexFlatIP(dim)
    kb_zh._index.add(embeddings.astype("float32"))

    os.makedirs(ZH_DATA_DIR, exist_ok=True)
    faiss.write_index(kb_zh._index, os.path.join(ZH_DATA_DIR, "faiss_index.bin"))
    with open(os.path.join(ZH_DATA_DIR, "chunks.pkl"), "wb") as f:
        pickle.dump(zh_chunks, f)
    with open(os.path.join(ZH_DATA_DIR, "chunk_meta.pkl"), "wb") as f:
        pickle.dump(zh_meta, f)

    kb_zh._build_keyword_index()
    with open(os.path.join(ZH_DATA_DIR, "keyword_index.pkl"), "wb") as f:
        pickle.dump(kb_zh._keyword_index, f)

    print(f"\n中文知识库构建完成!")
    print(f"  文件数: {len(zh_txt_files)}")
    print(f"  文本块: {len(zh_chunks)}")
    print(f"  向量维度: {dim}")
    print(f"  索引路径: {ZH_DATA_DIR}")

    Config.RAG_DATA_DIR = original_data_dir
    return {"chunks": len(zh_chunks), "dim": dim}


def main():
    if len(sys.argv) < 2:
        print("用法: python pipeline.py [en|zh|both]")
        sys.exit(1)

    mode = sys.argv[1]
    pdf_paths = get_pdf_list()
    if not pdf_paths:
        print("未找到 PDF 文件")
        sys.exit(1)

    if mode in ("en", "both"):
        build_english_kb(pdf_paths)

    if mode in ("zh", "both"):
        build_chinese_kb(pdf_paths)


if __name__ == "__main__":
    main()
