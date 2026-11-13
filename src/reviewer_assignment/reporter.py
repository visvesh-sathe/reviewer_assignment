"""Reporting and plotting module for reviewer assignments."""

import os
from typing import List, Dict, Any, Tuple, Optional
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

    def save_excel_deliverable(
        self,
        template_path: str,
        output_path: str,
        paper_info_path: Optional[str] = None,
    ) -> str:
        """Fills the deliverable Excel spreadsheet according to the template format.

        Columns list all reviewers in order of reviewer_expertise.csv.
        For each paper, assigned reviewers receive 1, unassigned receive 'x'.
        Champions are shaded in green, and Co-Champions are shaded in yellow.

        Args:
            template_path: Path to the template Excel file.
            output_path: Path where the filled Excel file should be written.
            paper_info_path: Optional path to paper info CSV to retrieve paper titles.

        Returns:
            The path to the saved Excel file.
        """
        import io
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from openpyxl.workbook.views import BookView
        import pandas as pd

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")

        # Map paper IDs to titles
        id_title_map = {}
        if paper_info_path and os.path.exists(paper_info_path):
            try:
                df_info = pd.read_csv(paper_info_path, encoding="utf-8", encoding_errors="replace")
                id_col = None
                for col in ["ID", "id", "Paper ID", "PaperID", "paper_id"]:
                    if col in df_info.columns:
                        id_col = col
                        break
                title_col = None
                for col in ["Title", "title", "Paper Title", "paper_title"]:
                    if col in df_info.columns:
                        title_col = col
                        break
                if id_col and title_col:
                    id_title_map = dict(zip(df_info[id_col].astype(str), df_info[title_col].astype(str)))
            except Exception as e:
                print(f"Warning: could not read paper info from '{paper_info_path}': {e}")

        # Load workbook via BytesIO to support .xls file extension with OOXML internal structure
        with open(template_path, "rb") as f:
            wb = openpyxl.load_workbook(io.BytesIO(f.read()))

        target_sheet = "2027 Review Summary" if "2027 Review Summary" in wb.sheetnames else wb.sheetnames[0]
        ws = wb[target_sheet]
        target_idx = wb.sheetnames.index(target_sheet)
        wb.active = target_idx
        wb.views = [BookView(activeTab=target_idx)]

        # Styles
        champ_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        cochamp_fill = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
        white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        thin_side = Side(border_style="thin", color="D9D9D9")
        cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        font_12 = Font(name="Arial", size=12)
        font_12_bold = Font(name="Arial", size=12, bold=True)
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")

        # Update swatch colors in the Key block (Row 3: Champion, Row 4: Co-Champion)
        if target_sheet == "2027 Review Summary":
            ws.cell(3, 1).fill = champ_fill
            ws.cell(4, 1).fill = cochamp_fill

        num_reviewers = len(self.reviewer_ids)
        num_papers = len(self.paper_ids)

        # Header Row (Row 8)
        ws.cell(8, 1, value="ID").font = font_12_bold
        ws.cell(8, 1).alignment = center_align
        ws.cell(8, 1).border = cell_border

        ws.cell(8, 2, value="Title").font = font_12_bold
        ws.cell(8, 2).alignment = left_align
        ws.cell(8, 2).border = cell_border

        for r_idx, r_name in enumerate(self.reviewer_ids):
            col_idx = 3 + r_idx
            c = ws.cell(8, col_idx, value=r_name)
            c.font = font_12_bold
            c.alignment = center_align
            c.border = cell_border

        walkouts_col = 3 + num_reviewers
        reviews_col = 4 + num_reviewers
        first_rev_letter = get_column_letter(3)
        last_rev_letter = get_column_letter(2 + num_reviewers)

        ws.cell(8, walkouts_col, value="# of Walkouts").font = font_12_bold
        ws.cell(8, walkouts_col).alignment = center_align
        ws.cell(8, walkouts_col).border = cell_border

        ws.cell(8, reviews_col, value="# of Reviews").font = font_12_bold
        ws.cell(8, reviews_col).alignment = center_align
        ws.cell(8, reviews_col).border = cell_border

        # Clear any old headers beyond reviews_col
        max_c = max(reviews_col + 2, ws.max_column)
        for col_idx in range(reviews_col + 1, max_c + 1):
            ws.cell(8, col_idx, value=None)

        start_row = 9
        for p_idx, p_id in enumerate(self.paper_ids):
            row_num = start_row + p_idx
            p_str = str(p_id)
            title = id_title_map.get(p_str, f"Paper {p_id}")

            # Col A: ID
            cA = ws.cell(row_num, 1, value=int(p_str) if p_str.isdigit() else p_str)
            cA.font = font_12
            cA.alignment = center_align
            cA.fill = white_fill
            cA.border = cell_border

            # Col B: Title
            cB = ws.cell(row_num, 2, value=title)
            cB.font = font_12
            cB.alignment = left_align
            cB.fill = white_fill
            cB.border = cell_border

            # Reviewer columns
            for r_idx, r_name in enumerate(self.reviewer_ids):
                col_idx = 3 + r_idx
                is_assigned = (self.assignment_matrix[r_idx, p_idx] == 1)
                is_champ = (self.champ_matrix is not None and self.champ_matrix[r_idx, p_idx] == 1)
                is_cochamp = (self.cochamp_matrix is not None and self.cochamp_matrix[r_idx, p_idx] == 1)

                cell = ws.cell(row_num, col_idx)
                cell.font = font_12
                cell.alignment = center_align
                cell.border = cell_border

                if is_assigned:
                    cell.value = 1
                    if is_champ:
                        cell.fill = champ_fill
                    elif is_cochamp:
                        cell.fill = cochamp_fill
                    else:
                        cell.fill = white_fill
                else:
                    cell.value = "x"
                    cell.fill = white_fill

            # Col Walkouts
            cW = ws.cell(row_num, walkouts_col, value=f'=COUNTIF({first_rev_letter}{row_num}:{last_rev_letter}{row_num},"x")')
            cW.font = font_12
            cW.alignment = center_align
            cW.fill = white_fill
            cW.border = cell_border

            # Col Reviews
            cR = ws.cell(row_num, reviews_col, value=f'=COUNTIF({first_rev_letter}{row_num}:{last_rev_letter}{row_num},"1")')
            cR.font = font_12
            cR.alignment = center_align
            cR.fill = white_fill
            cR.border = cell_border

        # Summary rows at bottom
        end_data_row = start_row + num_papers - 1
        summary_start = end_data_row + 2

        # 1. # of Reviews
        r_revs = summary_start
        ws.cell(r_revs, 2, value="# of Reviews").font = font_12_bold
        ws.cell(r_revs, 2).alignment = left_align
        ws.cell(r_revs, 2).border = cell_border
        for r_idx in range(num_reviewers):
            col_idx = 3 + r_idx
            col_let = get_column_letter(col_idx)
            c = ws.cell(r_revs, col_idx, value=f'=COUNTIF({col_let}{start_row}:{col_let}{end_data_row},"1")')
            c.font = font_12_bold
            c.alignment = center_align
            c.border = cell_border
        ws.cell(r_revs, reviews_col, value=f'=SUM({get_column_letter(reviews_col)}{start_row}:{get_column_letter(reviews_col)}{end_data_row})').font = font_12_bold
        ws.cell(r_revs, reviews_col).alignment = center_align
        ws.cell(r_revs, reviews_col).border = cell_border

        # 2. # of Walkouts
        r_walks = summary_start + 1
        ws.cell(r_walks, 2, value="# of Walkouts").font = font_12_bold
        ws.cell(r_walks, 2).alignment = left_align
        ws.cell(r_walks, 2).border = cell_border
        for r_idx in range(num_reviewers):
            col_idx = 3 + r_idx
            col_let = get_column_letter(col_idx)
            c = ws.cell(r_walks, col_idx, value=f'=COUNTIF({col_let}{start_row}:{col_let}{end_data_row},"x")')
            c.font = font_12_bold
            c.alignment = center_align
            c.border = cell_border
        ws.cell(r_walks, walkouts_col, value=f'=SUM({get_column_letter(walkouts_col)}{start_row}:{get_column_letter(walkouts_col)}{end_data_row})').font = font_12_bold
        ws.cell(r_walks, walkouts_col).alignment = center_align
        ws.cell(r_walks, walkouts_col).border = cell_border

        # 3. # of Champion Papers
        r_champs = summary_start + 2
        ws.cell(r_champs, 2, value="# of Champion Papers").font = font_12_bold
        ws.cell(r_champs, 2).alignment = left_align
        ws.cell(r_champs, 2).border = cell_border
        for r_idx, r_name in enumerate(self.reviewer_ids):
            col_idx = 3 + r_idx
            champ_count = int(np.sum(self.champ_matrix[r_idx, :])) if self.champ_matrix is not None else 0
            c = ws.cell(r_champs, col_idx, value=champ_count)
            c.font = font_12_bold
            c.alignment = center_align
            c.border = cell_border
            if champ_count > 0:
                c.fill = champ_fill

        # 4. # of Co-Champion Papers
        r_cochamps = summary_start + 3
        ws.cell(r_cochamps, 2, value="# of Co-Champion Papers").font = font_12_bold
        ws.cell(r_cochamps, 2).alignment = left_align
        ws.cell(r_cochamps, 2).border = cell_border
        for r_idx, r_name in enumerate(self.reviewer_ids):
            col_idx = 3 + r_idx
            cochamp_count = int(np.sum(self.cochamp_matrix[r_idx, :])) if self.cochamp_matrix is not None else 0
            c = ws.cell(r_cochamps, col_idx, value=cochamp_count)
            c.font = font_12_bold
            c.alignment = center_align
            c.border = cell_border
            if cochamp_count > 0:
                c.fill = cochamp_fill

        # 5. Role
        r_role = summary_start + 4
        ws.cell(r_role, 2, value="Role").font = font_12_bold
        ws.cell(r_role, 2).alignment = left_align
        ws.cell(r_role, 2).border = cell_border
        chair = getattr(self.problem.config, "chair", "Shanshan Xie") if hasattr(self.problem, "config") else "Shanshan Xie"
        cochair = getattr(self.problem.config, "cochair", "Yoonmyung Lee") if hasattr(self.problem, "config") else "Yoonmyung Lee"
        for r_idx, r_name in enumerate(self.reviewer_ids):
            col_idx = 3 + r_idx
            role_val = "Subcom Chair" if r_name == chair else ("Subcom Co-Chair" if r_name == cochair else "")
            c = ws.cell(r_role, col_idx, value=role_val)
            c.font = font_12_bold
            c.alignment = center_align
            c.border = cell_border

        # Adjust column widths for clean display
        ws.column_dimensions["A"].width = 10
        ws.column_dimensions["B"].width = 50
        for col_idx in range(3, 3 + num_reviewers):
            ws.column_dimensions[get_column_letter(col_idx)].width = 18
        ws.column_dimensions[get_column_letter(walkouts_col)].width = 16
        ws.column_dimensions[get_column_letter(reviews_col)].width = 14

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        wb.save(output_path)
        print(f"Saved final reviewer assignment spreadsheet to {output_path}")
        return output_path
