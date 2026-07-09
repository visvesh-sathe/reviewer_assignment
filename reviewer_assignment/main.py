"""Command Line Interface for Reviewer Assignment."""

from pathlib import Path
import argparse
import os
import sys
import pandas as pd
from .config import Config
from .scrubber import AffiliationScrubber
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
    # parser.add_argument(
    #     "--scrub-output",
    #     default="paper_id_and_affiliations.csv",
    #     help="Path to write scrubbed affiliations CSV (default: paper_id_and_affiliations.csv)",
    # )
    # parser.add_argument(
    #     "--matching-output",
    #     default="intermediate_data/reviewer_matching.csv",
    #     help="Path to write reviewer matching matrix CSV (default: intermediate_data/reviewer_matching.csv)",
    # )
    # parser.add_argument(
    #     "--matrix-output",
    #     default="assignment_matrix.csv",
    #     help="Path to write assignment matrix CSV (default: assignment_matrix.csv)",
    # )
    # parser.add_argument(
    #     "--vector-output",
    #     default="assignment_vector.csv",
    #     help="Path to write assignment vector CSV (default: assignment_vector.csv)",
    # )
    # parser.add_argument(
    #     "--report-dir",
    #     default="reports",
    #     help="Directory to save generated report charts (default: reports)",
    # )
    args = parser.parse_args()

    # 1. Load config and prepare output directories
    if not os.path.exists(args.config):
        print(f"Error: Config file not found at {args.config}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading configuration from {args.config}...")
    try:
        config = Config.from_yaml(args.config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(config.output_files_dir, exist_ok=True)
    os.makedirs(config.report_files_dir, exist_ok=True)

    # 2. Scrub affiliations
    affiliations_file = config.input_files_dir / Path(config.files.get("affiliations"))
    if not affiliations_file or not os.path.exists(affiliations_file):
        print(
            f"Error: Affiliations input file not found at {affiliations_file}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Scrubbing affiliations...")
    paper_id_and_affiliations= config.input_files_dir /  Path(config.files.get("paper_id_and_affiliations"))
    try:
        AffiliationScrubber.scrub(affiliations_file, paper_id_and_affiliations)
        print(f"Successfully scrubbed affiliations. Output saved to {paper_id_and_affiliations}")
    except Exception as e:
        print(f"Error scrubbing affiliations: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Load problem matrices
    print("Loading data files and aligning matrices...")
    try:
        problem = ReviewerAssignmentProblem.load(config)
    except Exception as e:
        print(f"Error loading and aligning data files: {e}", file=sys.stderr)
        sys.exit(1)

    # Save matching matrix to intermediate_data subdirectory
    print("Computing and saving reviewer matching matrix...")
    try:
        problem.save_matching_matrix(config.files.get("reviewer_paper_match_scores"))
    except Exception as e:
        print(f"Error saving matching matrix: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Solve the MILP
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

    # 5. Extract and print assignments
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


    # Save assignment_matrix.csv
    try:
        df_matrix = pd.DataFrame(
            assignment_matrix,
            index=reviewer_ids,
            columns=paper_ids
        )
        df_matrix.index.name = "reviewer_id"
        df_matrix.to_csv(config.files.get("assignment_matrix"))
        assignment_matrix_file = config.files.get("assignment_matrix")
        print(f"Saved assignment matrix to CSV: {assignment_matrix_file} ")
    except Exception as e:
        print(f"Error saving assignment matrix: {e}", file=sys.stderr)
        sys.exit(1)

    # Save assignment_vector.csv
    try:
        # Flat list of values representing the matrix flattened row by row
        flat_vector = assignment_matrix.flatten()
        df_vector = pd.DataFrame(flat_vector, columns=["assigned"])
        df_vector.to_csv(config.files.get("assignment_vector"), index=False)
        assignment_vector_file = config.files["assignment_vector"]
        print(f"Saved assignment vector to CSV: {assignment_vector_file}")
    except Exception as e:
        print(f"Error saving assignment vector: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate reports and plots
    print("\nGenerating assignment summary reports and charts...")
    try:
        reporter = ReviewerAssignmentReporter(problem, assignment_matrix)
        reporter.save_text_report(config.report_files_dir)
        reporter.save_plots(config.report_files_dir)
    except Exception as e:
        print(f"Error generating reports: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
