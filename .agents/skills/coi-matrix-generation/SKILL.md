---
name: coi-matrix-generation
description: >-
  Extracts paper author affiliations from submitted papers and generates the Conflict
  of Interest (COI) matrix and audit reports by matching reviewer affiliations against
  paper affiliations. Use when the user asks to extract affiliations, generate/build
  the COI matrix, check conflicts of interest, or audit institutional COIs.
---

# Conflict of Interest (COI) Matrix & Affiliation Extraction

This skill guides the agent through extracting paper author affiliations and computing the Conflict of Interest (COI) matrix for reviewer assignment.

---

## Workflow Overview

```
input_files/paper_info.csv (Submitted Papers & Author Affiliations)
input_files/reviewer_expertise.csv (Reviewers & Reviewer Affiliations)
          │
          ├──► Step 1: Scrub Paper Author Affiliations (src/extract_affiliations.py)
          │      └──► output_files/intermediate_data/paper_id_and_affiliations.csv
          │
          └──► Step 2: Generate Conflict of Interest (COI) Matrix (src/generate_coi_matrix.py)
                 ├──► output_files/coi.csv (Binary COI Matrix)
                 └──► reports/coi_report.txt (Audit Trail & Conflict Report)
```

---

## Step 1: Scrub Paper Author Affiliations

Run the affiliation extraction script:
```bash
python3 src/extract_affiliations.py --config input_files/config.yaml
```

### What this does:
- **Double-Blind Affiliation Scrubbing**: Extracts `paper_id` and `affiliations` from `paper_info.csv` (removing author names and paper titles) and saves the scrubbed mapping to `output_files/intermediate_data/paper_id_and_affiliations.csv`.

---

## Step 2: Generate the Conflict of Interest (COI) Matrix

Run the COI matrix generator:
```bash
python3 src/generate_coi_matrix.py --config input_files/config.yaml
```

### COI Matching Rules:
- A conflict exists when a reviewer's affiliation matches any author affiliation of a paper.
- Matching handles normalized and partial string comparisons (e.g. `Intel` matches `Intel Corporation`, `MIT` matches `Massachusetts Institute of Technology`).
- Reviewer affiliations are read directly from the `Affiliation` column of `reviewer_expertise.csv`.

### Output Files Generated:
- **`output_files/coi.csv`**: A binary matrix ($N_{papers} \times N_{reviewers}$) where `1` indicates an institutional conflict and `0` indicates no conflict.
- **`reports/coi_report.txt`**: A detailed report itemizing every identified conflict and the matching institution names.

---

## Step 3: Stage COI File for Optimization

Copy the generated COI matrix to `input_files/` for consumption by the assignment solver:
```bash
cp output_files/coi.csv input_files/coi.csv
```

---

## Verification & Sanity Checks

1. Verify that `output_files/coi.csv` row count matches `num_papers` and column count matches `num_reviewers` in `config.yaml`.
2. Inspect `reports/coi_report.txt` to review detected conflicts with the user.
3. If unsure about ambiguous institutional abbreviations, ask the user for confirmation before proceeding to optimization.
