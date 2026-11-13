"""Configuration parser for reviewer assignment."""
#Question: how do i cast a yaml file into a dataclass

from pathlib import Path
import os
import math
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
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
    reviews_per_paper: int = 4
    max_extra_reviews: int = 2
    chair: str = ""
    cochair: str = ""
    files: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Loads configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            An instance of Config.
        """
        cfg_path = Path(path).resolve()
        with open(cfg_path, "r") as f:
            data = yaml.safe_load(f)

        # Infer base directory from config file location
        if cfg_path.parent.name == "input_files":
            base_dir = cfg_path.parent.parent
        else:
            base_dir = cfg_path.parent

        def resolve_dir(d_name: str) -> str:
            d_path = Path(d_name)
            if d_path.is_absolute() or d_path.exists():
                return str(d_path)
            if (base_dir / d_path).exists() or not d_path.exists():
                return str(base_dir / d_path)
            return str(d_path)

        input_files_dir = resolve_dir(data.get("input_files_dir", "input_files"))
        report_files_dir = resolve_dir(data.get("report_files_dir", "reports"))
        output_files_dir = resolve_dir(data.get("output_files_dir", "output_files"))

        num_reviewers = int(data["num_reviewers"])
        num_papers = int(data["num_papers"])
        reviews_per_paper = int(data.get("reviews_per_paper", data.get("min_reviews_per_paper", 4)))
        min_reviews_per_paper = reviews_per_paper
        max_extra_reviews = int(data.get("max_extra_reviews", 2))

        # Dynamically compute min_reviews_per_reviewer if not explicitly provided
        if "min_reviews_per_reviewer" in data and data["min_reviews_per_reviewer"] is not None:
            min_reviews_per_reviewer = int(data["min_reviews_per_reviewer"])
        else:
            min_reviews_per_reviewer = math.floor((num_papers * reviews_per_paper) / num_reviewers)

        # Dynamically compute max_reviews_per_reviewer if not explicitly provided
        if "max_reviews_per_reviewer" in data and data["max_reviews_per_reviewer"] is not None:
            max_reviews_per_reviewer = int(data["max_reviews_per_reviewer"])
        else:
            max_reviews_per_reviewer = min_reviews_per_reviewer + max_extra_reviews

        config = cls(
            num_reviewers=num_reviewers,
            num_papers=num_papers,
            min_reviews_per_reviewer=min_reviews_per_reviewer,
            max_reviews_per_reviewer=max_reviews_per_reviewer,
            min_reviews_per_paper=min_reviews_per_paper,
            reviews_per_paper=reviews_per_paper,
            max_extra_reviews=max_extra_reviews,
            input_files_dir=input_files_dir,
            report_files_dir=report_files_dir,
            output_files_dir=output_files_dir,
            chair=str(data.get("chair", "")).strip(),
            cochair=str(data.get("cochair", "")).strip(),
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
        if self.reviews_per_paper <= 0:
            raise ValueError("reviews_per_paper must be positive")
        if self.min_reviews_per_paper <= 0:
            raise ValueError("min_reviews_per_paper must be positive")
        if self.max_extra_reviews < 0:
            raise ValueError("max_extra_reviews cannot be negative")

        # Check mathematical workload viability
        total_reviews_needed = self.num_papers * self.reviews_per_paper
        max_total_reviews_possible = self.num_reviewers * self.max_reviews_per_reviewer
        min_total_reviews_possible = self.num_reviewers * self.min_reviews_per_reviewer
        if max_total_reviews_possible < total_reviews_needed:
            raise ValueError(
                f"Infeasible workload constraints: papers require {total_reviews_needed} total reviews, "
                f"but reviewers can only perform at most {max_total_reviews_possible} total reviews."
            )
        if min_total_reviews_possible > total_reviews_needed:
            raise ValueError(
                f"Infeasible workload constraints: papers require {total_reviews_needed} total reviews, "
                f"but reviewers are required to perform at least {min_total_reviews_possible} total reviews."
            )

#Update me to add output files too
        required_files = [
            "reviewer_expertise",
            "must_review",
            "coi",
        ]
        for key in required_files:
            if key not in self.files:
                raise ValueError(
                    f"Missing required file path under files in config: '{key}'"
                )
            file_path = Path(self.input_files_dir) / Path(self.files[key])
            if not os.path.exists(file_path):
                raise ValueError(
                    f"File specified for '{key}' does not exist: '{file_path}'"
                )

        has_paper_tech = "paper_technical_areas" in self.files and os.path.exists(Path(self.input_files_dir) / Path(self.files["paper_technical_areas"]))
        has_paper_area = "paper_area" in self.files and os.path.exists(Path(self.input_files_dir) / Path(self.files["paper_area"]))
        if not has_paper_tech and not has_paper_area:
            raise ValueError(
                f"Neither 'paper_technical_areas' nor 'paper_area' file found in '{self.input_files_dir}'."
            )

