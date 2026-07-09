"""MILP Solver for the Reviewer Assignment Problem."""

from typing import Tuple
import pulp
import numpy as np
from .data_structures import ReviewerAssignmentProblem


class ReviewerAssignmentSolver:
    """Sets up and solves the reviewer assignment optimization problem."""

    def __init__(self, problem: ReviewerAssignmentProblem):
        self.problem = problem

    def solve(self) -> Tuple[np.ndarray, float]:
        """Solves the MILP for reviewer assignment.

        Returns:
            A tuple of (assignment_matrix, objective_value), where:
                - assignment_matrix: A binary numpy array of shape
                  (num_reviewers, num_papers) with 1s indicating assignments.
                - objective_value: The value of the optimized objective function.
        """
        prob = pulp.LpProblem("Reviewer_Assignment", pulp.LpMaximize)

        num_reviewers = self.problem.config.num_reviewers
        num_papers = self.problem.config.num_papers

        #Question: what is this tuple type?
        # Decision variables: x[r, p] = 1 if reviewer r is assigned to paper p, 0 otherwise.
        x = pulp.LpVariable.dicts(
            "assign",
            ((r, p) for r in range(num_reviewers) for p in range(num_papers)),
            cat=pulp.LpBinary,
        )

        # Compute matching matrix (reviewer_expertise * paper_area^T)
        matching_matrix = self.problem.compute_matching_matrix()

        #Question
        # Objective Function: Maximize the matching score dot product
        prob += pulp.lpSum(
            matching_matrix[r, p] * x[r, p]
            for r in range(num_reviewers)
            for p in range(num_papers)
        )

        # Constraints
        coi = self.problem.coi.matrix
        must = self.problem.must_review.matrix

        # 1. COI and Must Review constraints
        for r in range(num_reviewers):
            for p in range(num_papers):
                r_id = self.problem.reviewer_expertise.reviewer_ids[r]
                p_id = self.problem.paper_area.paper_ids[p]
                if coi[r, p] == 1 and must[r, p] == 1:
                    raise ValueError(
                        f"Conflict of interest and Must-review are both active for Reviewer {r_id} and Paper {p_id}"
                    )
                if coi[r, p] == 1:
                    prob += x[r, p] == 0
                if must[r, p] == 1:
                    prob += x[r, p] == 1

        # 2. Reviewer workload constraints
        min_rev = self.problem.config.min_reviews_per_reviewer
        max_rev = self.problem.config.max_reviews_per_reviewer
        for r in range(num_reviewers):
            prob += pulp.lpSum(x[r, p] for p in range(num_papers)) >= min_rev
            prob += pulp.lpSum(x[r, p] for p in range(num_papers)) <= max_rev

        # 3. Paper coverage constraints
        min_pap = self.problem.config.min_reviews_per_paper
        for p in range(num_papers):
            prob += pulp.lpSum(x[r, p] for r in range(num_reviewers)) >= min_pap

        # Solve the model using default PuLP solver (CBC)
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))

        if status != pulp.LpStatusOptimal:
            raise ValueError(
                f"MILP Solver did not find an optimal solution. Status: {pulp.LpStatus[status]}"
            )

        # Extract solution matrix
        assignment_matrix = np.zeros((num_reviewers, num_papers), dtype=int)
        for r in range(num_reviewers):
            for p in range(num_papers):
                if pulp.value(x[r, p]) > 0.5:
                    assignment_matrix[r, p] = 1

        objective_value = pulp.value(prob.objective)
        return assignment_matrix, objective_value
