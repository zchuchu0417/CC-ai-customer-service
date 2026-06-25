"""知识库灌库脚本

读取 data/knowledge/ 下所有 .md 文件，执行：
  ① 切分（按 ~400 字 + 50 字重叠）
  ② Embedding（调硅基流动 bge-m3 API）
  ③ 存 Qdrant（vector + payload）
  ④ 存 MySQL doc_chunks（content + metadata）

用法（在 backend/ 目录，激活 venv 后）：
    python scripts/ingest.py                  # 增量灌库（已灌的跳过）
    python scripts/ingest.py --reset          # 清空所有知识库重灌
"""
import argparse
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client.http import models as qdrant_models
from sqlalchemy.orm import Session as DbSession

from app.db.base import SessionLocal
from app.db.qdrant import qdrant_client
from app.models import KnowledgeDoc, DocChunk
from app.services.embedding_client import embedding_client, EMBEDDING_DIMENSIONS


# ============ 配置 ============
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "data" / "knowledge"
COLLECTION_NAME = "cc_knowledge"
CHUNK_SIZE = 400      # 每块约 400 字
CHUNK_OVERLAP = 50    # 相邻块重叠 50 字（保上下文连贯）

# 根据文件名前缀映射分类（粗暴但够用）
CATEGORY_MAP = {
    "售后": "退换货",
    "物流": "物流",
    "优惠": "优惠券",
    "会员": "会员",
    "商品": "商品",
    "客服": "客服",
    "发票": "发票",
    "价格": "价保",
    "退款": "退款",
    "评价": "评价",
    "账户": "账户",
}


# ============ 工具函数 ============
def detect_category(filename: str) -> str:
    """从文件名识别分类"""
    for key, cat in CATEGORY_MAP.items():
        if key in filename:
            return cat
    return "其他"


def chunk_markdown(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """切分 markdown 文档

    策略：先按 H1/H2 标题分段（保持语义完整），如果段落仍过长再按字符数切。

    Returns:
        [{"content": "...", "section": "一、xxx"}, ...]
    """
    # 按 H2 标题（## ）分段
    sections = re.split(r'\n(?=## )', text)

    chunks = []
    for section in sections:
        if not section.strip():
            continue

        # 提取 section 标题
        title_match = re.match(r'^#+\s*(.+)$', section.split('\n')[0])
        section_title = title_match.group(1) if title_match else None

        # 如果 section 短于 chunk_size，整段一个 chunk
        if len(section) <= chunk_size:
            chunks.append({"content": section.strip(), "section": section_title})
            continue

        # 太长 → 按字符数滑动切分
        start = 0
        while start < len(section):
            end = start + chunk_size
            chunk_text = section[start:end].strip()
            if chunk_text:
                chunks.append({"content": chunk_text, "section": section_title})
            start += chunk_size - overlap

    return chunks


# ============ Qdrant Collection 管理 ============
def ensure_collection():
    """确保 Qdrant 里有 cc_knowledge collection"""
    collections = qdrant_client.get_collections().collections
    names = [c.name for c in collections]
    if COLLECTION_NAME not in names:
        print(f"📦 创建 Qdrant collection: {COLLECTION_NAME}")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_models.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
    else:
        print(f"✓ Qdrant collection 已存在: {COLLECTION_NAME}")


def reset_all(db: DbSession):
    """清空知识库（MySQL + Qdrant）"""
    print("⚠️  清空所有知识库数据...")
    db.query(DocChunk).delete()
    db.query(KnowledgeDoc).delete()
    db.commit()
    try:
        qdrant_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    print("✓ 已清空")


# ============ 主流程 ============
def ingest_file(db: DbSession, file_path: Path) -> int:
    """灌库单个文件，返回新增 chunk 数"""
    filename = file_path.name

    # 跳过已灌
    existing = db.query(KnowledgeDoc).filter(
        KnowledgeDoc.source_path == str(file_path)
    ).first()
    if existing:
        print(f"  ⏭  跳过已灌: {filename}")
        return 0

    text = file_path.read_text(encoding="utf-8")
    chunks = chunk_markdown(text)
    if not chunks:
        print(f"  ⚠ 空文件，跳过: {filename}")
        return 0

    # 1. 写 knowledge_docs
    title_match = re.match(r'^#\s*(.+)$', text.strip().split('\n')[0])
    title = title_match.group(1) if title_match else filename

    doc = KnowledgeDoc(
        title=title,
        source_path=str(file_path),
        category=detect_category(filename),
        version="v1.0",
        chunk_count=len(chunks),
        total_chars=len(text),
    )
    db.add(doc)
    db.flush()  # 拿到 doc.id

    # 2. 批量 embedding（一次 API 调用搞定一个文档的所有 chunks）
    contents = [c["content"] for c in chunks]
    print(f"  🔄 调用 embedding API（{len(contents)} 段）...")
    vectors = embedding_client.embed_batch(contents)

    # 3. 准备 Qdrant points + MySQL chunks
    points = []
    chunk_rows = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        point_id = str(uuid.uuid4())
        points.append(qdrant_models.PointStruct(
            id=point_id,
            vector=vec,
            payload={
                "doc_id": doc.id,
                "chunk_index": i,
                "title": title,
                "category": doc.category,
                "section": chunk["section"],
                "content": chunk["content"],
            },
        ))
        chunk_rows.append(DocChunk(
            doc_id=doc.id,
            chunk_index=i,
            content=chunk["content"],
            chunk_size=len(chunk["content"]),
            section=chunk["section"],
            vector_id=point_id,
        ))

    # 4. 批量写
    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
    db.add_all(chunk_rows)
    db.commit()

    print(f"  ✅ {filename}: {len(chunks)} chunks 已入库")
    return len(chunks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="清空所有知识库重灌")
    args = parser.parse_args()

    print(f"📂 知识库目录: {KNOWLEDGE_DIR}")
    print()

    db = SessionLocal()
    try:
        if args.reset:
            reset_all(db)

        ensure_collection()

        md_files = sorted(KNOWLEDGE_DIR.glob("*.md"))
        if not md_files:
            print(f"❌ {KNOWLEDGE_DIR} 下没有 .md 文件")
            return

        print(f"📚 发现 {len(md_files)} 个文件：")
        for f in md_files:
            print(f"   - {f.name}")
        print()

        start = time.time()
        total_chunks = 0
        for file_path in md_files:
            chunks_added = ingest_file(db, file_path)
            total_chunks += chunks_added

        elapsed = time.time() - start

        # 汇总
        total_docs = db.query(KnowledgeDoc).count()
        total_db_chunks = db.query(DocChunk).count()
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)

        print()
        print("=" * 50)
        print("🎉 灌库完成！")
        print(f"   本次新增 chunks: {total_chunks}")
        print(f"   总文档数: {total_docs}")
        print(f"   总切片数 (MySQL): {total_db_chunks}")
        print(f"   总向量数 (Qdrant): {collection_info.points_count}")
        print(f"   耗时: {elapsed:.1f}s")
    finally:
        db.close()


if __name__ == "__main__":
    main()
