"""MILP Solver for the Reviewer Assignment Problem."""

import math
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

        # Decision variables: x[r, p] = 1 if reviewer r is assigned to paper p, 0 otherwise.
        x = {
            (r, p): pulp.LpVariable(f"assign_{r}_{p}", cat=pulp.LpBinary)
            for r in range(num_reviewers)
            for p in range(num_papers)
        }

        # Compute matching matrix (reviewer_expertise * paper_area^T)
        matching_matrix = self.problem.compute_matching_matrix()

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

    def solve_champion(self, assignment_matrix: np.ndarray) -> Tuple[np.ndarray, float]:
        """Solves the MILP for champion reviewer assignment.

        Args:
            assignment_matrix: Binary assignment matrix from the initial solve.

        Returns:
            A tuple of (champ_matrix, objective_value), where:
                - champ_matrix: A binary numpy array of shape
                  (num_reviewers, num_papers) with 1s indicating champion assignments.
                - objective_value: The value of the optimized objective function.
        """
        prob = pulp.LpProblem("Champion_Assignment", pulp.LpMaximize)

        num_reviewers = self.problem.config.num_reviewers
        num_papers = self.problem.config.num_papers

        # Decision variables: y[r, p] = 1 if reviewer r is champion for paper p, 0 otherwise.
        y = {
            (r, p): pulp.LpVariable(f"champion_{r}_{p}", cat=pulp.LpBinary)
            for r in range(num_reviewers)
            for p in range(num_papers)
        }

        # Compute matching matrix (reviewer_expertise * paper_area^T)
        matching_matrix = self.problem.compute_matching_matrix()

        # Objective Function: Maximize the matching score dot product for champions
        prob += pulp.lpSum(
            matching_matrix[r, p] * y[r, p]
            for r in range(num_reviewers)
            for p in range(num_papers)
        )

        # Constraints
        coi = self.problem.coi.matrix
        champ_coi = 1 - assignment_matrix

        chair = self.problem.config.chair
        cochair = self.problem.config.cochair

        # 1. COI, non-reviewer, and chair/cochair constraints for champion
        for r in range(num_reviewers):
            r_id = self.problem.reviewer_expertise.reviewer_ids[r]
            is_chair_or_cochair = (r_id == chair or r_id == cochair)
            for p in range(num_papers):
                if coi[r, p] == 1 or champ_coi[r, p] == 1 or is_chair_or_cochair:
                    prob += y[r, p] == 0

        # 2. Each paper must have exactly one champion
        for p in range(num_papers):
            prob += pulp.lpSum(y[r, p] for r in range(num_reviewers)) == 1

        # 3. Champion workload constraints
        max_champ = math.ceil(num_papers / num_reviewers) + 1
        min_champ = max(0, math.floor(num_papers / num_reviewers) - 1)
        for r in range(num_reviewers):
            r_id = self.problem.reviewer_expertise.reviewer_ids[r]
            if r_id == chair or r_id == cochair:
                prob += pulp.lpSum(y[r, p] for p in range(num_papers)) == 0
            else:
                prob += pulp.lpSum(y[r, p] for p in range(num_papers)) >= min_champ
                prob += pulp.lpSum(y[r, p] for p in range(num_papers)) <= max_champ

        # Solve the model
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))

        if status != pulp.LpStatusOptimal:
            raise ValueError(
                f"MILP Solver did not find an optimal solution for Champion Assignment. Status: {pulp.LpStatus[status]}"
            )

        # Extract solution matrix
        champ_matrix = np.zeros((num_reviewers, num_papers), dtype=int)
        for r in range(num_reviewers):
            for p in range(num_papers):
                if pulp.value(y[r, p]) > 0.5:
                    champ_matrix[r, p] = 1

        # Post-validation checks
        for p in range(num_papers):
            assigned_champs = np.sum(champ_matrix[:, p])
            if assigned_champs != 1:
                raise ValueError(
                    f"Paper {self.problem.paper_area.paper_ids[p]} has {assigned_champs} champions, expected 1."
                )

        for r in range(num_reviewers):
            workload = np.sum(champ_matrix[r, :])
            r_id = self.problem.reviewer_expertise.reviewer_ids[r]
            if r_id == chair or r_id == cochair:
                if workload != 0:
                    raise ValueError(
                        f"Chair/Co-chair {r_id} champion workload is {workload}, expected 0."
                    )
            else:
                if workload > max_champ or workload < min_champ:
                    raise ValueError(
                        f"Reviewer {r_id} champion workload is {workload}, out of bounds [{min_champ}, {max_champ}]."
                    )

        for r in range(num_reviewers):
            for p in range(num_papers):
                if champ_matrix[r, p] == 1:
                    r_id = self.problem.reviewer_expertise.reviewer_ids[r]
                    p_id = self.problem.paper_area.paper_ids[p]
                    if r_id == chair or r_id == cochair:
                        raise ValueError(
                            f"Reviewer {r_id} is champion for paper {p_id} but is chair/co-chair."
                        )
                    if assignment_matrix[r, p] != 1:
                        raise ValueError(
                            f"Reviewer {r_id} is champion for paper {p_id} but is not an assigned reviewer."
                        )
                    if coi[r, p] == 1:
                        raise ValueError(
                            f"Reviewer {r_id} is champion for paper {p_id} but has a Conflict of Interest."
                        )

        objective_value = pulp.value(prob.objective)
        return champ_matrix, objective_value

    def solve_cochampion(
        self, assignment_matrix: np.ndarray, champ_matrix: np.ndarray
    ) -> Tuple[np.ndarray, float]:
        """Solves the MILP for co-champion reviewer assignment.

        Args:
            assignment_matrix: Binary assignment matrix from the initial solve.
            champ_matrix: Binary champion assignment matrix.

        Returns:
            A tuple of (cochamp_matrix, objective_value), where:
                - cochamp_matrix: A binary numpy array of shape
                  (num_reviewers, num_papers) with 1s indicating co-champion assignments.
                - objective_value: The value of the optimized objective function.
        """
        prob = pulp.LpProblem("Cochampion_Assignment", pulp.LpMaximize)

        num_reviewers = self.problem.config.num_reviewers
        num_papers = self.problem.config.num_papers

        # Decision variables: z[r, p] = 1 if reviewer r is co-champion for paper p, 0 otherwise.
        z = {
            (r, p): pulp.LpVariable(f"cochampion_{r}_{p}", cat=pulp.LpBinary)
            for r in range(num_reviewers)
            for p in range(num_papers)
        }

        # Compute matching matrix (reviewer_expertise * paper_area^T)
        matching_matrix = self.problem.compute_matching_matrix()

        # Objective Function: Maximize the matching score dot product for co-champions
        prob += pulp.lpSum(
            matching_matrix[r, p] * z[r, p]
            for r in range(num_reviewers)
            for p in range(num_papers)
        )

        # Constraints
        coi = self.problem.coi.matrix
        champ_coi = 1 - assignment_matrix
        cochamp_coi = champ_coi + champ_matrix

        chair = self.problem.config.chair
        cochair = self.problem.config.cochair

        # 1. COI, non-reviewer, champion, and chair/cochair constraints for co-champion
        for r in range(num_reviewers):
            r_id = self.problem.reviewer_expertise.reviewer_ids[r]
            is_chair_or_cochair = (r_id == chair or r_id == cochair)
            for p in range(num_papers):
                if coi[r, p] == 1 or cochamp_coi[r, p] == 1 or is_chair_or_cochair:
                    prob += z[r, p] == 0

        # 2. Each paper must have exactly one co-champion
        for p in range(num_papers):
            prob += pulp.lpSum(z[r, p] for r in range(num_reviewers)) == 1

        # 3. Co-champion workload constraints
        max_cochamp = math.ceil(num_papers / num_reviewers) + 1
        for r in range(num_reviewers):
            r_id = self.problem.reviewer_expertise.reviewer_ids[r]
            if r_id == chair or r_id == cochair:
                prob += pulp.lpSum(z[r, p] for p in range(num_papers)) == 0
            else:
                prob += pulp.lpSum(z[r, p] for p in range(num_papers)) <= max_cochamp

        # Solve the model
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))

        if status != pulp.LpStatusOptimal:
            raise ValueError(
                f"MILP Solver did not find an optimal solution for Co-champion Assignment. Status: {pulp.LpStatus[status]}"
            )

        # Extract solution matrix
        cochamp_matrix = np.zeros((num_reviewers, num_papers), dtype=int)
        for r in range(num_reviewers):
            for p in range(num_papers):
                if pulp.value(z[r, p]) > 0.5:
                    cochamp_matrix[r, p] = 1

        # Post-validation checks
        for p in range(num_papers):
            assigned_cochamps = np.sum(cochamp_matrix[:, p])
            if assigned_cochamps != 1:
                raise ValueError(
                    f"Paper {self.problem.paper_area.paper_ids[p]} has {assigned_cochamps} co-champions, expected 1."
                )

        for r in range(num_reviewers):
            workload = np.sum(cochamp_matrix[r, :])
            r_id = self.problem.reviewer_expertise.reviewer_ids[r]
            if r_id == chair or r_id == cochair:
                if workload != 0:
                    raise ValueError(
                        f"Chair/Co-chair {r_id} co-champion workload is {workload}, expected 0."
                    )
            else:
                if workload > max_cochamp:
                    raise ValueError(
                        f"Reviewer {r_id} co-champion workload is {workload}, exceeds maximum {max_cochamp}."
                    )

        for r in range(num_reviewers):
            for p in range(num_papers):
                if cochamp_matrix[r, p] == 1:
                    r_id = self.problem.reviewer_expertise.reviewer_ids[r]
                    p_id = self.problem.paper_area.paper_ids[p]
                    if r_id == chair or r_id == cochair:
                        raise ValueError(
                            f"Reviewer {r_id} is co-champion for paper {p_id} but is chair/co-chair."
                        )
                    if assignment_matrix[r, p] != 1:
                        raise ValueError(
                            f"Reviewer {r_id} is co-champion for paper {p_id} but is not an assigned reviewer."
                        )
                    if champ_matrix[r, p] == 1:
                        raise ValueError(
                            f"Reviewer {r_id} is co-champion for paper {p_id} but is also the champion."
                        )
                    if coi[r, p] == 1:
                        raise ValueError(
                            f"Reviewer {r_id} is co-champion for paper {p_id} but has a Conflict of Interest."
                        )

        objective_value = pulp.value(prob.objective)
        return cochamp_matrix, objective_value
