"""一键建表脚本

用法（在 backend/ 目录，激活 venv 后）：
    python scripts/init_db.py

效果：在 MySQL cc_ai_cs 库下创建 4 张表（users/sessions/messages/feedback）。
重复执行不会重建已存在的表（用 create_all 的 IF NOT EXISTS 语义）。
"""
import sys
from pathlib import Path

# 把 backend/ 加入 import 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import Base
from app.db.mysql import engine
from app import models  # noqa: F401  必须 import 才能让 Base 发现所有模型


def main():
    print("📊 创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 完成！可以在 Adminer 查看")
    print()
    print("已创建的表：")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


if __name__ == "__main__":
    main()