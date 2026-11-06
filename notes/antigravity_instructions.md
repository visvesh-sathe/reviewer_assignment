# Reviewer Assignment Package Execution Instructions

This guide explains how to install dependencies, configure, and execute the `reviewer_assignment` tool.

## Prerequisites
Install the required libraries:
```bash
python3 -m pip install pandas numpy pyyaml pulp matplotlib
```

## Running the Program
Run the top-level calling script under `.agents/`:
```bash
python3 .agents/assign_reviewers.py [options]
```
Or run `reviewer_assignment` as a module by including `src/` in `PYTHONPATH`:
```bash
PYTHONPATH=src python3 -m reviewer_assignment [options]
```

### Options and Parameters
* `--config`: Path to the YAML configuration file (default: `input_files/config.yaml`).
* `--scrub-output`: Path to write the scrubbed affiliations CSV (default: `output_files/intermediate_data/paper_id_and_affiliations.csv`).
* `--assignment-output`: Path to write the flat assignments CSV (default: `output_files/paper_assignment.csv`).
* `--matching-output`: Path to write the computed intermediate matching matrix (default: `output_files/intermediate_data/reviewer_paper_match_score.csv`).
* `--matrix-output`: Path to write the solved assignment matrix (default: `output_files/reviewer_assignment_matrix.csv`).
* `--champ-matrix-output`: Path to write the solved champion matrix (default: `output_files/champ_assignment_matrix.csv`).
* `--cochamp-matrix-output`: Path to write the solved co-champion matrix (default: `output_files/cochamp_assignment_matrix.csv`).
* `--vector-output`: Path to write the solved flattened assignment vector (default: `output_files/assignment_vector.csv`).
* `--report-dir`: Directory where report files and histograms will be saved (default: `reports`).

### Custom Execution Example
To run the tool with custom input config files and output locations:
```bash
python3 .agents/assign_reviewers.py --config path/to/my_config.yaml --report-dir custom_reports_dir
```
