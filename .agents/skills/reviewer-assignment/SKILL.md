---
name: reviewer-assignment
description: >-
  Solves the reviewer assignment optimization problem using Mixed-Integer Linear Programming (MILP).
  Maximizes expertise matching scores, enforces workload limits, minimum paper coverage,
  COI exclusions, and appoints balanced champions and co-champions (excluding Chair/Co-Chair).
  Generates summary reports, histograms, and output matrices. Use when the user asks to assign
  reviewers, optimize assignments, run the reviewer assignment pipeline, or inspect reviewer workloads.
---

# Reviewer Assignment Optimizer

This skill guides the agent in executing the Mixed-Integer Linear Program (MILP) optimization pipeline for assigning reviewers to academic papers, appointing paper champions/co-champions, and generating analytical reports.

---

## Workflow Overview

```
input_files/config.yaml
input_files/reviewer_expertise.csv
input_files/paper_technical_areas.csv
input_files/must_review.csv
input_files/coi.csv
          │
          ▼
.agents/assign_reviewers.py (Caller Script)
          │
          ├──► Stage 1: Solve Base Reviewer Assignment MILP
          │      └──► Maximize expertise match subject to workload, coverage, COI, & must-review
          │
          ├──► Stage 2: Solve Champion Assignment MILP
          │      └──► 1 champ/paper from assigned reviewers, exclude Chair/Co-Chair, balance champ workload
          │
          ├──► Stage 3: Solve Co-Champion Assignment MILP
          │      └──► 1 co-champ/paper from other reviewers, exclude Chair/Co-Chair, balance co-champ workload
          │
          └──► Stage 4: Reporting & Visualization
                 ├──► output_files/paper_assignment.csv (Flat Assignments)
                 ├──► output_files/reviewer_assignment_matrix.csv
                 ├──► output_files/champ_assignment_matrix.csv
                 ├──► output_files/cochamp_assignment_matrix.csv
                 ├──► output_files/assignment_vector.csv
                 ├──► reports/summary_report.txt (Text Summary)
                 └──► reports/*.png (Workload & Coverage Distribution Histograms)
```

---

## Execution Command

Always execute the top-level calling script located in `.agents/`:

```bash
python3 .agents/assign_reviewers.py --config input_files/config.yaml
```

### Python Programmatic Call:
```python
import sys
sys.path.insert(0, ".agents")
from assign_reviewers import assign_reviewers

results = assign_reviewers(config_path="input_files/config.yaml")
```

---

## Input Prerequisites Checklist

Before executing, verify the following files exist in `input_files/`:
1. **`config.yaml`**: Run configuration (`num_reviewers`, `num_papers`, `min/max_reviews_per_reviewer`, `min_reviews_per_paper`, `chair`, `cochair`, and file paths).
2. **`reviewer_expertise.csv`**: Reviewer names (`Firstname`, `Lastname`), `Affiliation`, and scores (`0` to `10`) across technical areas.
3. **`paper_technical_areas.csv`**: Paper IDs, titles, and populated relevance scores (`0` to `10`) across matching technical areas.
4. **`must_review.csv`**: Binary matrix ($N_{papers} \times N_{reviewers}$) specifying mandatory reviewer assignments (`1` = forced, `0` = optional).
5. **`coi.csv`**: Binary matrix ($N_{papers} \times N_{reviewers}$) specifying conflict of interest restrictions (`1` = conflict / forbidden, `0` = allowed).

---

## Optimization Stages

### 1. Base Reviewer Assignment Solve
- **Objective**: Maximize $\sum_{r,p} S_{r,p} \cdot X_{r,p}$, where $S = \text{Reviewer Expertise} \times \text{Paper Area}^T$.
- **Hard Constraints**:
  - $X_{r,p} = 0$ if $\text{COI}[r,p] = 1$.
  - $X_{r,p} = 1$ if $\text{MustReview}[r,p] = 1$.
  - $\text{min\_reviews\_per\_reviewer} \le \sum_p X_{r,p} \le \text{max\_reviews\_per\_reviewer}$ for each reviewer.
  - $\sum_r X_{r,p} \ge \text{min\_reviews\_per\_paper}$ for each paper.

### 2. Champion Selection Solve
- Selects exactly one reviewer per paper to serve as the **Champion**.
- Candidate must be an assigned reviewer ($X_{r,p} = 1$).
- Chair and Co-Chair are strictly excluded (assigned `0` champions).
- Champion workload is constrained between $\lfloor N_p / N_r \rfloor - 1$ and $\lceil N_p / N_r \rceil + 1$.

### 3. Co-Champion Selection Solve
- Selects exactly one other reviewer per paper to serve as the **Co-Champion**.
- Candidate must be an assigned reviewer ($X_{r,p} = 1$) and NOT the paper's Champion.
- Chair and Co-Chair are strictly excluded (assigned `0` co-champions).
- Co-Champion workload is constrained $\le \lceil N_p / N_r \rceil + 1$.

---

## Output Artifacts & Reporting

After execution, inspect the following generated files:
- **`reports/summary_report.txt`**: Complete audit breakdown of total assignments, reviewer workloads, paper review counts, champion/co-champion distribution, and detailed reviewer-to-paper mappings.
- **`reports/reviewer_roles_breakdown.png`**: Stacked bar chart showing Champion vs. Co-Champion vs. Regular Reviewer distribution per reviewer.
- **`reports/reviewer_workload_histogram.png`**: Reviewer workload distribution chart.
- **`reports/paper_reviews_histogram.png`**: Paper coverage chart.
- **`output_files/paper_assignment.csv`**: Flat CSV list of `reviewer_id` and `paper_id` pairs.
- **`output_files/reviewer_assignment_matrix.csv`**: Full binary assignment matrix ($N_{reviewers} \times N_{papers}$).
- **`output_files/champ_assignment_matrix.csv`**: Full binary champion matrix ($N_{reviewers} \times N_{papers}$).
- **`output_files/cochamp_assignment_matrix.csv`**: Full binary co-champion matrix ($N_{reviewers} \times N_{papers}$).
- **`output_files/assignment_vector.csv`**: Flattened assignment vector.

---

## Post-Execution Verification Checklist

1. Check that the solver returned status **Optimal** and reported positive objective scores for all three solves.
2. Confirm that every paper has at least `min_reviews_per_paper` reviews.
3. Confirm that every paper has exactly 1 Champion and 1 Co-Champion.
4. Confirm that the Chair and Co-Chair have 0 Champion and 0 Co-Champion assignments.
5. Verify that no assigned reviewer has a conflict of interest with their assigned paper.
