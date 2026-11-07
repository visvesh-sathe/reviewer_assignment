# 📑 Automated Reviewer Assignment & Conflict of Interest (COI) Solver

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/coi_gen_and_reviewer_allocation/reviewer_assignment_colab.ipynb)

A Python and Mixed-Integer Linear Programming (MILP) tool designed for academic conferences and peer-review committees. It automates:
1. **Conflict of Interest (COI) Detection:** Extracts author affiliations from manuscript submissions and matches them against reviewer institutional affiliations to produce audit reports and an editable COI matrix.
2. **Reviewer & Champion Assignment Optimization:** Uses the `pulp` MILP solver to maximize expertise matching, strictly enforce paper coverage (min/max reviews per paper), balance reviewer workloads, and appoint balanced **Champions** and **Co-Champions** (excluding the Chair/Co-Chair).

---

## 🚀 Running via Google Colab (Interactive Web UI)

Click the badge above or use the interactive notebook located at [`coi_gen_and_reviewer_allocation/reviewer_assignment_colab.ipynb`](coi_gen_and_reviewer_allocation/reviewer_assignment_colab.ipynb).

### 7-Step Interactive Workflow
1. **Install Dependencies & Setup:** Automatically sets up the `pulp` MILP solver and workspace.
2. **Upload Input Files:** Dedicated upload buttons for your conference CSV files (Expertise, Paper Submissions, Technical Areas, Must-Review constraints).
3. **Run COI Flow:** Generates the institutional conflict matrix and displays the audit report inline.
4. **Download COI Matrix:** Downloads `cfg_coi.csv` to your computer for manual inspection in Excel/Google Sheets.
5. **Upload Updated COI:** Uploads your refined conflict matrix back to the solver.
6. **Solve Reviewer Allocations:** Runs the mathematical optimization to assign reviewers, champions, and co-champions.
7. **Visualizations & Deliverables:** Displays distribution histograms inline and downloads `reviewer_assignment_results.zip`.

---

## 💻 Running Locally

### 1. Prerequisites
Install the required dependencies:
```bash
python3 -m pip install pulp pyyaml pandas matplotlib
```

### 2. Standalone Wrapper Flow (Simple)
Navigate to `coi_gen_and_reviewer_allocation` and run:
```bash
cd coi_gen_and_reviewer_allocation

# Step 1: Generate COI Matrix
python3 coi_generation.py

# Step 2: (Optional) Review/Edit input_files/cfg_coi.csv

# Step 3: Run Reviewer Allocation
python3 reviewer_allocation.py
```

### 3. Pipeline via Agent CLI
From the project root:
```bash
python3 .agents/assign_reviewers.py --config input_files/config.yaml
```

---

## 📁 Repository Structure

```
├── coi_gen_and_reviewer_allocation/
│   ├── reviewer_assignment_colab.ipynb  # Interactive Colab Notebook
│   ├── coi_generation.py                # COI extraction & audit runner
│   ├── reviewer_allocation.py           # MILP allocation solver runner
│   ├── input_files/                     # Active conference inputs
│   ├── intermediate_files/              # Cleaned affiliations & area maps
│   └── output_files/                    # Deliverable CSV matrices & charts
├── src/
│   ├── reviewer_assignment/             # Core mathematical solver & reporter
│   ├── extract_affiliations.py          # Affiliation parser
│   └── generate_coi_matrix.py           # Cross-matching COI logic
├── .agents/                             # Agent caller scripts & CLI entries
└── reports/                             # Generated summaries and histograms
```
