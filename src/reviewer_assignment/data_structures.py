"""Data structures representing the reviewer assignment data inputs."""

import os
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import numpy as np
from .config import Config
from pathlib import Path

@dataclass
class AffiliationData:
    """Represents the affiliations of papers."""

    paper_ids: List[int]
    affiliations: List[str]


@dataclass
class ReviewerExpertise:
    """Represents reviewer expertise ratings across different areas."""

    reviewer_ids: List[str]
    areas: List[str]
    matrix: np.ndarray  # Shape: (num_reviewers, num_areas)


@dataclass
class PaperArea:
    """Represents paper relevance scores across different areas."""

    paper_ids: List[int]
    areas: List[str]
    matrix: np.ndarray  # Shape: (num_papers, num_areas)


@dataclass
class MustReview:
    """Represents forced reviewer-paper assignments."""

    paper_ids: List[int]
    reviewer_ids: List[str]
    matrix: np.ndarray  # Shape: (num_reviewers, num_papers)


@dataclass
class ConflictOfInterest:
    """Represents conflicts of interest preventing reviewer-paper assignments."""

    paper_ids: List[int]
    reviewer_ids: List[str]
    matrix: np.ndarray  # Shape: (num_reviewers, num_papers)


class ReviewerAssignmentProblem:
    """Encapsulates the complete dataset for the reviewer assignment problem."""

    def __init__(
        self,
        config: Config,
        reviewer_expertise: ReviewerExpertise,
        paper_area: PaperArea,
        must_review: MustReview,
        coi: ConflictOfInterest,
    ):
        self.config = config
        self.reviewer_expertise = reviewer_expertise
        self.paper_area = paper_area
        self.must_review = must_review
        self.coi = coi

        # Validate dimensions
        assert (
            len(self.reviewer_expertise.reviewer_ids) == config.num_reviewers
        ), "Reviewer count mismatch in reviewer_expertise"
        assert (
            len(self.paper_area.paper_ids) == config.num_papers
        ), "Paper count mismatch in paper_area"

    @classmethod
    def load(cls, config: Config) -> "ReviewerAssignmentProblem":
        """Loads data from CSV files and aligns indices.

        Args:
            config: A Config instance containing file paths.

        Returns:
            A ReviewerAssignmentProblem instance.
        """
        # Load reviewer expertise
        df_exp = pd.read_csv(Path(config.input_files_dir) / Path(config.files["reviewer_expertise"]))
        
        # Identify Firstname and Lastname columns strictly
        cols_lower = [c.strip().lower() for c in df_exp.columns]
        fname_col = next((c for c, cl in zip(df_exp.columns, cols_lower) if cl in ["firstname", "first_name", "first name"]), None)
        lname_col = next((c for c, cl in zip(df_exp.columns, cols_lower) if cl in ["lastname", "last_name", "last name"]), None)

        if not fname_col or not lname_col:
            raise ValueError(
                "reviewer_expertise.csv must contain 'Firstname' and 'Lastname' columns."
            )

        # Combine Firstname and Lastname using pandas to form "Firstname Lastname"
        reviewer_ids = (
            df_exp[fname_col].astype(str).str.strip() + " " + df_exp[lname_col].astype(str).str.strip()
        ).str.strip().tolist()

        # Extract expertise areas strictly starting after the 'Areas' column (or after metadata columns)
        cols_list = list(df_exp.columns)
        summary_prefixes = ["average", "avg", "has a 10", "fill status", "status", "total", "comment", "note", "unnamed"]

        if any(cl in ["areas", "area"] for cl in cols_lower):
            areas_idx = next(i for i, cl in enumerate(cols_lower) if cl in ["areas", "area"])
            candidate_cols = cols_list[areas_idx + 1:]
        else:
            metadata_cols = {"firstname", "first_name", "first name", "lastname", "last_name", "last name", "affiliation", "affiliations", "areas", "area"}
            candidate_cols = [c for c, cl in zip(cols_list, cols_lower) if cl not in metadata_cols]

        areas = []
        for c in candidate_cols:
            cl = c.strip().lower()
            if not any(cl.startswith(prefix) for prefix in summary_prefixes):
                areas.append(c)

        if not areas:
            raise ValueError("No expertise area columns found in reviewer_expertise.csv.")

        matrix_exp = df_exp[areas].apply(pd.to_numeric).to_numpy() # Map the content portion into a numpy matrix.

        if len(reviewer_ids) != config.num_reviewers:
            raise ValueError(
                f"Number of reviewers in reviewer_expertise file ({len(reviewer_ids)}) "
                f"does not match num_reviewers in configuration ({config.num_reviewers})"
            )

        # Check bounds: expertise scores must be in [0, 10]
        if not np.all((matrix_exp >= 0) & (matrix_exp <= 10)):
            raise ValueError(
                "All expertise scores in reviewer_expertise must be between 0 and 10 (inclusive)."
            )

        reviewer_exp = ReviewerExpertise(
            reviewer_ids=reviewer_ids, areas=areas, matrix=matrix_exp
        )

        # Load paper technical areas (or fall back to paper_area.csv) and generate paperID_areas.csv in intermediate_data
        tech_areas_key = "paper_technical_areas"
        tech_areas_file = config.files.get(tech_areas_key, "paper_technical_areas.csv")
        tech_areas_path = Path(config.input_files_dir) / Path(tech_areas_file)

        if os.path.exists(tech_areas_path):
            df_tech = pd.read_csv(tech_areas_path)
            cols_tech_lower = [str(c).strip().lower() for c in df_tech.columns]

            pid_col = next((c for c, cl in zip(df_tech.columns, cols_tech_lower) if cl in ["paper_id", "paper_id", "paperid", "id"]), df_tech.columns[0])
            title_col = next((c for c, cl in zip(df_tech.columns, cols_tech_lower) if cl in ["title", "paper_title", "papertitle"]), None)

            # Prune out paper title column
            if title_col and title_col in df_tech.columns:
                df_p_area = df_tech.drop(columns=[title_col])
            else:
                df_p_area = df_tech.copy()

            # Drop trailing/unnamed columns that commonly appear from Excel exports
            df_p_area = df_p_area.loc[:, ~df_p_area.columns.astype(str).str.contains(r'^Unnamed', case=False)]

            # Normalize common area name variations (e.g. Powermanagement -> Pwrmgmt)
            area_synonyms = {
                "powermanagement": "Pwrmgmt",
                "power management": "Pwrmgmt",
            }
            rename_map = {col: "Pwrmgmt" for col in df_p_area.columns if str(col).strip().lower() in area_synonyms and "Pwrmgmt" in areas}
            if rename_map:
                df_p_area = df_p_area.rename(columns=rename_map)

            # Ensure paper ID column is named 'paper_id'
            if pid_col != "paper_id":
                df_p_area = df_p_area.rename(columns={pid_col: "paper_id"})
                pid_col = "paper_id"

            # Save pruned paperID_areas.csv into intermediate_data or intermediate_files
            paper_id_areas_out = config.files.get("paperID_areas", "intermediate_data/paperID_areas.csv")
            paper_id_areas_path = Path(paper_id_areas_out)
            if not paper_id_areas_path.is_absolute():
                if not any(part in ["intermediate_files", "intermediate_data", "output_files"] for part in paper_id_areas_path.parts):
                    paper_id_areas_path = Path(config.output_files_dir) / paper_id_areas_path

            os.makedirs(paper_id_areas_path.parent, exist_ok=True)
            df_p_area.to_csv(paper_id_areas_path, index=False)
            print(f"Pruned paper titles and saved paperID_areas.csv to '{paper_id_areas_path}'")
        else:
            # Fallback to paper_area.csv if paper_technical_areas.csv is not present
            paper_area_file = config.files.get("paper_area", "paper_area.csv")
            paper_area_path = Path(config.input_files_dir) / Path(paper_area_file)
            df_p_area = pd.read_csv(paper_area_path)
            pid_col = df_p_area.columns[0]

        paper_col = pid_col
        paper_ids = df_p_area[paper_col].astype(int).tolist()

        if len(paper_ids) != config.num_papers:
            raise ValueError(
                f"Number of papers in paper technical areas file ({len(paper_ids)}) "
                f"does not match num_papers in configuration ({config.num_papers})"
            )

        # Ensure expertise areas in paper technical areas file match those in reviewer_expertise.csv
        paper_areas = [c for c in df_p_area.columns if c != paper_col]
        if set(paper_areas) != set(areas):
            missing_in_exp = set(paper_areas) - set(areas)
            missing_in_paper = set(areas) - set(paper_areas)
            details = []
            if missing_in_exp:
                details.append(
                    f"  - Areas in paper technical areas missing from reviewer_expertise.csv: {sorted(list(missing_in_exp))}"
                )
            if missing_in_paper:
                details.append(
                    f"  - Areas in reviewer_expertise.csv missing from paper technical areas: {sorted(list(missing_in_paper))}"
                )
            raise ValueError(
                "Areas in paper technical areas file do not match those in reviewer_expertise.csv.\n"
                + "\n".join(details)
            )

        # Align columns to match the reviewer expertise areas ordering, filling blank cells with 0.
        matrix_p_area = df_p_area[areas].apply(pd.to_numeric).fillna(0).to_numpy()

        # Check bounds: paper relevance scores must be in [0, 10]
        if not np.all((matrix_p_area >= 0) & (matrix_p_area <= 10)):
            raise ValueError(
                "All paper relevance scores in paper technical areas file must be between 0 and 10 (inclusive)."
            )

        p_area = PaperArea(
            paper_ids=paper_ids, areas=areas, matrix=matrix_p_area
        )


        # Helper to align sparse CSVs (must_review & coi) with loaded paper_ids and reviewer_ids
        def load_sparse_matrix(path: str) -> np.ndarray:
            df = pd.read_csv(path)
            row_col = df.columns[0]

            csv_paper_ids = df[row_col].astype(int).tolist()
            csv_reviewer_ids = [str(r).strip() for r in df.columns[1:].tolist()]

            # Verify that paper IDs match
            unrecognized_papers = set(csv_paper_ids) - set(paper_ids)
            if unrecognized_papers:
                raise ValueError(
                    f"Unrecognized paper IDs in file {path}: {unrecognized_papers}. "
                    "All paper IDs in must_review / coi must exist in paper_area."
                )

            # Verify that reviewer IDs match strictly by name
            unrecognized_reviewers = set(csv_reviewer_ids) - set(reviewer_ids)
            if unrecognized_reviewers:
                raise ValueError(
                    f"Unrecognized reviewer IDs in file {path}: {unrecognized_reviewers}.\n"
                    f"Reviewer column headers in {path} must match reviewer names in reviewer_expertise.csv."
                )

            df = df.set_index(row_col)
            df_aligned = df.reindex(index=paper_ids, columns=reviewer_ids).fillna(0)
            return df_aligned.to_numpy().T

        # Load and align must review
        must_review_matrix = load_sparse_matrix(Path(config.input_files_dir) / Path(config.files["must_review"]))
        must_review = MustReview(
            paper_ids=paper_ids,
            reviewer_ids=reviewer_ids,
            matrix=must_review_matrix,
        )

        # Load and align coi
        coi_matrix = load_sparse_matrix(Path(config.input_files_dir) / Path(config.files["coi"]))
        coi = ConflictOfInterest(
            paper_ids=paper_ids, reviewer_ids=reviewer_ids, matrix=coi_matrix
        )

        return cls(
            config=config,
            reviewer_expertise=reviewer_exp,
            paper_area=p_area,
            must_review=must_review,
            coi=coi,
        )

    def compute_matching_matrix(self) -> np.ndarray:
        """Computes matching scores for all reviewer-paper pairs.

        reviewer_paper_matching = reviewer_matrix * paper_areas_matrix^T

        Returns:
            A numpy array of shape (num_reviewers, num_papers).
        """
        # (num_reviewers x num_areas) * (num_areas x num_papers) -> (num_reviewers x num_papers)
        return np.dot(self.reviewer_expertise.matrix, self.paper_area.matrix.T)

    def save_matching_matrix(self, output_path: str = "intermediate_data/reviewer_matching.csv") -> None:
        """Computes and saves the reviewer-paper matching matrix to a CSV file.

        Args:
            output_path: Path where the CSV file should be saved.
        """
        matching_matrix = self.compute_matching_matrix()
        df = pd.DataFrame(
            matching_matrix,
            index=self.reviewer_expertise.reviewer_ids,
            columns=self.paper_area.paper_ids,
        )
        df.index.name = "reviewer_id"

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        df.to_csv(output_path)
        print(f"Saved reviewer matching matrix to {output_path}")
