"""Reviewer Assignment Package.

This package provides tools for parsing reviewer/paper data, scrubbing paper
affiliations, and running a Mixed-Integer Linear Program (MILP) solver to
assign papers to reviewers subject to expertise, conflicts, and workload constraints.
"""

from .config import Config
from .data_structures import (
    AffiliationData,
    ReviewerExpertise,
    PaperArea,
    MustReview,
    ConflictOfInterest,
    ReviewerAssignmentProblem,
)
from .scrubber import AffiliationScrubber
from .solver import ReviewerAssignmentSolver
from .reporter import ReviewerAssignmentReporter

__all__ = [
    "Config",
    "AffiliationData",
    "ReviewerExpertise",
    "PaperArea",
    "MustReview",
    "ConflictOfInterest",
    "ReviewerAssignmentProblem",
    "AffiliationScrubber",
    "ReviewerAssignmentSolver",
    "ReviewerAssignmentReporter",
]
