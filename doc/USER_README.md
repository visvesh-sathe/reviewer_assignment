# User Documentation: Reviewer Assignment Optimizer

Welcome to the **Reviewer Assignment Optimizer**! This tool is designed to automate and optimize the process of assigning academic papers to peer reviewers. 

---

## 1. What This Project Does
When organizing a conference or managing peer reviews, you need to match reviewers to papers. Doing this manually is tedious and rarely yields optimal results. This tool uses **Mixed-Integer Linear Programming (MILP)** to find the mathematically best reviewer-to-paper assignment.

Specifically, the optimizer:
1. **Maximizes Expertise Matching**: It calculates a compatibility score between each reviewer and paper (by matching reviewer expertise areas with paper subject areas) and tries to maximize the total score across all assignments.
2. **Respects Constraints**:
   * **Workload Limits**: Ensures reviewers are not assigned too many or too few papers (e.g., between 4 and 8 papers).
   * **Paper Coverage**: Ensures each paper receives at least a minimum number of reviews (e.g., at least 3 reviews per paper).
   * **Conflicts of Interest (COI)**: Guarantees that a reviewer is never assigned to a paper with which they have a conflict (e.g., co-author, same institution).
   * **Forced Reviewers (Must Review)**: Allows organizers to force specific assignments when necessary.
3. **Protects Reviewer Anonymity**: It scrubs author names and paper titles, producing an affiliation-only mapping for double-blind compatibility checking.

---

## 2. Running a Demo
We have set up a pre-configured example in the `demo/` folder so you can see the optimizer in action immediately.

To run the optimizer using the demo files, open your terminal in the project root directory and execute:

```bash
python3 -m reviewer_assignment \
  --config demo/input_files/config.yaml \
  --scrub-output demo/paper_id_and_affiliations.csv \
  --assignment-output demo/assignments.csv \
  --matching-output demo/intermediate_data/reviewer_matching.csv \
  --matrix-output demo/assignment_matrix.csv \
  --vector-output demo/assignment_vector.csv \
  --report-dir demo/reports
```

This will run the pipeline, solve the assignment problem for 10 reviewers and 20 papers, print the assignments, and write all output files and plots directly into the `demo/` subdirectory.

---

## 3. What Files to Inspect (Inside the `demo/` Directory)

After running the optimizer, you will find several folders and files inside the `demo/` directory. Here is what they contain and why you should inspect them:

### A. Reports & Visualizations (Inspect first!)
* **`demo/reports/summary_report.txt`**: A text report summarizing:
  * Total papers and reviewers found.
  * Number of assignments made.
  * Which reviewers have the lowest/highest workloads.
  * Which papers have the lowest/highest number of reviews.
* **`demo/reports/reviewer_workload_histogram.png`**: A chart showing how many papers are assigned to each reviewer. Use this to verify that the workload is distributed evenly among reviewers.
* **`demo/reports/paper_reviews_histogram.png`**: A chart showing how many reviews each paper received. Use this to verify that every paper meets the minimum coverage requirement.

### B. Output Assignment Results
* **`demo/assignments.csv`**: A human-readable list showing which reviewer is assigned to which paper ID.
* **`demo/assignment_matrix.csv`**: A spreadsheet of size $N_{reviewers} \times N_{papers}$. A cell contains `1` if the reviewer is assigned to the paper, and `0` otherwise.
* **`demo/assignment_vector.csv`**: The flattened row-major version of the assignment matrix, used by operations requiring a single 1D vector of decision outcomes.

### C. Cleaned Data & Intermediate Files
* **`demo/paper_id_and_affiliations.csv`**: A scrubbed version of paper affiliations. It lists only the paper ID and institutions, with author names and titles removed.
* **`demo/intermediate_data/reviewer_matching.csv`**: A table showing the calculated matching quality score for every reviewer-paper pair before assignments are made.

---

## 4. Running with Your Own Data
To run the optimizer with your own files:
1. Prepare your input files (affiliations, reviewer expertise, paper areas, must-review, and conflict of interest) matching the CSV formats of the files inside `demo/input_files/`.
2. Create your own `config.yaml` specifying the paths to your CSV files and your review count limits.
3. Run:
   ```bash
   python3 -m reviewer_assignment --config path/to/your/config.yaml
   ```
