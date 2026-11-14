# Reviewer Assignment Optimization Flow (`reviewer_assignment`)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/visvesh-sathe/reviewer_assignment/blob/main/reviewer_assignment/reviewer_assignment_colab.ipynb)

A standalone workflow and Colab notebook to optimize academic peer review assignments using Mixed-Integer Linear Programming (MILP).

This directory focuses **exclusively on reviewer assignment optimization**. Conflict of Interest (COI) matrix generation from author affiliations is handled separately by the [`coi_generator`](../coi_generator/) module.

---

## 📋 Required Input Files (`input_files/`)

All required inputs reside in `input_files/`:

1. **`cfg_paper_area.csv`**: Paper technical area relevance scores ($N_{\text{papers}} \times N_{\text{areas}}$, scores 0–10).
2. **`cfg_reviewer_expertise.csv`**: Reviewer technical area expertise scores ($N_{\text{reviewers}} \times N_{\text{areas}}$, scores 0–10).
3. **`cfg_coi.csv`**: Institutional Conflict of Interest binary matrix ($N_{\text{papers}} \times N_{\text{reviewers}}$). *(Can be generated using `coi_generator`)*.
4. **`cfg_must_review.csv`**: Mandatory reviewer assignment constraints ($N_{\text{papers}} \times N_{\text{reviewers}}$).
5. **`cfg_config.yaml`**: Pipeline configuration specifying reviewer/paper counts, target `reviews_per_paper`, `max_extra_reviews`, and committee chair / co-chair names.
6. **`cfg_assignment_sheet_deliverable_template.xls`**: Formatted template spreadsheet for the final deliverable.

---

## 🚀 Optimization Features

- **Expertise Maximization:** Maximizes overall committee matching score:
  $$\text{Score} = \text{Expertise}_{\text{reviewer}} \times \text{Relevance}_{\text{paper}}^T$$
- **Coverage & Workload Balancing:** Strictly enforces paper review counts (`reviews_per_paper`) and balances reviewer load between fair floor and ceiling:
  $$\text{min\_reviews} = \left\lfloor \frac{\text{num\_papers} \times \text{reviews\_per\_paper}}{\text{num\_reviewers}} \right\rfloor$$
  $$\text{max\_reviews} = \text{min\_reviews} + \text{max\_extra\_reviews}$$
- **COI Exclusions:** Guarantees zero reviewer assignments where $\text{COI} = 1$.
- **Must-Review Assignments:** Guarantees all specified assignments where $\text{MustReview} = 1$.
- **Fair Leadership Appointments:** Appoints balanced **Champions** and **Co-Champions** for every paper across non-chair reviewers (workload within $\lfloor N/K \rfloor$ and $\lfloor N/K \rfloor + 1$).
- **Deliverable Spreadsheet:** Generates `final_reviewer_assignment_sheet.xls` listing all reviewers across columns C–S in order, with:
  - `1` for assigned papers (shaded **Green** for Champion, **Yellow** for Co-Champion, white for regular reviewers).
  - `'x'` for non-assigned reviewers.
  - Formula counts for `# of Walkouts` and `# of Reviews`.
  - Reviewer summary rows at the bottom (total reviews, walkouts, champions, co-champions, committee roles).

---

## 💻 Local CLI Execution

Run the optimizer from terminal:

```bash
cd reviewer_assignment

# Run with default configuration:
python3 reviewer_allocation.py

# Run with custom parameters:
python3 reviewer_allocation.py --reviews-per-paper 8 --max-extra-reviews 2
```

---

## 📊 Outputs Generated (`output_files/`)

- **`final_reviewer_assignment_sheet.xls`**: Final deliverable spreadsheet with color-coded assignments and formulas.
- **`reviewer_assignment_matrix.csv`**: Binary assignment matrix ($67 \times 17$).
- **`champ_assignment_matrix.csv`**: Champion assignment matrix ($67 \times 17$).
- **`cochamp_assignment_matrix.csv`**: Co-Champion assignment matrix ($67 \times 17$).
- **`assignment_vector.csv`**: Flat paper-to-reviewer assignment vector.
- **`paper_assignment.csv`**: Summary table of all paper assignments with roles.
- **`summary_report.txt`**: Detailed statistical report itemizing workloads, distributions, and roles.
- **Workload Histograms:**
  - `paper_reviews_histogram.png`
  - `reviewer_workload_histogram.png`
  - `reviewer_champ_workload_histogram.png`
  - `reviewer_cochamp_workload_histogram.png`
  - `reviewer_roles_breakdown.png`
