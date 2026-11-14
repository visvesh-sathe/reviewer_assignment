# CICC Reviewer Assignment & Conflict of Interest (COI) Automation Guide

This guide details the complete end-to-end automated pipeline for generating Conflict of Interest (COI) matrices and optimizing reviewer assignments for conference subcommittees (such as IEEE CICC).

The system is decoupled into two modular, independent workflows:
1. **[`coi_generator`](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/coi_generator/coi_generator.ipynb):** Extracts institutional affiliations from raw submission sheets, strips author metadata for double-blind compliance, and evaluates COIs using a local LLM (**Ollama `qwen2.5:7b`**) with zero external API keys or logins.
2. **[`reviewer_assignment`](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/reviewer_assignment/reviewer_assignment_colab.ipynb):** Solves the Mixed-Integer Linear Programming (MILP) assignment problem, appointing balanced Champions and Co-Champions, and generating the populated deliverable spreadsheet (`final_reviewer_assignment_sheet.xls`).

---

## 🚀 Quick Access Links

| Workflow | Google Colab Link | GitHub Documentation | Local Directory |
| :--- | :--- | :--- | :--- |
| **1. COI Generation** | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/coi_generator/coi_generator.ipynb) | [README.md](coi_generator/README.md) | `coi_generator/` |
| **2. Reviewer Assignment** | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/reviewer_assignment/reviewer_assignment_colab.ipynb) | [README.md](reviewer_assignment/README.md) | `reviewer_assignment/` |

---

## 🏛️ Phase 1: Conflict of Interest (COI) Generation Flow

*Colab Notebook:* **[`coi_generator/coi_generator.ipynb`](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/coi_generator/coi_generator.ipynb)**

### Why Use a Local LLM (`qwen2.5:7b`)?
Conference submission sheets frequently contain abbreviations, acronyms, or alternate names for universities and companies (e.g., **UIUC** ↔ *University of Illinois Urbana-Champaign*, **MIT** ↔ *Massachusetts Institute of Technology*, **GT** ↔ *Georgia Tech*, **Intel Labs** ↔ *Intel*, **Samsung SAIT** ↔ *Samsung Electronics*). Standard Python substring comparisons often miss these. Running `qwen2.5:7b` locally in Ollama on a free T4 GPU ensures high-accuracy institutional reasoning with zero cloud data sharing and zero API key setup.

### Step-by-Step Flow:
1. **GPU Runtime Setup:**
   - In Colab, go to **Runtime ➔ Change runtime type ➔ T4 GPU**.
2. **Setup Cell:**
   - Automatically installs `zstd` and Ollama, starts the `ollama serve` background daemon, and downloads the `qwen2.5:7b` model (~1–2 minutes).
3. **Step 1: Download Reviewer Expertise Template:**
   - Click the play button to download `cfg_reviewer_expertise.csv` to your computer.
4. **Step 2: Upload Edited Reviewer Expertise:**
   - Upload your committee's filled reviewer CSV with their affiliations and expertise ratings.
5. **Step 3: Upload Submitted Paper Information:**
   - Upload the raw conference submission export (`cfg_paper_info.csv`) containing author names and affiliations.
6. **Step 4: Extract & Scrub Paper Affiliations (Python):**
   - Automatically scrubs author names and paper titles (preserving double-blind integrity) and filters out noisy role labels (e.g., `"Student"` / `"Professor"`), producing `intermediate_files/paper_id_and_affiliations.csv`.
7. **Step 5: Run `affiliation-matcher` Skill & Download Deliverables:**
   - Executes the `affiliation-matcher` skill headlessly against local Ollama (`http://localhost:11434/v1`) using `qwen2.5:7b`.
   - Generates the binary COI matrix (`output_files/cfg_coi.csv`) and itemized audit report (`output_files/coi_report.txt`).
   - Automatically downloads `cfg_coi.csv` and `coi_report.txt` directly to your browser.

---

## 📑 Phase 2: Reviewer Assignment Optimization Flow

*Colab Notebook:* **[`reviewer_assignment/reviewer_assignment_colab.ipynb`](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/reviewer_assignment/reviewer_assignment_colab.ipynb)**

### Key Optimization Features:
- **Expertise Maximization:** Optimizes total matching scores based on paper technical areas and reviewer expertise.
- **Strict Paper Coverage:** Every paper receives exactly `reviews_per_paper` reviews.
- **Fair Workload Balancing:** Balances reviewer workloads strictly between fair mathematical floor and ceiling:
  $$\text{min\_reviews} = \left\lfloor \frac{\text{num\_papers} \times \text{reviews\_per\_paper}}{\text{num\_reviewers}} \right\rfloor$$
  $$\text{max\_reviews} = \text{min\_reviews} + \text{max\_extra\_reviews}$$
