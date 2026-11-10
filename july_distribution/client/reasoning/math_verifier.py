"""
HS AI SOLUTIONS — MATHEMATICAL INTELLIGENCE & VERIFICATION ENGINE
Module: july_distribution.client.reasoning.math_verifier
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Family: JULY AI Family

Provides symbolic computation, formal equation solving, underdetermined system detection,
degrees of freedom analysis, calculus, probability sufficiency checking, and numerical verification.
"""

from __future__ import annotations
import re
import math
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field

try:
    import sympy as sp
    from sympy.core.numbers import Rational, Float, Integer
    from sympy.solvers.solveset import linsolve, nonlinsolve
except ImportError:
    sp = None


@dataclass
class MathVerificationResult:
    is_mathematical: bool
    is_valid: bool
    problem_type: str  # 'system_of_equations', 'single_equation', 'calculus', 'probability_bounds', 'arithmetic', 'unsolvable'
    uniquely_determined_vars: Dict[str, str] = field(default_factory=dict)
    underdetermined_vars: Dict[str, str] = field(default_factory=dict)
    unconstrained_vars: List[str] = field(default_factory=list)
    degrees_of_freedom: int = 0
    exact_solution: Optional[str] = None
    approximate_solution: Optional[str] = None
    missing_constraints: List[str] = field(default_factory=list)
    verification_notes: str = ""
    is_underdetermined: bool = False
    is_inconsistent: bool = False
    probability_bounds: Optional[Tuple[float, float]] = None


