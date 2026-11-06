"""Reporting and plotting module for reviewer assignments."""

import os
from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
import numpy as np
from .data_structures import ReviewerAssignmentProblem


class ReviewerAssignmentReporter:
    """Computes summary statistics and generates charts for reviewer assignments."""

    def __init__(
        self,
        problem: ReviewerAssignmentProblem,
        assignment_matrix: np.ndarray,
        champ_matrix: np.ndarray = None,
        cochamp_matrix: np.ndarray = None,
    ):
        """Initializes the reporter.

        Args:
            problem: A ReviewerAssignmentProblem instance.
            assignment_matrix: Binary assignment matrix from the MILP solver.
            champ_matrix: Binary champion assignment matrix.
            cochamp_matrix: Binary co-champion assignment matrix.
        """
        self.problem = problem
        self.assignment_matrix = assignment_matrix
        self.champ_matrix = champ_matrix
        self.cochamp_matrix = cochamp_matrix
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

        summary = {
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

        if self.champ_matrix is not None:
            champ_counts = np.sum(self.champ_matrix, axis=1)
            summary["reviewer_champ_counts"] = {
                self.reviewer_ids[i]: int(count) for i, count in enumerate(champ_counts)
            }
            paper_champs = {}
            for p_idx, p_id in enumerate(self.paper_ids):
                champ_r_idx = np.where(self.champ_matrix[:, p_idx] == 1)[0]
                if len(champ_r_idx) > 0:
                    paper_champs[p_id] = self.reviewer_ids[champ_r_idx[0]]
            summary["paper_champs"] = paper_champs

        if self.cochamp_matrix is not None:
            cochamp_counts = np.sum(self.cochamp_matrix, axis=1)
            summary["reviewer_cochamp_counts"] = {
                self.reviewer_ids[i]: int(count) for i, count in enumerate(cochamp_counts)
            }
            paper_cochamps = {}
            for p_idx, p_id in enumerate(self.paper_ids):
                cochamp_r_idx = np.where(self.cochamp_matrix[:, p_idx] == 1)[0]
                if len(cochamp_r_idx) > 0:
                    paper_cochamps[p_id] = self.reviewer_ids[cochamp_r_idx[0]]
            summary["paper_cochamps"] = paper_cochamps

        return summary

    def print_text_report(self) -> str:
        """Prints a human-readable text summary of the assignment.

        Returns:
            The printed report string.
        """
        s = self.generate_summary()
        report_lines = [
            "=== Reviewer Assignment Summary Report ===",
            f"Total Papers Found: {s['num_papers']}",
            f"Total Reviewers Found: {s['num_reviewers']}",
            f"Total Review Assignments Made (1s in matrix): {s['total_assignments']}\n",
            "Reviewer Workload:",
            f"  - Lowest paper count assigned to a reviewer: {s['min_reviews_per_reviewer']}",
            f"    Reviewers: {', '.join(s['min_reviews_reviewers'])}",
            f"  - Highest paper count assigned to a reviewer: {s['max_reviews_per_reviewer']}",
            f"    Reviewers: {', '.join(s['max_reviews_reviewers'])}\n",
            "Paper Review Counts:",
            f"  - Lowest number of reviews a paper receives: {s['min_reviews_per_paper']}",
            f"    Papers: {s['min_reviews_papers']}",
            f"  - Highest number of reviews a paper receives: {s['max_reviews_per_paper']}",
            f"    Papers: {s['max_reviews_papers']}"
        ]

        if "reviewer_champ_counts" in s or "reviewer_cochamp_counts" in s:
            report_lines.append("\nRole Distribution per Reviewer:")
            for r_id in self.reviewer_ids:
                r_idx = self.reviewer_ids.index(r_id)
                total_reviews = int(np.sum(self.assignment_matrix[r_idx, :]))
                champ_val = s.get("reviewer_champ_counts", {}).get(r_id, 0)
                cochamp_val = s.get("reviewer_cochamp_counts", {}).get(r_id, 0)
                other_reviews = total_reviews - champ_val - cochamp_val
                report_lines.append(
                    f"  - {r_id:<12}: Total={total_reviews}, Champ={champ_val}, Co-Champ={cochamp_val}, Regular={other_reviews}"
                )

        if "paper_champs" in s or "paper_cochamps" in s:
            report_lines.append("\nPaper Assignments Details:")
            for p_id in self.paper_ids:
                p_idx = self.paper_ids.index(p_id)
                assigned_revs = [
                    self.reviewer_ids[r_idx]
                    for r_idx in range(len(self.reviewer_ids))
                    if self.assignment_matrix[r_idx, p_idx] == 1
                ]
                champ = s.get("paper_champs", {}).get(p_id, "None")
                cochamp = s.get("paper_cochamps", {}).get(p_id, "None")
                others = [r for r in assigned_revs if r != champ and r != cochamp]
                report_lines.append(
                    f"  - Paper {p_id:<3}: Champ={champ:<12} | Co-Champ={cochamp:<12} | Other Reviewers={others}"
                )

        report_lines.append("===========================================")
        report = "\n".join(report_lines)
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

        # 3. Stacked bar chart showing reviewer role breakdown if champ_matrix is provided
        if self.champ_matrix is not None and self.cochamp_matrix is not None:
            plt.figure(figsize=(10, 6))
            r_labels = [str(rid) for rid in self.reviewer_ids]
            champ_counts = np.sum(self.champ_matrix, axis=1)
            cochamp_counts = np.sum(self.cochamp_matrix, axis=1)
            total_counts = np.sum(self.assignment_matrix, axis=1)
            regular_counts = total_counts - champ_counts - cochamp_counts

            # Plot stacked bar chart
            plt.bar(r_labels, champ_counts, label="Champion", color="#4e79a7", edgecolor="black")
            plt.bar(r_labels, cochamp_counts, bottom=champ_counts, label="Co-Champion", color="#f28e2b", edgecolor="black")
            plt.bar(r_labels, regular_counts, bottom=champ_counts+cochamp_counts, label="Regular Reviewer", color="#e15759", edgecolor="black")

            plt.title("Reviewer Workload Breakdown by Role")
            plt.xlabel("Reviewer ID")
            plt.ylabel("Number of Assigned Papers")
            plt.xticks(rotation=45)
            plt.legend(loc="upper right")
            plt.grid(axis="y", linestyle="--", alpha=0.7)
            role_chart_path = os.path.join(output_dir, "reviewer_roles_breakdown.png")
            plt.savefig(role_chart_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved reviewer roles breakdown chart to {role_chart_path}")

            # 4. Histogram of reviewer champion workloads
            plt.figure(figsize=(8, 5))
            bins_champ = np.arange(np.min(champ_counts) - 0.5, np.max(champ_counts) + 1.5, 1)
            plt.hist(champ_counts, bins=bins_champ, rwidth=0.8, color="#4e79a7", edgecolor="black")
            plt.title("Distribution of Champion Assignments to Reviewers")
            plt.xlabel("Number of Champion Assignments")
            plt.ylabel("Number of Reviewers")
            plt.xticks(np.arange(np.min(champ_counts), np.max(champ_counts) + 1))
            plt.grid(axis="y", linestyle="--", alpha=0.7)
            champ_hist_path = os.path.join(output_dir, "reviewer_champ_workload_histogram.png")
            plt.savefig(champ_hist_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved reviewer champion workload histogram to {champ_hist_path}")

            # 5. Histogram of reviewer co-champion workloads
            plt.figure(figsize=(8, 5))
            bins_cochamp = np.arange(np.min(cochamp_counts) - 0.5, np.max(cochamp_counts) + 1.5, 1)
            plt.hist(cochamp_counts, bins=bins_cochamp, rwidth=0.8, color="#f28e2b", edgecolor="black")
            plt.title("Distribution of Co-Champion Assignments to Reviewers")
            plt.xlabel("Number of Co-Champion Assignments")
            plt.ylabel("Number of Reviewers")
            plt.xticks(np.arange(np.min(cochamp_counts), np.max(cochamp_counts) + 1))
            plt.grid(axis="y", linestyle="--", alpha=0.7)
            cochamp_hist_path = os.path.join(output_dir, "reviewer_cochamp_workload_histogram.png")
            plt.savefig(cochamp_hist_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved reviewer co-champion workload histogram to {cochamp_hist_path}")

        print(f"Saved workload histogram to {reviewer_hist_path}")
        print(f"Saved paper reviews histogram to {paper_hist_path}")
        return reviewer_hist_path, paper_hist_path
