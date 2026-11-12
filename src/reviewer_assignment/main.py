"""Command Line Interface for Reviewer Assignment."""

from pathlib import Path
import argparse
import os
import sys
import pandas as pd
from .config import Config
from .data_structures import ReviewerAssignmentProblem
from .solver import ReviewerAssignmentSolver
from .reporter import ReviewerAssignmentReporter


def main():
    """Main execution function for running the reviewer assignment pipeline."""
    parser = argparse.ArgumentParser(
        description="Reviewer Assignment Optimization Tool"
    )
    parser.add_argument(
        "--config",
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

    # 1. Load config
    if not os.path.exists(args.config):
        print(f"Error: Config file not found at {args.config}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading configuration from {args.config}...")
    try:
        config = Config.from_yaml(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Determine output paths (CLI overrides config values)
    def resolve_output_path(cli_override, config_key, default_name):
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

    assignment_output = resolve_output_path(args.assignment_output, "assignment_output", "paper_assignment.csv")
    matching_output = resolve_output_path(args.matching_output, "reviewer_paper_match_scores", "intermediate_data/reviewer_paper_match_score.csv")
    matrix_output = resolve_output_path(args.matrix_output, "reviewer_assignment_matrix", "reviewer_assignment_matrix.csv")
    if not args.matrix_output and "reviewer_assignment_matrix" not in config.files and "assignment_matrix" in config.files:
        matrix_output = resolve_output_path(args.matrix_output, "assignment_matrix", "reviewer_assignment_matrix.csv")

    champ_matrix_output = resolve_output_path(args.champ_matrix_output, "champ_assignment_matrix", "champ_assignment_matrix.csv")
    cochamp_matrix_output = resolve_output_path(args.cochamp_matrix_output, "cochamp_assignment_matrix", "cochamp_assignment_matrix.csv")
    vector_output = resolve_output_path(args.vector_output, "assignment_vector", "assignment_vector.csv")

    report_dir = args.report_dir if args.report_dir else config.report_files_dir

    # Create directories for outputs
    os.makedirs(config.output_files_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
    for path in [assignment_output, matching_output, matrix_output, champ_matrix_output, cochamp_matrix_output, vector_output]:
        if path.parent:
            os.makedirs(path.parent, exist_ok=True)

    # 3. Load problem matrices
    print("Loading data files and aligning matrices...")
    try:
        problem = ReviewerAssignmentProblem.load(config)
    except Exception as e:
        print(f"Error loading and aligning data files: {e}", file=sys.stderr)
        sys.exit(1)

    # Save matching matrix
    print("Computing and saving reviewer matching matrix...")
    try:
        problem.save_matching_matrix(matching_output)
    except Exception as e:
        print(f"Error saving matching matrix: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Solve the MILP
    print("Solving the reviewer assignment MILP...")
    try:
        solver = ReviewerAssignmentSolver(problem)
        assignment_matrix, objective_value = solver.solve()
    except Exception as e:
        print(f"Error during MILP solving: {e}", file=sys.stderr)
        sys.exit(1)

    print(
        f"\nOptimal solution found! Total Matching Score (Objective Value): {objective_value:.2f}"
    )

    # Solve champion assignment
    print("Solving the champion assignment MILP...")
    try:
        champ_matrix, champ_objective_value = solver.solve_champion(assignment_matrix)
        print(f"Champion assignment found! Objective Value: {champ_objective_value:.2f}")
    except Exception as e:
        print(f"Error during champion assignment solving: {e}", file=sys.stderr)
        sys.exit(1)

    # Solve co-champion assignment
    print("Solving the co-champion assignment MILP...")
    try:
        cochamp_matrix, cochamp_objective_value = solver.solve_cochampion(assignment_matrix, champ_matrix)
        print(f"Co-champion assignment found! Objective Value: {cochamp_objective_value:.2f}")
    except Exception as e:
        print(f"Error during co-champion assignment solving: {e}", file=sys.stderr)
        sys.exit(1)

    # 6. Extract and print assignments
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
    try:
        df_assign = pd.DataFrame(assignments)
        df_assign.to_csv(assignment_output, index=False)
        print(f"Saved flat list of assignments to CSV: {assignment_output}")
    except Exception as e:
        print(f"Error saving assignments list: {e}", file=sys.stderr)
        sys.exit(1)

    # Save assignment_matrix.csv
    try:
        df_matrix = pd.DataFrame(
            assignment_matrix,
            index=reviewer_ids,
            columns=paper_ids
        )
        df_matrix.index.name = "reviewer_id"
        df_matrix.to_csv(matrix_output)
        print(f"Saved assignment matrix to CSV: {matrix_output}")
    except Exception as e:
        print(f"Error saving assignment matrix: {e}", file=sys.stderr)
        sys.exit(1)

    # Save champ_assignment_matrix.csv
    try:
        df_champ_matrix = pd.DataFrame(
            champ_matrix,
            index=reviewer_ids,
            columns=paper_ids
        )
        df_champ_matrix.index.name = "reviewer_id"
        df_champ_matrix.to_csv(champ_matrix_output)
        print(f"Saved champion assignment matrix to CSV: {champ_matrix_output}")
    except Exception as e:
        print(f"Error saving champion assignment matrix: {e}", file=sys.stderr)
        sys.exit(1)

    # Save cochamp_assignment_matrix.csv
    try:
        df_cochamp_matrix = pd.DataFrame(
            cochamp_matrix,
            index=reviewer_ids,
            columns=paper_ids
        )
        df_cochamp_matrix.index.name = "reviewer_id"
        df_cochamp_matrix.to_csv(cochamp_matrix_output)
        print(f"Saved co-champion assignment matrix to CSV: {cochamp_matrix_output}")
    except Exception as e:
        print(f"Error saving co-champion assignment matrix: {e}", file=sys.stderr)
        sys.exit(1)

    # Save assignment_vector.csv
    try:
        flat_vector = assignment_matrix.flatten()
        df_vector = pd.DataFrame(flat_vector, columns=["assigned"])
        df_vector.to_csv(vector_output, index=False)
        print(f"Saved assignment vector to CSV: {vector_output}")
    except Exception as e:
        print(f"Error saving assignment vector: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate reports and plots
    print("\nGenerating assignment summary reports and charts...")
    try:
        reporter = ReviewerAssignmentReporter(
            problem, assignment_matrix, champ_matrix, cochamp_matrix
        )
        reporter.save_text_report(report_dir)
        reporter.save_plots(report_dir)
    except Exception as e:
        print(f"Error generating reports: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