class MathematicalIntelligenceEngine:
    """
    Symbolic & Numerical Verification Subsystem for JULY LLM.
    Guarantees mathematical correctness without fabricating certainty.
    """

    def __init__(self):
        self.sp = sp

    def analyze_mathematical_query(self, text: str) -> MathVerificationResult:
        """
        Analyzes a query or response for mathematical statements,
        detects systems of equations, calculus, or probability problems,
        and returns formal symbolic verification.
        """
        if not self.sp:
            return MathVerificationResult(
                is_mathematical=False,
                is_valid=False,
                problem_type="sympy_unavailable",
                verification_notes="SymPy library not available."
            )

        # 1. Check for underdetermined / systems of equations (e.g., a + b + c = 10 ...)
        sys_res = self._check_equation_system(text)
        if sys_res and sys_res.is_mathematical:
            return sys_res

        # 2. Check for probability questions with insufficient information (e.g., P(A)=0.6, P(B)=0.7, P(A and B))
        prob_res = self._check_probability_sufficiency(text)
        if prob_res and prob_res.is_mathematical:
            return prob_res

        # 3. Check for single equation or expression arithmetic
        single_res = self._check_single_equation_or_expression(text)
        if single_res and single_res.is_mathematical:
            return single_res

        # 4. Check for calculus
        calc_res = self._check_calculus(text)
        if calc_res and calc_res.is_mathematical:
            return calc_res

        return MathVerificationResult(
            is_mathematical=False,
            is_valid=True,
            problem_type="non_mathematical",
            verification_notes="No verifiable mathematical structure identified."
        )

    def _extract_equation_lines(self, text: str) -> List[str]:
        """Extract lines or patterns that represent equations."""
        lines = text.splitlines()
        eqs = []
        for line in lines:
            line_str = line.strip()
            # Match equations like a + b + c = 10, 2*x + 5 = 15, etc.
            if "=" in line_str and not line_str.startswith("#"):
                # Clean up bullets or numbering
                cleaned = re.sub(r"^[\d\.\-\*\+\s]+", "", line_str)
                parts = cleaned.split("=")
                if len(parts) == 2:
                    lhs, rhs = parts[0].strip(), parts[1].strip()
                    # Check if valid algebraic characters
                    if re.search(r"[a-zA-Z0-9]", lhs) and re.search(r"[a-zA-Z0-9]", rhs):
                        eqs.append(f"{lhs} = {rhs}")
        return eqs

    def _check_equation_system(self, text: str) -> Optional[MathVerificationResult]:
        """Examines systems of linear or non-linear equations for solvability, degrees of freedom, and constraints."""
        eq_lines = self._extract_equation_lines(text)
        if len(eq_lines) < 2:
            return None

        # Extract queried variables (e.g. 'values for a, b, c, d, and e')
        queried_vars = set()
        var_query_match = re.search(r"(?:values?\s+for|solve\s+for|find)\s+([a-zA-Z\s,and]+)", text, re.IGNORECASE)
        if var_query_match:
            raw_vars = var_query_match.group(1)
            tokens = re.findall(r"\b([a-zA-Z])\b", raw_vars)
            for t in tokens:
                if t.lower() not in ("a", "and", "or", "for", "the", "in", "of"):
                    queried_vars.add(t)

        equations = []
        all_symbols = set()

        for eq_str in eq_lines:
            lhs, rhs = eq_str.split("=", 1)
            try:
                # Pre-process implicit multiplication (e.g., 2a -> 2*a)
                lhs_proc = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", lhs)
                rhs_proc = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", rhs)
                lhs_proc = re.sub(r"([a-zA-Z])([a-zA-Z])", r"\1*\2", lhs_proc)
                rhs_proc = re.sub(r"([a-zA-Z])([a-zA-Z])", r"\1*\2", rhs_proc)

                lhs_sym = sp.sympify(lhs_proc)
                rhs_sym = sp.sympify(rhs_proc)
                eq_expr = lhs_sym - rhs_sym
                equations.append(eq_expr)
                all_symbols.update(eq_expr.free_symbols)
            except Exception:
                continue

        if len(equations) < 2:
            return None

        sym_list = sorted(list(all_symbols), key=lambda s: s.name)
        if not sym_list:
            return None

        # Check for unconstrained variables mentioned in query that don't appear in any equation
        unconstrained = []
        sym_names = {s.name for s in sym_list}
        for qv in queried_vars:
            if qv not in sym_names:
                unconstrained.append(qv)

        try:
            solution_set = sp.linsolve(equations, sym_list)
        except Exception:
            solution_set = sp.solve(equations, sym_list, dict=True)

        if not solution_set or (hasattr(solution_set, "__len__") and len(solution_set) == 0):
            return MathVerificationResult(
                is_mathematical=True,
                is_valid=True,
                problem_type="system_of_equations",
                is_inconsistent=True,
                verification_notes="System has NO valid real solutions (inconsistent equations)."
            )

        # Inspect solution form
        uniquely_det = {}
        underdet = {}
        free_symbols_found = set()

        if hasattr(solution_set, "args"):
            sol_tuples = list(solution_set)
            if sol_tuples:
                sol_tuple = sol_tuples[0]
                for sym, val in zip(sym_list, sol_tuple):
                    # Check if val is a constant number
                    if hasattr(val, "is_number") and val.is_number:
                        uniquely_det[sym.name] = str(val)
                    else:
                        underdet[sym.name] = str(val)
                        free_symbols_found.update(val.free_symbols)
        elif isinstance(solution_set, list) and solution_set and isinstance(solution_set[0], dict):
            sol_dict = solution_set[0]
            for sym in sym_list:
                if sym in sol_dict:
                    val = sol_dict[sym]
                    if hasattr(val, "is_number") and val.is_number:
                        uniquely_det[sym.name] = str(val)
                    else:
                        underdet[sym.name] = str(val)
                        free_symbols_found.update(val.free_symbols)
                else:
                    underdet[sym.name] = "free parameter"
                    free_symbols_found.add(sym)

        dof = len(free_symbols_found)
        is_underdet = dof > 0 or len(underdet) > 0 or len(unconstrained) > 0

        # Build verification notes
        notes_parts = []
        if uniquely_det:
            notes_parts.append(f"Uniquely determined: {', '.join(f'{k} = {v}' for k, v in uniquely_det.items())}")
        if underdet:
            notes_parts.append(f"Underdetermined variables: {', '.join(f'{k} = {v}' for k, v in underdet.items())} (Degrees of Freedom: {dof})")
        if unconstrained:
            notes_parts.append(f"Unconstrained variables: {', '.join(unconstrained)} (completely unconstrained; can take any real value)")

        notes = ". ".join(notes_parts) + "."

        return MathVerificationResult(
            is_mathematical=True,
            is_valid=True,
            problem_type="system_of_equations",
            uniquely_determined_vars=uniquely_det,
            underdetermined_vars=underdet,
            unconstrained_vars=unconstrained,
            degrees_of_freedom=dof,
            exact_solution=str(solution_set),
            is_underdetermined=is_underdet,
            verification_notes=notes
        )

    def _check_probability_sufficiency(self, text: str) -> Optional[MathVerificationResult]:
        """
        Checks probability questions (e.g., P(A), P(B), joint P(A and B)).
        Identifies missing constraints and provides tight Fréchet bounds.
        """
        p_matches = re.findall(r"P\(([A-Za-z0-9_\s\+]+)\)\s*=\s*([0-9\.]+)", text)
        if not p_matches or len(p_matches) < 2:
            return None

        probs = {}
        for ev, val_str in p_matches:
            try:
                ev_clean = ev.strip()
                clean_num = val_str.strip().rstrip(".")
                probs[ev_clean] = float(clean_num)
            except ValueError:
                continue

        # Look for target query P(A and B) or P(A ∩ B) or similar
        target_joint = re.search(r"(?:calculate|find|what\s+is)\s+P\(([A-Za-z0-9_\s\+]+(?:and|∩|\&)[A-Za-z0-9_\s\+]+)\)", text, re.IGNORECASE)
        if not target_joint and ("P(A and B)" in text or "P(A and B)" in text.upper() or "joint probability" in text.lower()):
            # Assume A and B
            target_evs = ("A", "B")
        elif target_joint:
            raw = target_joint.group(1)
            parts = re.split(r"\s+and\s+|\s*∩\s*|\s*\&\s*", raw, flags=re.IGNORECASE)
            target_evs = tuple(p.strip() for p in parts if p.strip())
        else:
            return None

        if len(target_evs) == 2 and target_evs[0] in probs and target_evs[1] in probs:
            pA = probs[target_evs[0]]
            pB = probs[target_evs[1]]

            # Check if independence or conditional probability is given
            has_independence = bool(re.search(r"\bindependent\b", text, re.IGNORECASE))
            has_conditional = bool(re.search(r"P\([A-Za-z]\|[A-Za-z]\)", text))

            lower_bound = max(0.0, pA + pB - 1.0)
            upper_bound = min(pA, pB)

            if not has_independence and not has_conditional:
                missing = [
                    f"Independence assumption between {target_evs[0]} and {target_evs[1]} is not specified",
                    f"Conditional probability P({target_evs[0]}|{target_evs[1]}) or P({target_evs[1]}|{target_evs[0]}) is not provided"
                ]
                notes = (
                    f"Insufficient information to determine unique probability P({target_evs[0]} and {target_evs[1]}). "
                    f"Without independence or conditional data, Fréchet / Boole inequality bounds apply: "
                    f"max(0, P({target_evs[0]}) + P({target_evs[1]}) - 1) <= P({target_evs[0]} and {target_evs[1]}) <= min(P({target_evs[0]}), P({target_evs[1]})). "
                    f"Exact bounds: [{round(lower_bound, 4)}, {round(upper_bound, 4)}]."
                )
                return MathVerificationResult(
                    is_mathematical=True,
                    is_valid=True,
                    problem_type="probability_bounds",
                    is_underdetermined=True,
                    probability_bounds=(round(lower_bound, 4), round(upper_bound, 4)),
                    missing_constraints=missing,
                    verification_notes=notes
                )
            elif has_independence:
                joint_val = round(pA * pB, 4)
                return MathVerificationResult(
                    is_mathematical=True,
                    is_valid=True,
                    problem_type="probability",
                    exact_solution=str(joint_val),
                    verification_notes=f"Assuming independent events: P({target_evs[0]} and {target_evs[1]}) = P({target_evs[0]}) * P({target_evs[1]}) = {joint_val}."
                )

        return None

    def _check_single_equation_or_expression(self, text: str) -> Optional[MathVerificationResult]:
        """Handles single equation solving or arithmetic expressions."""
        # Find single equations like 2*x + 10 = 30
        eq_match = re.search(r"([0-9a-zA-Z\s\+\-\*\/\^\(\)]+)\s*=\s*([0-9a-zA-Z\s\+\-\*\/\^\(\)]+)", text)
        if eq_match:
            lhs_s, rhs_s = eq_match.group(1).strip(), eq_match.group(2).strip()
            # Strip prompt keywords like "solve", "calculate", "find"
            lhs_s = re.sub(r"^(?:solve|calculate|find|evaluate|compute)\s+", "", lhs_s, flags=re.IGNORECASE).strip()
            # Must contain at least one arithmetic operator
            if any(op in lhs_s + rhs_s for op in ["+", "-", "*", "/", "^"]):
                try:
                    lhs = sp.sympify(lhs_s)
                    rhs = sp.sympify(rhs_s)
                    symbols = list(lhs.free_symbols.union(rhs.free_symbols))
                    if symbols:
                        sol = sp.solve(lhs - rhs, symbols[0])
                        return MathVerificationResult(
                            is_mathematical=True,
                            is_valid=True,
                            problem_type="single_equation",
                            uniquely_determined_vars={symbols[0].name: str(sol)},
                            exact_solution=f"{symbols[0].name} = {sol}",
                            verification_notes=f"Solved equation for {symbols[0].name}: {sol}"
                        )
                    else:
                        is_eq = bool(lhs == rhs)
                        return MathVerificationResult(
                            is_mathematical=True,
                            is_valid=is_eq,
                            problem_type="identity",
                            verification_notes=f"Identity check: {lhs} == {rhs} -> {is_eq}"
                        )
                except Exception:
                    pass

        # Pure arithmetic expression: e.g., (15 * 4) + (100 / 5)
        arith_match = re.search(r"(?:calculate|compute|what\s+is)\s+([0-9\.\s\+\-\*\/\^\(\)]+)", text, re.IGNORECASE)
        if arith_match:
            expr_str = arith_match.group(1).strip()
            if any(op in expr_str for op in ["+", "-", "*", "/", "^"]):
                try:
                    expr = sp.sympify(expr_str)
                    res_exact = str(expr)
                    res_eval = str(expr.evalf())
                    return MathVerificationResult(
                        is_mathematical=True,
                        is_valid=True,
                        problem_type="arithmetic",
                        exact_solution=res_exact,
                        approximate_solution=res_eval,
                        verification_notes=f"Calculated: {expr_str} = {res_exact}"
                    )
                except Exception:
                    pass

        return None

    def _check_calculus(self, text: str) -> Optional[MathVerificationResult]:
        """Handles derivatives, integrals, and limits."""
        # Derivative: d/dx (x^3) or derivative of ...
        diff_match = re.search(r"(?:derivative\s+of|diff\s+|d/dx\s*)\s*([0-9a-zA-Z\s\+\-\*\/\^\(\)]+)", text, re.IGNORECASE)
        if diff_match:
            expr_str = diff_match.group(1).strip()
            try:
                x = sp.Symbol("x")
                expr = sp.sympify(expr_str)
                deriv = sp.diff(expr, x)
                return MathVerificationResult(
                    is_mathematical=True,
                    is_valid=True,
                    problem_type="calculus",
                    exact_solution=str(deriv),
                    verification_notes=f"Derivative of {expr} with respect to x: {deriv}"
                )
            except Exception:
                pass

        # Integral: integral of ...
        int_match = re.search(r"(?:integral\s+of|integrate\s+)\s*([0-9a-zA-Z\s\+\-\*\/\^\(\)]+)", text, re.IGNORECASE)
        if int_match:
            expr_str = int_match.group(1).strip()
            try:
                x = sp.Symbol("x")
                expr = sp.sympify(expr_str)
                integ = sp.integrate(expr, x)
                return MathVerificationResult(
                    is_mathematical=True,
                    is_valid=True,
                    problem_type="calculus",
                    exact_solution=str(integ),
                    verification_notes=f"Indefinite integral of {expr} dx: {integ} + C"
                )
            except Exception:
                pass

        return None
