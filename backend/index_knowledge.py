"""
知识库索引构建工具

用法:
    python index_knowledge.py /path/to/veterinary.pdf
    python index_knowledge.py /path/to/veterinary.pdf --force
    python index_knowledge.py --stats
    python index_knowledge.py --query "犬细小病毒症状"
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.rag_service import VetKnowledgeBase, get_knowledge_base
from config import Config


def cmd_index(args):
    pdf_path = args.pdf
    if not os.path.exists(pdf_path):
        print(f"错误: 文件不存在 - {pdf_path}")
        sys.exit(1)

    kb = VetKnowledgeBase()

    if kb.is_ready and not args.force:
        print("知识库索引已存在，使用 --force 强制重建")
        print(f"索引路径: {kb._get_index_path()}")
        return

    if kb.is_ready and args.force:
        print("正在删除旧索引...")
        for f in [kb._get_index_path(), kb._get_chunks_path(),
                  kb._get_meta_path(), kb._get_kwindex_path()]:
            if os.path.exists(f):
                os.remove(f)

    print(f"开始构建知识库索引...")
    print(f"PDF 文件: {pdf_path}")
    print(f"Embedding 模型: {kb.embedding_model_name}")
    print(f"Chunk 大小: {kb.chunk_size} 字符")
    print(f"索引存储: {kb.data_dir}")
    print()

    def progress(msg_type, msg):
        if msg_type == "step":
            print(f"  → {msg}")

    result = kb.build_index(pdf_path, progress_callback=progress)

    if "error" in result:
        print(f"\n构建失败: {result['error']}")
        sys.exit(1)

    print()
    print("=" * 50)
    print("索引构建成功!")
    print(f"  总页数: {result['pages']}")
    print(f"  文本块数: {result['chunks']}")
    print(f"  向量维度: {result['embedding_dim']}")
    print(f"  索引路径: {result['index_path']}")
    print("=" * 50)


def cmd_stats(args):
    kb = get_knowledge_base()
    stats = kb.get_stats()
    print("知识库状态:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


def cmd_query(args):
    query = args.query
    kb = get_knowledge_base()

    if not kb.is_ready:
        print("知识库未构建，请先运行: python index_knowledge.py <pdf_path>")
        sys.exit(1)

    if not kb._chunks:
        kb.load()

    top_k = args.top_k or 5
    results = kb.search(query, top_k=top_k)

    if not results:
        print(f"未找到与「{query}」相关的内容")
        return

    print(f"查询: {query}")
    print(f"找到 {len(results)} 条结果:\n")

    for i, r in enumerate(results):
        print(f"--- 结果 {i + 1} (相似度: {r['score']}, 第{r['page']}页) ---")
        if r['title']:
            print(f"  章节: {r['title']}")
        preview = r['text'][:300].replace('\n', ' ')
        print(f"  内容: {preview}...")
        print()


def main():
    parser = argparse.ArgumentParser(description="兽医知识库索引工具")
    subparsers = parser.add_subparsers(dest="command")

    index_parser = subparsers.add_parser("index", help="构建知识库索引")
    index_parser.add_argument("pdf", help="PDF 文件路径")
    index_parser.add_argument("--force", action="store_true", help="强制重建索引")

    subparsers.add_parser("stats", help="查看知识库状态")

    query_parser = subparsers.add_parser("query", help="检索知识库")
    query_parser.add_argument("query", help="检索关键词/问题")
    query_parser.add_argument("--top-k", type=int, default=5, help="返回结果数")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "query":
        cmd_query(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