- **COI Exclusions:** Guarantees zero reviewer assignments where $\text{COI} = 1$.
- **Must-Review Assignments:** Guarantees all assignments where $\text{MustReview} = 1$.
- **Leadership Roles:** Automatically appoints balanced **Champions** and **Co-Champions** for every paper across non-chair committee members ($\lfloor N/K \rfloor$ to $\lfloor N/K \rfloor + 1$).
- **Deliverable Excel Sheet:** Populates `final_reviewer_assignment_sheet.xls` with all reviewers in columns C–S in order, Champion shaded in **Green**, Co-Champion in **Yellow**, unassigned marked as `'x'`, and dynamic `=COUNTIF()` formulas.

### Step-by-Step Flow:
1. **Step 1: Install Dependencies & Setup Workspace:**
   - Installs optimization dependencies (`pulp<4.0`, `openpyxl`, `pandas`, `pyyaml`, `matplotlib`).
2. **Step 2: Reference Templates & Input Files Panel:**
   - **Part A (Download Templates First):** Click **Download All Templates (.ZIP)** to download all blank templates (`paper_area`, `reviewer_expertise`, `must_review`, `config.yaml`, and deliverable sheet template).
   - **Part B (Upload Files):** Upload your completed files, including the `cfg_coi.csv` matrix generated in Phase 1.
3. **Step 3: Execute Reviewer Allocation Flow (MILP Optimizer):**
   - Adjust `reviews_per_paper` (e.g. 6 or 8) and `max_extra_reviews` (default: 2) in the interactive form.
   - Solves the assignment, champion, and co-champion MILPs in seconds.
4. **Step 4: View Visualizations & Download Deliverables:**
   - Renders 5 workload and role distribution plots inline.
   - Displays a preview of `summary_report.txt`.
   - Automatically downloads the final deliverable spreadsheet (`final_reviewer_assignment_sheet.xls`) and the full archive (`reviewer_assignment_results.zip`).

---

## 📊 Summary of Input & Output Files

### Inputs
| File Name | Purpose | Prepared By |
| :--- | :--- | :--- |
| `cfg_paper_info.csv` | Raw paper submission sheet (authors & affiliations) | Conference portal export (used in Phase 1) |
| `cfg_reviewer_expertise.csv` | Committee reviewer names, affiliations, expertise ratings | Download template in Phase 1 or Phase 2 |
| `cfg_paper_area.csv` | Paper technical area relevance scores | Download template in Phase 2 |
| `cfg_coi.csv` | Binary Conflict of Interest matrix | **Generated by Phase 1 (`coi_generator`)** |
| `cfg_must_review.csv` | Mandatory reviewer assignments (optional) | Download template in Phase 2 |
| `cfg_config.yaml` | Committee chair/co-chair, paper counts, review targets | Download template in Phase 2 |
| `cfg_assignment_sheet_deliverable_template.xls` | Excel template with layout and formula formatting | Provided in repository |

### Outputs
| File Name | Description | Generated By |
| :--- | :--- | :--- |
| `cfg_coi.csv` | Binary COI matrix ($N_{\text{papers}} \times N_{\text{reviewers}}$) | Phase 1 (`coi_generator`) |
| `coi_report.txt` | Itemized audit report with reasoning for each conflict | Phase 1 (`coi_generator`) |
| `final_reviewer_assignment_sheet.xls` | Final Excel deliverable with color-coded assignments & formulas | Phase 2 (`reviewer_assignment`) |
| `reviewer_assignment_matrix.csv` | Binary review assignment matrix | Phase 2 (`reviewer_assignment`) |
| `champ_assignment_matrix.csv` | Binary champion assignment matrix | Phase 2 (`reviewer_assignment`) |
| `cochamp_assignment_matrix.csv` | Binary co-champion assignment matrix | Phase 2 (`reviewer_assignment`) |
| `assignment_vector.csv` | Flat paper-to-reviewer assignment vector | Phase 2 (`reviewer_assignment`) |
| `paper_assignment.csv` | Table of all papers with assigned reviewers & champions | Phase 2 (`reviewer_assignment`) |
| `summary_report.txt` | Comprehensive workload and role balance report | Phase 2 (`reviewer_assignment`) |
| Workload PNGs | 5 distribution histograms and role breakdowns | Phase 2 (`reviewer_assignment`) |

---

## 💻 Standalone Local CLI Execution

Both flows can also be executed directly on a local workstation:

### Running COI Generation Locally:
```bash
cd coi_generator

# Run full flow with local Ollama:
python3 coi_generation.py --base-url "http://localhost:11434/v1" --model "qwen2.5:7b"

# Or run with heuristic fallback (no model):
python3 coi_generation.py
```

### Running Reviewer Assignment Locally:
```bash
cd reviewer_assignment

# Run optimizer with default configuration:
python3 reviewer_allocation.py

# Run with custom review workload overrides:
python3 reviewer_allocation.py --reviews-per-paper 6 --max-extra-reviews 2
```
