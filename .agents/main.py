"""Top-level CLI entry point under .agents."""

import sys
from pathlib import Path

# Add .agents, src, and project root to sys.path
agents_dir = Path(__file__).resolve().parent
project_root = agents_dir.parent
src_dir = project_root / "src"

for d in [str(agents_dir), str(src_dir), str(project_root)]:
    if d not in sys.path:
        sys.path.insert(0, d)

from assign_reviewers import assign_reviewers, main

if __name__ == "__main__":
    main()
