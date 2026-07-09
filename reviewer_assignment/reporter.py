"""Reporting and plotting module for reviewer assignments."""

import os
from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import numpy as np
from .data_structures import ReviewerAssignmentProblem


class ReviewerAssignmentReporter:
    """Computes summary statistics and generates charts for reviewer assignments."""

    def __init__(
        self, problem: ReviewerAssignmentProblem, assignment_matrix: np.ndarray
    ):
        """Initializes the reporter.

        Args:
            problem: A ReviewerAssignmentProblem instance.
            assignment_matrix: Binary assignment matrix from the MILP solver.
        """
        self.problem = problem
        self.assignment_matrix = assignment_matrix
        self.reviewer_ids = problem.reviewer_expertise.reviewer_ids
        self.paper_ids = problem.paper_area.paper_ids

    def generate_summary(self) -> Dict[str, Any]:
        """Calculates statistical metrics of the assignments.

        Returns:
            A dictionary containing report metrics.
        """
        num_papers = len(self.paper_ids)
        num_reviewers = len(self.reviewer_ids)
        total_assignments = int(np.sum(self.assignment_matrix))

        # Reviews per reviewer (workload)
        reviews_per_reviewer = np.sum(self.assignment_matrix, axis=1)
        min_revs = int(np.min(reviews_per_reviewer))
        max_revs = int(np.max(reviews_per_reviewer))

        min_revs_reviewers = [
            self.reviewer_ids[i]
            for i, count in enumerate(reviews_per_reviewer)
            if count == min_revs
        ]
        max_revs_reviewers = [
            self.reviewer_ids[i]
            for i, count in enumerate(reviews_per_reviewer)
            if count == max_revs
        ]

        # Reviews per paper
        reviews_per_paper = np.sum(self.assignment_matrix, axis=0)
        min_paper_revs = int(np.min(reviews_per_paper))
        max_paper_revs = int(np.max(reviews_per_paper))

        min_revs_papers = [
            self.paper_ids[i]
            for i, count in enumerate(reviews_per_paper)
            if count == min_paper_revs
        ]
        max_revs_papers = [
            self.paper_ids[i]
            for i, count in enumerate(reviews_per_paper)
            if count == max_paper_revs
        ]

        return {
            "num_papers": num_papers,
            "num_reviewers": num_reviewers,
            "total_assignments": total_assignments,
            "min_reviews_per_reviewer": min_revs,
            "min_reviews_reviewers": min_revs_reviewers,
            "max_reviews_per_reviewer": max_revs,
            "max_reviews_reviewers": max_revs_reviewers,
            "min_reviews_per_paper": min_paper_revs,
            "min_reviews_papers": min_revs_papers,
            "max_reviews_per_paper": max_paper_revs,
            "max_reviews_papers": max_revs_papers,
        }

    def print_text_report(self) -> str:
        """Prints a human-readable text summary of the assignment.

        Returns:
            The printed report string.
        """
        s = self.generate_summary()
        report = (
            f"=== Reviewer Assignment Summary Report ===\n"
            f"Total Papers Found: {s['num_papers']}\n"
            f"Total Reviewers Found: {s['num_reviewers']}\n"
            f"Total Review Assignments Made (1s in matrix): {s['total_assignments']}\n\n"
            f"Reviewer Workload:\n"
            f"  - Lowest paper count assigned to a reviewer: {s['min_reviews_per_reviewer']}\n"
            f"    Reviewers: {', '.join(s['min_reviews_reviewers'])}\n"
            f"  - Highest paper count assigned to a reviewer: {s['max_reviews_per_reviewer']}\n"
            f"    Reviewers: {', '.join(s['max_reviews_reviewers'])}\n\n"
            f"Paper Review Counts:\n"
            f"  - Lowest number of reviews a paper receives: {s['min_reviews_per_paper']}\n"
            f"    Papers: {s['min_reviews_papers']}\n"
            f"  - Highest number of reviews a paper receives: {s['max_reviews_per_paper']}\n"
            f"    Papers: {s['max_reviews_papers']}\n"
            f"==========================================="
        )
        print(report)
        return report

    def save_text_report(self, output_dir: str = "reports") -> str:
        """Saves the text summary report to a file inside the output directory.

        Args:
            output_dir: Directory where the report will be saved.

        Returns:
            The path to the saved text report file.
        """
        os.makedirs(output_dir, exist_ok=True)
        report = self.print_text_report()
        report_path = os.path.join(output_dir, "summary_report.txt")
        with open(report_path, "w") as f:
            f.write(report)
        print(f"Saved summary report to {report_path}")
        return report_path

    def save_plots(self, output_dir: str = "reports") -> Tuple[str, str]:
        """Saves distribution histograms for reviewers and papers using matplotlib.

        Args:
            output_dir: Directory where png charts will be saved.

        Returns:
            Tuple of (reviewer_workload_chart_path, paper_reviews_chart_path).
        """
        os.makedirs(output_dir, exist_ok=True)

        # 1. Histogram of reviewer workloads
        reviews_per_reviewer = np.sum(self.assignment_matrix, axis=1)
        plt.figure(figsize=(8, 5))
        bins = np.arange(
            np.min(reviews_per_reviewer) - 0.5,
            np.max(reviews_per_reviewer) + 1.5,
            1,
        )
        plt.hist(
            reviews_per_reviewer,
            bins=bins,
            rwidth=0.8,
            color="skyblue",
            edgecolor="black",
        )
        plt.title("Distribution of Paper Counts Assigned to Reviewers")
        plt.xlabel("Number of Papers Assigned")
        plt.ylabel("Number of Reviewers")
        plt.xticks(
            np.arange(np.min(reviews_per_reviewer), np.max(reviews_per_reviewer) + 1)
        )
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        reviewer_hist_path = os.path.join(
            output_dir, "reviewer_workload_histogram.png"
        )
        plt.savefig(reviewer_hist_path, dpi=300, bbox_inches="tight")
        plt.close()

        # 2. Histogram of reviews per paper (bins = paper_ids, frequency = reviewer count)
        reviews_per_paper = np.sum(self.assignment_matrix, axis=0)
        plt.figure(figsize=(10, 5))
        paper_labels = [str(pid) for pid in self.paper_ids]
        plt.bar(paper_labels, reviews_per_paper, color="lightgreen", edgecolor="black")
        plt.title("Number of Reviewers per Paper")
        plt.xlabel("Paper ID")
        plt.ylabel("Number of Reviewers")
        plt.xticks(rotation=45)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        paper_hist_path = os.path.join(output_dir, "paper_reviews_histogram.png")
        plt.savefig(paper_hist_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"Saved workload histogram to {reviewer_hist_path}")
        print(f"Saved paper reviews histogram to {paper_hist_path}")
        return reviewer_hist_path, paper_hist_path
