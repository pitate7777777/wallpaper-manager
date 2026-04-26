"""pytest 配置 — 确保项目根目录在 sys.path 中"""
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保 core 包可导入
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
