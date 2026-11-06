# Agent Instructions for Reviewer Assignment

## Project Structure
- All core Python modules, utilities, and packages reside in the `src/` directory (e.g. `src/reviewer_assignment/`, `src/extract_affiliations.py`, `src/generate_coi_matrix.py`).
- The top-level caller function and execution script resides in the `.agents/` directory (`.agents/assign_reviewers.py` and `.agents/main.py`).

## Reviewer Assignment Execution
When requested to assign reviewers, optimize assignments, or run the reviewer assignment pipeline:
- Always run the top-level calling script from the `.agents/` directory:
  ```bash
  python3 .agents/assign_reviewers.py --config input_files/config.yaml
  ```
  Or from Python:
  ```python
  from .agents.assign_reviewers import assign_reviewers
  assign_reviewers(config_path="input_files/config.yaml")
  ```

## Accessing Source Modules
Scripts in `.agents/` automatically configure `sys.path` to include `src/`, allowing full access to all `reviewer_assignment` packages and submodules:
```python
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import reviewer_assignment
```

## Available Workspace Skills
- [`coi-matrix-generation`](file:///Users/vsathe7/v/git_repos/python/reviewer_assignment/skills/coi-matrix-generation/SKILL.md): Extracts affiliations and builds the Conflict of Interest (COI) matrix and audit reports.
- [`reviewer-assignment`](file:///Users/vsathe7/v/git_repos/python/reviewer_assignment/skills/reviewer-assignment/SKILL.md): Executes the MILP optimization pipeline to assign reviewers, appoint champions/co-champions, and generate reporting visualizations.

