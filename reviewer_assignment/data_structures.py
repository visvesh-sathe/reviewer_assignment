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
        df_exp = pd.read_csv(config.input_files_dir / Path(config.files["reviewer_expertise"]))
        if "Firstname" in df_exp.columns and "Lastname" in df_exp.columns:
            reviewer_ids = [
                f"{str(fname).strip()} {str(lname).strip()}".strip()
                for fname, lname in zip(df_exp["Firstname"], df_exp["Lastname"])
            ]
            areas = [c for c in df_exp.columns if c not in ["Firstname", "Lastname"]]
        else:
            reviewer_ids = [
                f"{str(fname).strip()} {str(lname).strip()}".strip()
                for fname, lname in zip(df_exp.iloc[:, 0], df_exp.iloc[:, 1])
            ]
            areas = df_exp.columns[2:].tolist()

        matrix_exp = df_exp[areas].to_numpy() #Map the content portion of the matrix into a numpy matrix.

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

        # Load paper area
        df_p_area = pd.read_csv(config.input_files_dir / Path(config.files["paper_area"]))
        paper_col = df_p_area.columns[0]
        paper_ids = df_p_area[paper_col].astype(int).tolist() #Extract the paper ids as a string.

        if len(paper_ids) != config.num_papers:
            raise ValueError(
                f"Number of papers in paper_area file ({len(paper_ids)}) "
                f"does not match num_papers in configuration ({config.num_papers})"
            )

        # Ensure all required areas are present in paper_area
        missing_areas = set(df_p_area.columns[1:]) - set(areas) 
        if missing_areas:
            raise ValueError(
                f"The following areas among the submitted papers have no reviewer expertise: {missing_areas} \n Do you have a typo? "
            )
        # Align columns to match the reviewer expertise areas ordering. Use the areas from the reviewers. That's what matters.
        # It's possible you'll get papers that simply won't span reviewer expertise.
        matrix_p_area = df_p_area[areas].to_numpy()

        # Check bounds: paper relevance scores must be in [0, 10]
        if not np.all((matrix_p_area >= 0) & (matrix_p_area <= 10)):
            raise ValueError(
                "All paper relevance scores in paper_area must be between 0 and 10 (inclusive)."
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

            # Match columns either by exact reviewer ID strings or positionally if count matches
            if set(csv_reviewer_ids) == set(reviewer_ids):
                df = df.set_index(row_col)
                df_aligned = df.reindex(index=paper_ids, columns=reviewer_ids).fillna(0)
                return df_aligned.to_numpy().T
            elif len(csv_reviewer_ids) == len(reviewer_ids):
                df = df.set_index(row_col)
                df_aligned = df.reindex(index=paper_ids).fillna(0)
                df_aligned.columns = reviewer_ids
                return df_aligned.to_numpy().T
            else:
                unrecognized_reviewers = set(csv_reviewer_ids) - set(reviewer_ids)
                raise ValueError(
                    f"Unrecognized reviewer IDs in file {path}: {unrecognized_reviewers}. "
                    "All reviewer IDs in must_review / coi must exist in reviewer_expertise."
                )

        # Load and align must review
        must_review_matrix = load_sparse_matrix(config.input_files_dir / Path(config.files["must_review"]))
        must_review = MustReview(
            paper_ids=paper_ids,
            reviewer_ids=reviewer_ids,
            matrix=must_review_matrix,
        )

        # Load and align coi
        coi_matrix = load_sparse_matrix(config.input_files_dir / Path(config.files["coi"]))
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
