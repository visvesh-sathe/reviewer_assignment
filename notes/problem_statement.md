<!-- Notes for agy -->

# Reviewer Assignment Problem Statement

The goal of this project is to build a Python package to perform optimal reviewer assignment. 

## Input Data Elements
The system reads the following files:
* **Affiliations**: A CSV containing tiles like `paper_id`, `title`, and multiple authors and affiliations encoded `author_<number>`, and `affiliations_<number>`.
* **Reviewer Expertise**: A CSV containing reviewer names (`Firstname`, `Lastname`), an optional `Affiliation` column (ignored for matrix operations), and rated expertise scores (from 0 to 10) in sub-committee areas.
* **Paper Area**: A CSV containing paper IDs and their relevance scores (from 0 to 10) in the same set of areas.
* **Must-review**: A sparse CSV containing forced assignments of reviewers (denoted by `1`).
* **Conflict of Interest (COI)**: A sparse CSV listing conflicts where a reviewer cannot review a paper (denoted by `1`).
* **Config**: A YAML file containing run settings (`num_reviewers`, `num_papers`, reviewer/paper constraints, `chair` and `cochair` names, and relative paths to all input files).

## Execution Pipeline
1. **Scrub Affiliations**: Cleans `affiliations.csv` to keep only `paper_id` and a list of `affiliations` (scrubbing titles and author names) to produce `paper_id_and_affiliations.csv`.
2. **Load & Validate**:
   * Assures that all scores are numeric and strictly in the `[0, 10]` range.
   * Assures reviewer and paper counts match the configuration.
   * Uses Pandas to combine `Firstname` and `Lastname` into `"Firstname Lastname"` format for all reviewer IDs.
   * Automatically ignores metadata columns such as `Affiliation` when constructing the expertise score matrix.
   * Assures areas match and align, and checks that must-review and COI files do not contain unrecognized IDs.
   * Assures workload constraints are mathematically feasible before starting:
     $$\text{num\_reviewers} \times \text{max\_reviews\_per\_reviewer} \ge \text{num\_papers} \times \text{min\_reviews\_per\_paper}$$
3. **Optimize (MILP)**: Sets up and solves a Mixed-Integer Linear Program.
   * **Variables**: A binary matrix $X$ of size $N_{reviewers} \times N_{papers}$ indicating assignments.
   * **Objective**: Maximize the sum of matching scores:
     $$\sum_{r} \sum_{p} S_{r,p} \cdot X_{r,p}$$
     where matching scores $S$ is computed as the matrix product: $\text{Reviewer Expertise} \times \text{Paper Area}^T$.
   * **Constraints**: Hard conflicts (COI = 0), forced assignments (Must Review = 1), and user-configured minimum/maximum workloads per reviewer and paper.
4. Next, it's time to pick a champion. Take the matrix assignment from Step three and create a complement of that matrix (ones become 0s and 0s become 1s).
  This matrix is now the champ_coi matrix. In other words, the champ has to be one of the reviewers of the paper.
  * In addition to non-reviewers, flood the Chair and Co-Chair as COI unconditionally for all papers, preventing them from being appointed as champions even if they are assigned reviewers for the paper.
  * Now setup an MILP with the following conditions. This is the same problem as step 3 but with different constraints.
    * Each paper must have one and only one champion
    * continue to respect the coi matrix and flooded Chair/Co-Chair COIs
    * ignore the must-review matrix
    * Total champion assignments for a reviewer cannot exceed  ceiling(num_papers/num_reviewers)+1 (0 for Chair/Co-Chair). 
    * Total champion assignments for a reviewer cannot be less than: floor (num_papers/num_reviewers)-1 (0 for Chair/Co-Chair).
    * Under these constraints, goal is to maximize the sum of matching scores where the matching scores $S$ are defined as in 4 above.
  * Finally, check that all constraints are satisfied, and that the champion is also an existing reviewer (and not Chair/Co-Chair).
5. Next, it's time to pick a co-champion. Add the matrix assignment from Step 4 (sparse matrix of reviewers_by_papers with any column having only a single "1")
   and add it to the champ_coi to create a cochamp_coi_matrix. Now all reviewers except the champion are the only ones which are not a coi.
  * Unconditionally flood the Chair and Co-Chair as COI for all papers during co-champion assignment as well.
  * With this cochamp_coi matrix, solve for a cochamp assignment matrix by solving the same MILP as step 4 above (except the coi matrix is different)
    * Each paper must have one and only one co-champion
    * Total co-champion assignments for a reviewer cannot exceed  ceiling(num_papers/num_reviewers)+1 (0 for Chair/Co-Chair).
    * Under these constraints, goal is to maximize the sum of matching scores where the matching scores $S$ are defined as in 4 above.
  * Finally, check that all constraints are satisfied, and that the co-champion is also an existing reviewer (and not Chair/Co-Chair).

6. **Report & Summarize**: Generates detailed statistics on paper counts, reviewer assignments, champion assignments, cochampion assignments, and workload metrics that include the amount of times a reviewer is champ and cochamp . Outputs the text log (`summary_report.txt`) and distribution charts into the `reports/` folder. 

## Outputs
The package creates the following files:
* `paper_id_and_affiliations.csv`: Cleaned affiliations mapping.
* `intermediate_data/reviewer_matching.csv`: Pre-calculated matching matrix scores.
* `assignments.csv`: List of assigned pairs.
* `assignment_matrix.csv`: Solved binary assignment matrix.
* `assignment_vector.csv`: Row-major flattened assignment vector.
* `reports/summary_report.txt`: Stat summary (paper/reviewer counts, total assignments, workloads, and review counts).
* `reports/reviewer_workload_histogram.png` and `reports/paper_reviews_histogram.png`: Workload and paper coverage charts.
* `doc/readme.md` : Detailed readme that describes intent, directory structure, dependencies to be installed (using pip), 
    how to execute the code, and what entry in that yaml file means.