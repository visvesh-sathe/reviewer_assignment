"""Top-level caller script and function for Reviewer Assignment.

This script is located in the .agents directory and provides both a Python
function `assign_reviewers()` and a command-line interface `main()` to execute
the complete reviewer assignment optimization pipeline.

It dynamically configures sys.path so it has full access to packages and
modules located under the `src` directory.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Resolve directory paths
AGENTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = AGENTS_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"

# Add src and project root to sys.path to access packages
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(1, str(PROJECT_ROOT))

# Import reviewer_assignment package modules from src
from reviewer_assignment.config import Config
from reviewer_assignment.data_structures import ReviewerAssignmentProblem
from reviewer_assignment.solver import ReviewerAssignmentSolver
from reviewer_assignment.reporter import ReviewerAssignmentReporter
import pandas as pd


def resolve_path(path_str: str, base_dir: Path = PROJECT_ROOT) -> Path:
    """Resolves a file path relative to current working directory or project root."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    # Check relative to project root
    root_p = base_dir / p
    if root_p.exists() or not p.parent.exists():
        return root_p
    return p.resolve()


def assign_reviewers(
    config_path: str = "input_files/config.yaml",
    scrub_output: Optional[str] = None,
    assignment_output: Optional[str] = None,
    matching_output: Optional[str] = None,
    matrix_output: Optional[str] = None,
    champ_matrix_output: Optional[str] = None,
    cochamp_matrix_output: Optional[str] = None,
    vector_output: Optional[str] = None,
    report_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Caller function to run the reviewer assignment optimization workflow.

    Args:
        config_path: Path to YAML configuration file.
        scrub_output: Optional override for scrubbed affiliations output path.
        assignment_output: Optional override for flat assignments CSV output path.
        matching_output: Optional override for reviewer matching matrix CSV output path.
        matrix_output: Optional override for reviewer assignment matrix CSV output path.
        champ_matrix_output: Optional override for champion matrix CSV output path.
        cochamp_matrix_output: Optional override for co-champion matrix CSV output path.
        vector_output: Optional override for assignment vector CSV output path.
        report_dir: Optional override for report output directory.

    Returns:
        A dictionary with problem, solver results, objective values, and output file paths.
    """
    resolved_config = resolve_path(config_path)
    if not resolved_config.exists():
        raise FileNotFoundError(f"Configuration file not found: {resolved_config}")

    print(f"Loading configuration from {resolved_config}...")
    config = Config.from_yaml(str(resolved_config))

    # Adjust config relative directories if working directory is inside .agents or elsewhere
    def fix_relative_dir(d_str: str) -> str:
        d_path = Path(d_str)
        if not d_path.is_absolute() and not d_path.exists() and (PROJECT_ROOT / d_path).exists():
            return str(PROJECT_ROOT / d_path)
        return d_str

    config.input_files_dir = fix_relative_dir(config.input_files_dir)
    config.output_files_dir = fix_relative_dir(config.output_files_dir)
    config.report_files_dir = fix_relative_dir(config.report_files_dir)

    # Determine output paths
    def resolve_out(cli_override, config_key, default_name):
        raw_val = cli_override if cli_override else config.files.get(config_key, default_name)
        val_path = Path(raw_val)
        if val_path.is_absolute():
            return val_path
        # Respect paths explicitly targeting intermediate directories
        if val_path.parts and val_path.parts[0] in ["intermediate_files", "intermediate_data"]:
            return val_path
        out_dir = Path(config.output_files_dir)
        if val_path.parts and val_path.parts[0] == out_dir.name:
            val_path = Path(*val_path.parts[1:])
        return out_dir / val_path

    assignment_out_path = resolve_out(assignment_output, "assignment_output", "paper_assignment.csv")
    matching_out_path = resolve_out(matching_output, "reviewer_paper_match_scores", "intermediate_data/reviewer_paper_match_score.csv")
    matrix_out_path = resolve_out(matrix_output, "reviewer_assignment_matrix", "reviewer_assignment_matrix.csv")
    if not matrix_output and "reviewer_assignment_matrix" not in config.files and "assignment_matrix" in config.files:
        matrix_out_path = resolve_out(matrix_output, "assignment_matrix", "reviewer_assignment_matrix.csv")

    champ_out_path = resolve_out(champ_matrix_output, "champ_assignment_matrix", "champ_assignment_matrix.csv")
    cochamp_out_path = resolve_out(cochamp_matrix_output, "cochamp_assignment_matrix", "cochamp_assignment_matrix.csv")
    vector_out_path = resolve_out(vector_output, "assignment_vector", "assignment_vector.csv")

    resolved_report_dir = report_dir if report_dir else config.report_files_dir

    # Create directories for outputs
    os.makedirs(config.output_files_dir, exist_ok=True)
    os.makedirs(resolved_report_dir, exist_ok=True)
    for p in [assignment_out_path, matching_out_path, matrix_out_path, champ_out_path, cochamp_out_path, vector_out_path]:
        if p.parent:
            os.makedirs(p.parent, exist_ok=True)

    # Load problem matrices
    print("Loading data files and aligning matrices...")
    problem = ReviewerAssignmentProblem.load(config)

    # Save matching matrix
    print("Computing and saving reviewer matching matrix...")
    problem.save_matching_matrix(str(matching_out_path))

    # Solve MILP
    print("Solving the reviewer assignment MILP...")
    solver = ReviewerAssignmentSolver(problem)
    assignment_matrix, objective_value = solver.solve()
    print(f"\nOptimal solution found! Total Matching Score (Objective Value): {objective_value:.2f}")

    # Solve champion assignment
    print("Solving the champion assignment MILP...")
    champ_matrix, champ_objective_value = solver.solve_champion(assignment_matrix)
    print(f"Champion assignment found! Objective Value: {champ_objective_value:.2f}")

    # Solve co-champion assignment
    print("Solving the co-champion assignment MILP...")
    cochamp_matrix, cochamp_objective_value = solver.solve_cochampion(assignment_matrix, champ_matrix)
    print(f"Co-champion assignment found! Objective Value: {cochamp_objective_value:.2f}")

    # Extract and save flat assignments
    reviewer_ids = problem.reviewer_expertise.reviewer_ids
    paper_ids = problem.paper_area.paper_ids

    assignments = []
    print("\n--- Reviewer Assignment Results ---")
    for r_idx, r_id in enumerate(reviewer_ids):
        assigned_p_indices = [
            p_idx
            for p_idx in range(len(paper_ids))
            if assignment_matrix[r_idx, p_idx] == 1
        ]
        assigned_p_ids = [paper_ids[p_idx] for p_idx in assigned_p_indices]
        print(f"Reviewer: {r_id:<12} | Assigned Papers: {assigned_p_ids}")

        for p_id in assigned_p_ids:
            assignments.append({"reviewer_id": r_id, "paper_id": p_id})

    # Save assignments.csv
    df_assign = pd.DataFrame(assignments)
    df_assign.to_csv(assignment_out_path, index=False)
    print(f"Saved flat list of assignments to CSV: {assignment_out_path}")

    # Save assignment_matrix.csv
    df_matrix = pd.DataFrame(assignment_matrix, index=reviewer_ids, columns=paper_ids)
    df_matrix.index.name = "reviewer_id"
    df_matrix.to_csv(matrix_out_path)
    print(f"Saved assignment matrix to CSV: {matrix_out_path}")

    # Save champ_assignment_matrix.csv
    df_champ_matrix = pd.DataFrame(champ_matrix, index=reviewer_ids, columns=paper_ids)
    df_champ_matrix.index.name = "reviewer_id"
    df_champ_matrix.to_csv(champ_out_path)
    print(f"Saved champion assignment matrix to CSV: {champ_out_path}")

    # Save cochamp_assignment_matrix.csv
    df_cochamp_matrix = pd.DataFrame(cochamp_matrix, index=reviewer_ids, columns=paper_ids)
    df_cochamp_matrix.index.name = "reviewer_id"
    df_cochamp_matrix.to_csv(cochamp_out_path)
    print(f"Saved co-champion assignment matrix to CSV: {cochamp_out_path}")

    # Save assignment_vector.csv
    flat_vector = assignment_matrix.flatten()
    df_vector = pd.DataFrame(flat_vector, columns=["assigned"])
    df_vector.to_csv(vector_out_path, index=False)
    print(f"Saved assignment vector to CSV: {vector_out_path}")

    # Generate reports and plots
    print("\nGenerating assignment summary reports and charts...")
    reporter = ReviewerAssignmentReporter(
        problem, assignment_matrix, champ_matrix, cochamp_matrix
    )
    text_report_path = reporter.save_text_report(resolved_report_dir)
    reporter.save_plots(resolved_report_dir)

    return {
        "problem": problem,
        "assignment_matrix": assignment_matrix,
        "champ_matrix": champ_matrix,
        "cochamp_matrix": cochamp_matrix,
        "objective_value": objective_value,
        "champ_objective_value": champ_objective_value,
        "cochamp_objective_value": cochamp_objective_value,
        "output_files": {
            "assignments": str(assignment_out_path),
            "assignment_matrix": str(matrix_out_path),
            "champ_matrix": str(champ_out_path),
            "cochamp_matrix": str(cochamp_out_path),
            "assignment_vector": str(vector_out_path),
            "matching_scores": str(matching_out_path),
            "text_report": str(text_report_path),
        },
    }


def main():
    """Main execution function for running the caller script from CLI."""
    parser = argparse.ArgumentParser(
        description="Top-Level Caller for Reviewer Assignment Optimization"
    )
    parser.add_argument(
        "--config",
        "-c",
        default="input_files/config.yaml",
        help="Path to YAML config file (default: input_files/config.yaml)",
    )
    parser.add_argument(
        "--scrub-output",
        help="Path to write scrubbed affiliations CSV",
    )
    parser.add_argument(
        "--assignment-output",
        help="Path to write the flat assignments CSV",
    )
    parser.add_argument(
        "--matching-output",
        help="Path to write reviewer matching matrix CSV",
    )
    parser.add_argument(
        "--matrix-output",
        help="Path to write reviewer assignment matrix CSV",
    )
    parser.add_argument(
        "--champ-matrix-output",
        help="Path to write champion assignment matrix CSV",
    )
    parser.add_argument(
        "--cochamp-matrix-output",
        help="Path to write co-champion assignment matrix CSV",
    )
    parser.add_argument(
        "--vector-output",
        help="Path to write assignment vector CSV",
    )
    parser.add_argument(
        "--report-dir",
        help="Directory to save generated report charts",
    )
    args = parser.parse_args()

    try:
        assign_reviewers(
            config_path=args.config,
            scrub_output=args.scrub_output,
            assignment_output=args.assignment_output,
            matching_output=args.matching_output,
            matrix_output=args.matrix_output,
            champ_matrix_output=args.champ_matrix_output,
            cochamp_matrix_output=args.cochamp_matrix_output,
            vector_output=args.vector_output,
            report_dir=args.report_dir,
        )
    except Exception as e:
        print(f"Error during reviewer assignment execution: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
