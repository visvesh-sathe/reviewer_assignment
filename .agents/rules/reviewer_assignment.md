---
trigger: always_on
description: Instructions for running reviewer assignment through .agents caller script
---

# Reviewer Assignment Execution Guidelines

1. **Source Code Location**: All implementation modules and packages are organized under `src/` (`src/reviewer_assignment`, `src/extract_affiliations.py`, `src/generate_coi_matrix.py`).
2. **Caller Script**: The primary caller script and function is located in `.agents/assign_reviewers.py` (and `.agents/main.py`).
3. **Execution**: Whenever the user asks to assign reviewers, execute:
   ```bash
   python3 .agents/assign_reviewers.py --config input_files/config.yaml
   ```
4. **Imports**: The `.agents/` scripts automatically resolve `src/` into `sys.path`.
