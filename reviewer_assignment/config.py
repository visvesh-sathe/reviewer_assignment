"""Configuration parser for reviewer assignment."""
#Question: how do i cast a yaml file into a dataclass

from pathlib import Path
import os
from dataclasses import dataclass, field
from typing import Dict, Any
import yaml


@dataclass
class Config:
    """Stores reviewer assignment parameters and file paths loaded from config.yaml."""

    num_reviewers: int
    num_papers: int
    min_reviews_per_reviewer: int
    max_reviews_per_reviewer: int
    min_reviews_per_paper: int
    input_files_dir: str
    report_files_dir: str
    output_files_dir: str
    files: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Loads configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            An instance of Config.
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        config = cls(
            num_reviewers=int(data["num_reviewers"]),
            num_papers=int(data["num_papers"]),
            min_reviews_per_reviewer=int(data["min_reviews_per_reviewer"]),
            max_reviews_per_reviewer=int(data["max_reviews_per_reviewer"]),
            min_reviews_per_paper=int(data["min_reviews_per_paper"]),
            input_files_dir = data["input_files_dir"],
            report_files_dir = data["report_files_dir"],
            output_files_dir = data["output_files_dir"],
            files=data.get("files", {}),
        )
        config.validate()
        return config

    def validate(self) -> None:
        """Validates configuration parameters and file presence.

        Raises:
            ValueError: If configurations are invalid or files are missing.
        """
        if self.num_reviewers <= 0:
            raise ValueError(f"num_reviewers must be positive, got {self.num_reviewers}")
        if self.num_papers <= 0:
            raise ValueError(f"num_papers must be positive, got {self.num_papers}")
        if self.min_reviews_per_reviewer < 0:
            raise ValueError("min_reviews_per_reviewer cannot be negative")
        if self.max_reviews_per_reviewer < self.min_reviews_per_reviewer:
            raise ValueError(
                f"max_reviews_per_reviewer ({self.max_reviews_per_reviewer}) must be "
                f"greater than or equal to min_reviews_per_reviewer ({self.min_reviews_per_reviewer})"
            )
        if self.min_reviews_per_paper < 0:
            raise ValueError("min_reviews_per_paper cannot be negative")

        # Check mathematical workload viability
        min_total_reviews_needed = self.num_papers * self.min_reviews_per_paper
        max_total_reviews_possible = self.num_reviewers * self.max_reviews_per_reviewer
        if max_total_reviews_possible < min_total_reviews_needed:
            raise ValueError(
                f"Infeasible workload constraints: papers require at least {min_total_reviews_needed} total reviews, "
                f"but reviewers can only perform at most {max_total_reviews_possible} total reviews."
            )

#Update me to add output files too
        required_files = [
            "affiliations",
            "reviewer_expertise",
            "paper_area",
            "must_review",
            "coi",
        ]
        for key in required_files:
            if key not in self.files:
                raise ValueError(
                    f"Missing required file path under files in config: '{key}'"
                )
            file_path = self.input_files_dir / Path(self.files[key])
            if not os.path.exists(file_path):
                raise ValueError(
                    f"File specified for '{key}' does not exist: '{file_path}'"
                )
