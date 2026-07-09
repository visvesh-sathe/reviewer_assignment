# Reviewer Assignment Package Execution Instructions

This guide explains how to install dependencies, configure, and execute the `reviewer_assignment` tool.

## Prerequisites
Install the required libraries:
```bash
python3 -m pip install pandas numpy pyyaml pulp matplotlib
```

## Running the Program
Run the package as a Python module:
```bash
python3 -m reviewer_assignment [options]
```

### Options and Parameters
* `--config`: Path to the YAML configuration file (default: `input_files/config.yaml`).
* `--scrub-output`: Path to write the scrubbed affiliations CSV (default: `paper_id_and_affiliations.csv`).
* `--assignment-output`: Path to write the flat assignments CSV (default: `assignments.csv`).
* `--matching-output`: Path to write the computed intermediate matching matrix (default: `intermediate_data/reviewer_matching.csv`).
* `--matrix-output`: Path to write the solved assignment matrix (default: `assignment_matrix.csv`).
* `--vector-output`: Path to write the solved flattened assignment vector (default: `assignment_vector.csv`).
* `--report-dir`: Directory where report files and histograms will be saved (default: `reports`).

### Custom Execution Example
To run the tool with custom input config files and output locations:
```bash
python3 -m reviewer_assignment --config path/to/my_config.yaml --report-dir custom_reports_dir
```
