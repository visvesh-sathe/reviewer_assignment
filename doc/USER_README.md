# User Documentation: Reviewer Assignment Optimizer

Welcome to the **Reviewer Assignment Optimizer**! This tool is designed to automate and optimize the process of assigning academic papers to peer reviewers. 

---

## 1. What This Project Does
When organizing a conference or managing peer reviews, you need to match reviewers to papers. Doing this manually is tedious and rarely yields optimal results. This tool uses **Mixed-Integer Linear Programming (MILP)** to find the mathematically best reviewer-to-paper assignment.

Specifically, the optimizer:
1. **Maximizes Expertise Matching**: It calculates a compatibility score between each reviewer and paper (by matching reviewer expertise areas with paper subject areas) and tries to maximize the total score across all assignments. Reviewer names are parsed from `Firstname` and `Lastname` columns in the expertise CSV.
2. **Respects Constraints**:
   * **Workload Limits**: Ensures reviewers are not assigned too many or too few papers (e.g., between 4 and 8 papers).
   * **Paper Coverage**: Ensures each paper receives at least a minimum number of reviews (e.g., at least 3 reviews per paper).
   * **Conflicts of Interest (COI)**: Guarantees that a reviewer is never assigned to a paper with which they have a conflict (e.g., co-author, same institution).
   * **Forced Reviewers (Must Review)**: Allows organizers to force specific assignments when necessary.
3. **Appoints Paper Champions**: Solves a secondary MILP to appoint exactly one "champion" reviewer for each paper from its assigned reviewers, balancing champion workloads. The committee Chair and Co-Chair (configured in `config.yaml`) are unconditionally flooded with COI during this solve so they cannot be appointed as champions.
4. **Appoints Paper Co-Champions**: Solves a third MILP to appoint exactly one "co-champion" reviewer for each paper from its other assigned reviewers, balancing co-champion workloads. The Chair and Co-Chair are also unconditionally flooded with COI during co-champion selection.
5. **Protects Reviewer Anonymity**: It scrubs author names and paper titles, producing an affiliation-only mapping for double-blind compatibility checking.

---

## 2. Standalone Affiliation Extraction
The `src/extract_affiliations.py` script reads the YAML configuration file (`--config input_files/config.yaml` by default, or an alternative YAML via `--config path/to/config.yaml`) to dynamically resolve input file paths (`affiliations`, `reviewer_expertise`) and output file locations (`paper_id_and_affiliations`, `paper_technical_areas`).

To extract affiliations and technical areas template using the configuration file, run:

```bash
python3 src/extract_affiliations.py --config input_files/config.yaml
```
*(Optional flags: `--config path/to/config.yaml`, `--input path/to/paper_info.csv`, `--output path/to/paper_id_and_affiliations.csv`, `--output-technical-areas path/to/paper_technical_areas.csv`, `--reviewer-expertise path/to/reviewer_expertise.csv`)*

---

## 3. Running the Assignment Optimizer
We have set up a pre-configured example using the files in the `input_files/` folder. All Python packages and library modules reside in `src/`, and the primary caller script resides in `.agents/`.

To run the optimizer, open your terminal in the project root directory and execute:

```bash
python3 .agents/assign_reviewers.py --config input_files/config.yaml
```
*(Alternatively, you can run `python3 .agents/main.py` or set `PYTHONPATH=src python3 -m reviewer_assignment`)*

This will run the pipeline, solve the assignment problem for 14 reviewers and 20 papers, resolve champion and co-champion assignments (excluding the Chair and Co-Chair from champion/co-champion roles), print the results, and write all output files, reports, and plots directly into the project directory.

---

## 3. What Files to Inspect

After running the optimizer, you will find several folders and files. Here is what they contain and why you should inspect them:

### A. Reports & Visualizations (Inspect first!)
* **`reports/summary_report.txt`**: A text report summarizing:
  * Total papers and reviewers found.
  * Number of assignments made.
  * Which reviewers have the lowest/highest workloads.
  * Which papers have the lowest/highest number of reviews.
  * **Role Distribution per Reviewer**: Number of times each reviewer is a champion, co-champion, or regular reviewer.
  * **Paper Assignments Details**: Full details listing which reviewer is the Champ, Co-Champ, and Other Reviewer(s) for each paper.
* **`reports/reviewer_roles_breakdown.png`**: A stacked bar chart showing the breakdown of each reviewer's workload (Champion vs. Co-Champion vs. Regular Reviewer). Use this to verify role balancing.
* **`reports/reviewer_workload_histogram.png`**: A chart showing how many papers are assigned to each reviewer. Use this to verify that the workload is distributed evenly among reviewers.
* **`reports/paper_reviews_histogram.png`**: A chart showing how many reviews each paper received. Use this to verify that every paper meets the minimum coverage requirement.

### B. Output Assignment Results
* **`assignments.csv`**: A human-readable list showing which reviewer is assigned to which paper ID.
* **`assignment_matrix.csv`**: A spreadsheet of size $N_{reviewers} \times N_{papers}$. A cell contains `1` if the reviewer is assigned to the paper, and `0` otherwise.
* **`assignment_vector.csv`**: The flattened row-major version of the assignment matrix, used by operations requiring a single 1D vector of decision outcomes.

### C. Cleaned Data & Intermediate Files
* **`paper_id_and_affiliations.csv`**: A scrubbed version of paper affiliations. It lists only the paper ID and institutions, with author names and titles removed.
* **`paper_technical_areas.csv`**: A mapping file listing each paper's `paper_ID`, `paper_title`, and technical area scores.
* **`intermediate_data/reviewer_matching.csv`**: A table showing the calculated matching quality score for every reviewer-paper pair before assignments are made.

---

## 4. Running with Your Own Data
To run the optimizer with your own files:
1. **Prepare Reviewer Expertise (`reviewer_expertise.csv`)**:
   - Create columns `Firstname`, `Lastname`, and `Affiliation`.
   - Reviewer names are concatenated using Pandas into `"Firstname Lastname"` format for all logs, matrices, and reports.
   - The `Affiliation` column (and any `areas` metadata header) is automatically ignored during matrix calculations.
   - Add your subcommittee expertise areas as subsequent columns (e.g., `Dig. Circuits`, `AMS Circuits`, `ML/AI`, etc.) with numeric rating scores from `0` to `10`.
2. **Prepare Other Input Files**:
   - Match the CSV formats for paper areas (`paper_area.csv`), forced assignments (`must_review.csv`), conflicts of interest (`coi.csv`), and paper info (`paper_info.csv`).
3. **Create your YAML configuration (`config.yaml`)**:
   - Specify file paths, `num_reviewers`, `num_papers`, workload constraints, `chair`, and `cochair`.
4. **Run**:
   ```bash
   python3 .agents/assign_reviewers.py --config path/to/your/config.yaml
   ```

---

## 5. New User Checklist & Setup Workflow

Follow this step-by-step workflow when setting up and running the pipeline with new paper submission data:

1. **Extract Affiliations & Technical Area Template**:
   - **Input Files Used**: Specified dynamically in the YAML config under `files.affiliations` (default: `input_files/paper_info.csv`) and `files.reviewer_expertise` (default: `input_files/reviewer_expertise.csv`).
   - **Action**: Run the affiliation extraction script (accepts `--config` / `-c` for alternative YAML configuration files):
     ```bash
     python3 src/extract_affiliations.py --config input_files/config.yaml
     ```
   - **Output Files Generated**: Specified in the YAML config under `files.paper_technical_areas` (default: `output_files/paper_technical_areas.csv`) and `files.paper_id_and_affiliations` (default: `output_files/paper_id_and_affiliations.csv`).

2. **Move Populated Technical Areas to Input Directory**:
   - **Input Files Used**: `output_files/paper_technical_areas.csv` (filled in with weights by the Chair).
   - **Action**: Move the populated file over to the `input_files/` directory (`input_files/paper_technical_areas.csv`).

3. **Generate Conflict of Interest (COI) Matrix**:
   - **Input Files Used**: `input_files/reviewer_expertise.csv` (reviewer names & affiliations) and `output_files/paper_id_and_affiliations.csv` (paper IDs & affiliations).
   - **Action**: Run the COI matrix generator (following `input_files/coi_matrix_generation.md`):
     ```bash
     python3 src/generate_coi_matrix.py
     ```
   - **Output Files Generated**:
     - `output_files/coi.csv`: Binary matrix with rows of paper IDs and columns of reviewer names (`1` for matching institutional COI, `0` otherwise).
     - `reports/coi_report.txt`: Detailed conflict report.

4. **Place COI File in Input Directory**:
   - **Input Files Used**: `output_files/coi.csv`.
   - **Action**: Move or copy `coi.csv` into the `input_files/` directory (`input_files/coi.csv`).

5. **Run the Optimizer Package**:
   - **Input Files Used**: `input_files/reviewer_expertise.csv`, `input_files/coi.csv`, `input_files/paper_technical_areas.csv`, `input_files/must_review.csv`, and `input_files/config.yaml`.
   - **Action**: Run the reviewer assignment caller script:
     ```bash
     python3 .agents/assign_reviewers.py --config input_files/config.yaml
     ```
   - **Output Files Generated**: Outputs flat assignments (`paper_assignment.csv`), solved matrices, flattened vectors, and statistical summary reports/charts in `reports/`.


