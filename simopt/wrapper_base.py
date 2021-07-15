#!/usr/bin/env python
"""
Summary
-------
Provide base classes for experiments and meta experiments.
Plus helper functions for reading/writing data and plotting.

Listing
-------
Curve : class
mean_of_curves : function
quantile_of_curves : function
difference_of_curves : function
Experiment : class
trim_solver_results : function
read_experiment_results : function
post_normalize : function
bootstrap_sample_all : function
bootstrap_procedure : function
functional_of_curves : function
compute_bootstrap_CI : function
plot_bootstrap_CIs : function
report_max_halfwidth : function
plot_progress_curves : function
stylize_plot : function
stylize_solvability_plot : function
stylize_difference_plot : function
stylize_area_plot : function
save_plot : function
area_under_prog_curve : function
solve_time_of_prog_curve : function
MetaExperiment : class
compute_difference_solvability_profile : function
"""

import numpy as np
import matplotlib.pyplot as plt
from numpy.core.defchararray import endswith
from scipy.stats import norm
import pickle
import importlib
from copy import deepcopy


from rng.mrg32k3a import MRG32k3a
from base import Solution
from directory import solver_directory, problem_directory


class Curve(object):
    """
    Base class for all curves.

    Attributes
    ----------
    x_vals : list of floats
        values of horizontal components
    y_vals : list of floats
        values of vertical components
    n_points : int
        number of values in x- and y- vectors

    Parameters
    ----------
    x_vals : list of floats
        values of horizontal components
    y_vals : list of floats
        values of vertical components
    """
    def __init__(self, x_vals, y_vals):
        if len(x_vals) != len(y_vals):
            print("Vectors of x- and y- values must be of same length.")
        self.x_vals = x_vals
        self.y_vals = y_vals
        self.n_points = len(x_vals)

    def lookup(self, x):
        """
        Lookup the y-value of the curve at an intermediate x-value.

        Parameters
        ----------
        x : float
            x-value at which to lookup the y-value

        Returns
        -------
        y : float
            y-value corresponding to x
        """
        if x < self.x_vals[0]:
            y = np.nan
        else:
            idx = np.max(np.where(np.array(self.x_vals) <= x))
            y = self.y_vals[idx]
        return y

    def compute_crossing_time(self, threshold):
        """
        Compute the first time at which a curve drops below a given threshold.

        Parameters
        ----------
        threshold : float
            value for which to find first crossing time

        Returns
        -------
        crossing_time : float
            first time at which a curve drops below threshold
        """
        # Crossing time is defined as infinity if the curve does not drop
        # below threshold.
        crossing_time = np.inf
        # Pass over curve to find first crossing time.
        for i in range(self.n_points):
            if self.y_vals[i] < threshold:
                crossing_time = self.x_vals[i]
                break
        return crossing_time

    def compute_area_under_curve(self):
        """
        Compute the area under a curve.

        Returns
        -------
        area : float
            area under the curve
        """
        area = np.dot(self.y_vals[:-1], np.diff(self.x_vals))
        return area

    def plot(self, color_str="C0", curve_type="regular"):
        """
        Plot a curve.

        Parameters
        ----------
        color_str : str
            string indicating line color, e.g., "C0", "C1", etc.

        Returns
        -------
        handle : list of matplotlib.lines.Line2D objects
            curve handle, to use when creating legends
        """
        if curve_type == "regular":
            linestyle = "-"
            linewidth = 2
        elif curve_type == "conf_bound":
            linestyle = "--"
            linewidth = 1
        handle, = plt.step(self.x_vals,
                           self.y_vals,
                           color=color_str,
                           linestyle=linestyle,
                           linewidth=linewidth,
                           where="post"
                           )
        return handle


def mean_of_curves(curves):
    """
    Compute pointwise (w.r.t. x values) mean of curves.
    Starting and ending x values must coincide for all curves.

    Parameters
    ----------
    curves : list of wrapper_base.Curve objects
        collection of curves to aggregate

    Returns
    -------
    mean_curve : wrapper_base.Curve object
        mean curve
    """
    unique_x_vals = np.unique([x_val for curve in curves for x_val in curve.x_vals])
    mean_y_vals = [np.mean([curve.lookup(x_val) for curve in curves]) for x_val in unique_x_vals]
    mean_curve = Curve(x_vals=unique_x_vals.tolist(), y_vals=mean_y_vals)
    return mean_curve


def quantile_of_curves(curves, beta):
    """
    Compute pointwise (w.r.t. x values) quantile of curves.
    Starting and ending x values must coincide for all curves.

    Parameters
    ----------
    curves : list of wrapper_base.Curve objects
        collection of curves to aggregate
    beta : float
        quantile level

    Returns
    -------
    quantile_curve : wrapper_base.Curve object
        quantile curve
    """
    unique_x_vals = np.unique([x_val for curve in curves for x_val in curve.x_vals])
    quantile_y_vals = [np.quantile([curve.lookup(x_val) for curve in curves], q=beta) for x_val in unique_x_vals]
    quantile_curve = Curve(x_vals=unique_x_vals.tolist(), y_vals=quantile_y_vals)
    return quantile_curve


def difference_of_curves(curve1, curve2):
    """
    Compute the difference of two curves (Curve 1 - Curve 2).

    Parameters
    ----------
    curve1, curve2 : wrapper_base.Curve objects
        curves to take the difference of

    Returns
    -------
    difference_curve : wrapper_base.Curve object
        difference of curves
    """
    unique_x_vals = np.unique(curve1.x_vals + curve2.x_vals)
    difference_y_vals = [(curve1.lookup(x_val) - curve2.lookup(x_val)) for x_val in unique_x_vals]
    difference_curve = Curve(x_vals=unique_x_vals.tolist(), y_vals=difference_y_vals)
    return difference_curve


def max_difference_of_curves(curve1, curve2):
    """
    Compute the maximum difference of two curves (Curve 1 - Curve 2)

    Parameters
    ----------
    curve1, curve2 : wrapper_base.Curve objects
        curves to take the difference of

    Returns
    -------
    max_diff : float
        maximum difference of curves
    """
    difference_curve = difference_of_curves(curve1, curve2)
    max_diff = max(difference_curve.y_vals)
    return max_diff


class Experiment(object):
    """
    Base class for running one solver on one problem.

    Attributes
    ----------
    solver : base.Solver object
        simulation-optimization solver
    problem : base.Problem object
        simulation-optimization problem
    n_macroreps : int > 0
        number of macroreplications run
    file_name_path : str
        path of .pickle file for saving wrapper_base.Experiment object
    all_recommended_xs : list of lists of tuples
        sequences of recommended solutions from each macroreplication
    all_intermediate_budgets : list of lists
        sequences of intermediate budgets from each macroreplication
    n_postreps : int
        number of postreplications to take at each recommended solution
    crn_across_budget : bool
        use CRN for post-replications at solutions recommended at different times?
    crn_across_macroreps : bool
        use CRN for post-replications at solutions recommended on different macroreplications?
    all_post_replicates : list of lists of lists
        all post-replicates from all solutions from all macroreplications
    all_est_objectives : numpy array of arrays
        estimated objective values of all solutions from all macroreplications
    n_postreps_init_opt : int
        number of postreplications to take at initial solution (x0) and
        optimal solution (x*)
    crn_across_init_opt : bool
        use CRN for post-replications at solutions x0 and x*?
    x0 : tuple
        initial solution (x0)
    x0_postreps : list
        post-replicates at x0
    xstar : tuple
        proxy for optimal solution (x*)
    xstar_postreps : list
        post-replicates at x*
    objective_curves : list of wrapper_base.Curve objects
        curves of estimated objective function values,
        one for each macroreplication
    progress_curves : list of wrapper_base.Curve objects
        progress curves, one for each macroreplication
    all_prog_curves : numpy array of arrays
        estimated progress curves from all macroreplications
    initial_soln : base.Solution object
        initial solution (w/ postreplicates) used for normalization
    ref_opt_soln : base.Solution object
        reference optimal solution (w/ postreplicates) used for normalization
    areas : list of floats
        areas under each estimated progress curve
    area_mean : float
        sample mean area under estimated progress curves
    area_std_dev : float
        sample standard deviation of area under estimated progress curves
    area_mean_CI : numpy array of length 2
        bootstrap CI of the form [lower bound, upper bound] for mean area
    area_std_dev_CI : numpy array of length 2
        bootstrap CI of the form [lower_bound, upper_bound] for std dev of area
    solve_tols : list of floats in (0,1]
        relative optimality gap(s) definining when a problem is solved
    solve_times = list of lists of floats
        solve_tol solve times for each estimated progress curve for each solve_tol
    solve_time_quantiles : list of floats
        beta quantile of solve times for each solve_tole
    solve_time_quantiles_CIs : list of numpy arrays of length 2
        bootstrap CI of the form [lower bound, upper bound] for quantile of solve time
        for each solve_tol

    Arguments
    ---------
    solver_name : str
        name of solver
    problem_name : str
        name of problem
    solver_rename : str
        user-specified name for solver
    problem_rename : str
        user-specified name for problem
    solver_fixed_factors : dict
        dictionary of user-specified solver factors
    problem_fixed_factors : dict
        dictionary of user-specified problem factors
    oracle_fixed_factors : dict
        dictionary of user-specified oracle factors
    file_name_path : str
        path of .pickle file for saving wrapper_base.Experiment object
    """
    def __init__(self, solver_name, problem_name, solver_rename=None, problem_rename=None, solver_fixed_factors={}, problem_fixed_factors={}, oracle_fixed_factors={}, file_name_path=None):
        if solver_rename is None:
            self.solver = solver_directory[solver_name](fixed_factors=solver_fixed_factors)
        else:
            self.solver = solver_directory[solver_name](name=solver_rename, fixed_factors=solver_fixed_factors)
        if problem_rename is None:
            self.problem = problem_directory[problem_name](fixed_factors=problem_fixed_factors, oracle_fixed_factors=oracle_fixed_factors)
        else:
            self.problem = problem_directory[problem_name](name=problem_rename, fixed_factors=problem_fixed_factors, oracle_fixed_factors=oracle_fixed_factors)
        if file_name_path is None:
            self.file_name_path = f"./experiments/outputs/{self.solver.name}_on_{self.problem.name}.pickle"
        else:
            self.file_name_path = file_name_path

    def run(self, n_macroreps):
        """
        Run n_macroreps of the solver on the problem.

        Arguments
        ---------
        n_macroreps : int
            number of macroreplications of the solver to run on the problem
        """
        self.n_macroreps = n_macroreps
        self.all_recommended_xs = []
        self.all_intermediate_budgets = []
        # Create, initialize, and attach random number generators
        #     Stream 0: reserved for taking post-replications
        #     Stream 1: reserved for bootstrapping
        #     Stream 2: reserved for overhead ...
        #         Substream 0: rng for random problem instance
        #         Substream 1: rng for random initial solution x0 and
        #                      restart solutions
        #         Substream 2: rng for selecting random feasible solutions
        #         Substream 3: rng for solver's internal randomness
        #     Streams 3, 4, ..., n_macroreps + 2: reserved for
        #                                         macroreplications
        rng0 = MRG32k3a(s_ss_sss_index=[2, 0, 0])  # unused
        rng1 = MRG32k3a(s_ss_sss_index=[2, 1, 0])  # unused
        rng2 = MRG32k3a(s_ss_sss_index=[2, 2, 0])
        rng3 = MRG32k3a(s_ss_sss_index=[2, 3, 0])  # unused
        self.solver.attach_rngs([rng1, rng2, rng3])
        # Run n_macroreps of the solver on the problem.
        # Report recommended solutions and corresponding intermediate budgets.
        for mrep in range(self.n_macroreps):
            print(f"Running macroreplication {mrep + 1} of {self.n_macroreps} of Solver {self.solver.name} on Problem {self.problem.name}.")
            # Create, initialize, and attach RNGs used for simulating solutions.
            progenitor_rngs = [MRG32k3a(s_ss_sss_index=[mrep + 2, ss, 0]) for ss in range(self.problem.oracle.n_rngs)]
            self.solver.solution_progenitor_rngs = progenitor_rngs
            # print([rng.s_ss_sss_index for rng in progenitor_rngs])
            # Run the solver on the problem.
            recommended_solns, intermediate_budgets = self.solver.solve(problem=self.problem)
            # Trim solutions recommended after final budget
            recommended_solns, intermediate_budgets = trim_solver_results(problem=self.problem, recommended_solns=recommended_solns, intermediate_budgets=intermediate_budgets)
            # Extract decision-variable vectors (x) from recommended solutions.
            # Record recommended solutions and intermediate budgets.
            self.all_recommended_xs.append([solution.x for solution in recommended_solns])
            self.all_intermediate_budgets.append(intermediate_budgets)
        # Save Experiment object to .pickle file.
        self.record_experiment_results()

    def post_replicate(self, n_postreps, crn_across_budget=True, crn_across_macroreps=False):
        """
        Run postreplications at solutions recommended by the solver.

        Arguments
        ---------
        n_postreps : int
            number of postreplications to take at each recommended solution
        crn_across_budget : bool
            use CRN for post-replications at solutions recommended at different times?
        crn_across_macroreps : bool
            use CRN for post-replications at solutions recommended on different macroreplications?
        """
        self.n_postreps = n_postreps
        self.crn_across_budget = crn_across_budget
        self.crn_across_macroreps = crn_across_macroreps
        # Create, initialize, and attach RNGs for oracle.
        # Stream 0: reserved for post-replications.
        # Skip over first set of substreams dedicated for sampling x0 and x*.
        baseline_rngs = [MRG32k3a(s_ss_sss_index=[0, self.problem.oracle.n_rngs + rng_index, 0]) for rng_index in range(self.problem.oracle.n_rngs)]
        # Initialize matrix containing
        #     all postreplicates of objective,
        #     for each macroreplication,
        #     for each budget.
        self.all_post_replicates = [[[] for _ in range(len(self.all_intermediate_budgets[mrep]))] for mrep in range(self.n_macroreps)]
        # Simulate intermediate recommended solutions.
        for mrep in range(self.n_macroreps):
            for budget_index in range(len(self.all_intermediate_budgets[mrep])):
                x = self.all_recommended_xs[mrep][budget_index]
                fresh_soln = Solution(x, self.problem)
                fresh_soln.attach_rngs(rng_list=baseline_rngs, copy=False)
                self.problem.simulate(solution=fresh_soln, m=self.n_postreps)
                # Store results
                self.all_post_replicates[mrep][budget_index] = list(fresh_soln.objectives[:fresh_soln.n_reps][:, 0])  # 0 <- assuming only one objective
                if crn_across_budget:
                    # Reset each rng to start of its current substream.
                    for rng in baseline_rngs:
                        rng.reset_substream()
            if crn_across_macroreps:
                # Reset each rng to start of its current substream.
                for rng in baseline_rngs:
                    rng.reset_substream()
            else:
                # Advance each rng to start of
                #     substream = current substream + # of oracle RNGs.
                for rng in baseline_rngs:
                    for _ in range(self.problem.oracle.n_rngs):
                        rng.advance_substream()
        # Store estimated objective for each macrorep for each budget.
        self.all_est_objectives = [[np.mean(self.all_post_replicates[mrep][budget_index]) for budget_index in range(len(self.all_intermediate_budgets[mrep]))] for mrep in range(self.n_macroreps)]
        # Save Experiment object to .pickle file.
        self.record_experiment_results()

    def plot_solvability_curves(self, solve_tols=[0.10], plot_CIs=True):
        """
        Plot the solvability curve(s) for a single solver-problem pair.
        Optionally plot bootstrap CIs.

        Arguments
        ---------
        solve_tols : list of floats in (0,1]
            relative optimality gap(s) definining when a problem is solved
        plot_CIs : Boolean
            plot bootstrapping confidence intervals?
        """
        # Compute solve times.
        self.compute_solvability(solve_tols=solve_tols)
        for tol_index in range(len(self.solve_tols)):
            solve_tol = solve_tols[tol_index]
            stylize_solvability_plot(solver_name=self.solver.name, problem_name=self.problem.name, solve_tol=solve_tol, plot_type="single")
            # Construct matrix showing when macroreplications are solved.
            solve_matrix = np.zeros((self.n_macroreps, len(self.unique_frac_budgets)))
            # Pass over progress curves to find first solve_tol crossing time.
            for mrep in range(self.n_macroreps):
                for budget_index in range(len(self.unique_frac_budgets)):
                    if self.solve_times[tol_index][mrep] <= self.unique_frac_budgets[budget_index]:
                        solve_matrix[mrep][budget_index] = 1
            # Compute proportion of macroreplications "solved" by intermediate budget.
            estimator = np.mean(solve_matrix, axis=0)
            # Plot solvability curve.
            plt.step(self.unique_frac_budgets, estimator, where="post")
            if plot_CIs:
                # Report bootstrapping error estimation and optionally plot bootstrap CIs.
                self.plot_bootstrap_CIs(plot_type="solvability", normalize=True, estimator=estimator, plot_CIs=plot_CIs, tol_index=tol_index)
            save_plot(solver_name=self.solver.name, problem_name=self.problem.name, plot_type="cdf solve times", normalize=True, extra=solve_tol)

    def compute_area_stats(self, compute_CIs=True):
        """
        Compute average and standard deviation of areas under progress curves.
        Optionally compute bootstrap confidence intervals.

        Arguments
        ---------
        compute_CIs : Boolean
            compute bootstrap confidence invervals for average and std dev?
        """
        # Compute areas under each estimated progress curve.
        self.areas = [area_under_prog_curve(prog_curve, self.unique_frac_budgets) for prog_curve in self.all_prog_curves]
        self.area_mean = np.mean(self.areas)
        self.area_std_dev = np.std(self.areas, ddof=1)
        # (Optional) Compute bootstrap CIs.
        if compute_CIs:
            lower_bound, upper_bound, _ = self.bootstrap_CI(plot_type="area_mean", normalize=True, estimator=[self.area_mean], n_bootstraps=100, conf_level=0.95, bias_correction=True)
            self.area_mean_CI = [lower_bound[0], upper_bound[0]]
            lower_bound, upper_bound, _ = self.bootstrap_CI(plot_type="area_std_dev", normalize=True, estimator=[self.area_std_dev], n_bootstraps=100, conf_level=0.95, bias_correction=True)
            self.area_std_dev_CI = [lower_bound[0], upper_bound[0]]

    def compute_solvability(self, solve_tols=[0.10]):
        """
        Compute alpha-solve times for all macroreplications.
        Can specify multiple values of alpha.

        Arguments
        ---------
        solve_tols : list of floats in (0,1]
            relative optimality gap(s) definining when a problem is solved
        """
        self.solve_tols = solve_tols
        self.solve_times = [[solve_time_of_prog_curve(prog_curve, self.unique_frac_budgets, solve_tol) for prog_curve in self.all_prog_curves] for solve_tol in solve_tols]

    def compute_solvability_quantiles(self, beta=0.50, compute_CIs=True):
        """
        Compute beta quantile of solve times, for each solve tolerance.
        Optionally compute bootstrap confidence intervals.

        Arguments
        ---------
        beta : float in (0,1)
            quantile to compute, e.g., beta quantile
        compute_CIs : Boolean
            compute bootstrap confidence invervals for quantile?
        """
        self.solve_time_quantiles = [np.quantile(self.solve_times[tol_index], q=beta, interpolation="higher") for tol_index in range(len(self.solve_tols))]
        # The default method for np.quantile is a *linear* interpolation.
        # Linear interpolation will throw error if a breakpoint is +/- infinity.
        if compute_CIs:
            lower_bounds, upper_bounds, _ = self.bootstrap_CI(plot_type="solve_time_quantile", normalize=True, estimator=self.solve_time_quantiles, beta=beta)
            self.solve_time_quantiles_CIs = [[lower_bounds[tol_index], upper_bounds[tol_index]] for tol_index in range(len(self.solve_tols))]

    def bootstrap_sample(self, bootstrap_rng, normalize=True):
        """
        Generate a bootstrap sample of estimated progress curves (normalized and unnormalized).

        Parameters
        ----------
        bootstrap_rng : MRG32k3a object
            random number generator to use for bootstrapping
        normalize : Boolean
            normalize progress curves w.r.t. optimality gaps?

        Returns
        -------
        bootstrap_curves : list of wrapper_base.Curve objects
            bootstrapped estimated objective curves or estimated progress curves
            of all solutions from all bootstrapped macroreplications
        """
        bootstrap_curves = []
        # Uniformly resample M macroreplications (with replacement) from 0, 1, ..., M-1.
        # Subsubstream 0: reserved for this outer-level bootstrapping.
        bs_mrep_idxs = bootstrap_rng.choices(range(self.n_macroreps), k=self.n_macroreps)
        # Advance RNG subsubstream to prepare for inner-level bootstrapping.
        bootstrap_rng.advance_subsubstream()
        # Subsubstream 1: reserved for bootstrapping at x0 and x*.
        # Bootstrap sample post-replicates at common x0.
        # Uniformly resample L postreps (with replacement) from 0, 1, ..., L-1.
        bs_postrep_idxs = bootstrap_rng.choices(range(self.n_postreps_init_opt), k=self.n_postreps_init_opt)
        # Compute the mean of the resampled postreplications.
        bs_initial_obj_val = np.mean([self.x0_postreps[postrep] for postrep in bs_postrep_idxs])
        # Reset subsubstream if using CRN across budgets.
        # This means the same postreplication indices will be used for resampling at x0 and x*.
        if self.crn_across_budget:
            bootstrap_rng.reset_subsubstream()
        # Bootstrap sample postreplicates at reference optimal solution x*.
        # Uniformly resample L postreps (with replacement) from 0, 1, ..., L.
        bs_postrep_idxs = bootstrap_rng.choices(range(self.n_postreps_init_opt), k=self.n_postreps_init_opt)
        # Compute the mean of the resampled postreplications.
        bs_optimal_obj_val = np.mean([self.xstar_postreps[postrep] for postrep in bs_postrep_idxs])
        # Compute initial optimality gap.
        bs_initial_opt_gap = bs_initial_obj_val - bs_optimal_obj_val
        # Advance RNG subsubstream to prepare for inner-level bootstrapping.
        # Will now be at start of subsubstream 2.
        bootstrap_rng.advance_subsubstream()
        # Bootstrap within each bootstrapped macroreplication.
        for idx in range(self.n_macroreps):
            mrep = bs_mrep_idxs[idx]
            # Inner-level bootstrapping over intermediate recommended solutions.
            est_objectives = []
            for budget in range(len(self.all_intermediate_budgets[mrep])):
                # If solution is x0...
                if self.all_recommended_xs[mrep][budget] == self.x0:
                    est_objectives.append(bs_initial_obj_val)
                # ...else if solution is x*...
                elif self.all_recommended_xs[mrep][budget] == self.xstar:
                    est_objectives.append(bs_optimal_obj_val)
                # ... else solution other than x0 or x*.
                else:
                    # Uniformly resample N postreps (with replacement) from 0, 1, ..., N-1.
                    bs_postrep_idxs = bootstrap_rng.choices(range(self.n_postreps), k=self.n_postreps)
                    # Compute the mean of the resampled postreplications.
                    est_objectives.append(np.mean([self.all_post_replicates[mrep][budget][postrep] for postrep in bs_postrep_idxs]))
                    # Reset subsubstream if using CRN across budgets.
                    if self.crn_across_budget:
                        bootstrap_rng.reset_subsubstream()
            # If using CRN across macroreplications...
            if self.crn_across_macroreps:
                # ...reset subsubstreams...
                bootstrap_rng.reset_subsubstream()
            # ...else if not using CRN across macrorep...
            else:
                # ...advance subsubstream.
                bootstrap_rng.advance_subsubstream()
            # Record objective or progress curve.
            if normalize:
                frac_intermediate_budgets = [budget / self.problem.factors["budget"] for budget in self.all_intermediate_budgets[mrep]]
                norm_est_objectives = [(est_objective - bs_optimal_obj_val) / bs_initial_opt_gap for est_objective in est_objectives]
                new_progress_curve = Curve(x_vals=frac_intermediate_budgets, y_vals=norm_est_objectives)
                bootstrap_curves.append(new_progress_curve)
            else:
                new_objective_curve = Curve(x_vals=self.all_intermediate_budgets[mrep], y_vals=est_objectives)
                bootstrap_curves.append(new_objective_curve)
        return bootstrap_curves

    def clear_runs(self):
        """
        Delete results from run() method and any downstream results.
        """
        attributes = ["n_macroreps",
                      "all_recommended_xs",
                      "all_intermediate_budgets"]
        for attribute in attributes:
            try:
                delattr(self, attribute)
            except Exception:
                pass
        self.clear_postreps()
        self.clear_stats()

    def clear_postreps(self):
        """
        Delete results from post_replicate() method and any downstream results.
        """
        attributes = ["n_postreps",
                      "n_postreps_init_opt",
                      "crn_across_budget",
                      "crn_across_macroreps",
                      "all_reevaluated_solns",
                      "all_post_replicates",
                      "all_est_objectives",
                      "all_prog_curves",
                      "initial_soln",
                      "ref_opt_soln"]
        for attribute in attributes:
            try:
                delattr(self, attribute)
            except Exception:
                pass
        self.clear_stats()

    def clear_stats(self):
        """
        Delete summary statistics associated with experiment.
        """
        attributes = ["areas",
                      "area_mean",
                      "area_std_dev",
                      "area_mean_CI",
                      "area_std_dev_CI",
                      "solve_tol",
                      "solve_times",
                      "solve_time_quantile",
                      "solve_time_quantile_CI"]
        for attribute in attributes:
            try:
                delattr(self, attribute)
            except Exception:
                pass

    def record_experiment_results(self):
        """
        Save wrapper_base.Experiment object to .pickle file.
        """
        with open(self.file_name_path, "wb") as file:
            pickle.dump(self, file, pickle.HIGHEST_PROTOCOL)


def trim_solver_results(problem, recommended_solns, intermediate_budgets):
    """
    Trim solutions recommended by solver after problem's max budget.

    Arguments
    ---------
    problem : base.Problem object
        Problem object on which the solver was run
    recommended_solutions : list of base.Solution objects
        solutions recommended by the solver
    intermediate_budgets : list of ints >= 0
        intermediate budgets at which solver recommended different solutions
    """
    # Remove solutions corresponding to intermediate budgets exceeding max budget.
    invalid_idxs = [idx for idx, element in enumerate(intermediate_budgets) if element > problem.factors["budget"]]
    for invalid_idx in sorted(invalid_idxs, reverse=True):
        del recommended_solns[invalid_idx]
        del intermediate_budgets[invalid_idx]
    # If no solution is recommended at the final budget,
    # re-recommend the latest recommended solution.
    # (Necessary for clean plotting of progress curves.)
    if intermediate_budgets[-1] < problem.factors["budget"]:
        recommended_solns.append(recommended_solns[-1])
        intermediate_budgets.append(problem.factors["budget"])
    return recommended_solns, intermediate_budgets


def read_experiment_results(file_name_path):
    """
    Read in wrapper_base.Experiment object from .pickle file.

    Arguments
    ---------
    file_name_path : string
        path of .pickle file for reading wrapper_base.Experiment object

    Returns
    -------
    experiment : wrapper_base.Experiment object
        experiment that has been run or has been post-processed
    """
    with open(file_name_path, "rb") as file:
        experiment = pickle.load(file)
    return experiment


def post_normalize(experiments, n_postreps_init_opt, crn_across_init_opt=True, proxy_init_val=None, proxy_opt_val=None, proxy_opt_x=None):
    """
    Construct objective curves and (normalized) progress curves
    for a collection of experiments on a given problem.

    Parameters
    ----------
    experiments : list of wrapper_base.Experiment objects
        experiments of different solvers on a common problem
    n_postreps_init_opt : int
        number of postreplications to take at initial x0 and optimal x*
    crn_across_init_opt : bool
        use CRN for post-replications at solutions x0 and x*?
    proxy_init_val : float
        known objective function value of initial solution
    proxy_opt_val : float
        proxy for or bound on optimal objective function value
    proxy_opt_x : tuple
        proxy for optimal solution
    """
    # Check that all experiments have the same problem and same
    # post-experimental setup.
    ref_experiment = experiments[0]
    for experiment in experiments:
        # Check if problems are the same.
        if experiment.problem != ref_experiment.problem:
            print("At least two experiments have different problem instances.")
        # Check if experiments have common number of macroreps.
        if experiment.n_macroreps != ref_experiment.n_macroreps:
            print("At least two experiments have different numbers of macro-replications.")
        # Check if experiment has been post-replicated and with common number of postreps.
        if getattr(experiment, "n_postreps", None) is None:
            print(f"The experiment of {experiment.solver_name} on {experiment.problem_name} has not been post-replicated.")
        elif getattr(experiment, "n_postreps", None) != getattr(ref_experiment, "n_postreps", None):
            print("At least two experiments have different numbers of post-replications.")
            print("Estimation of optimal solution x* may be based on different numbers of post-replications.")
    # Take post-replications at common x0.
    # Create, initialize, and attach RNGs for oracle.
        # Stream 0: reserved for post-replications.
    baseline_rngs = [MRG32k3a(s_ss_sss_index=[0, rng_index, 0]) for rng_index in range(experiment.problem.oracle.n_rngs)]
    x0 = ref_experiment.problem.factors["initial_solution"]
    if proxy_init_val is not None:
        x0_postreps = [proxy_init_val] * n_postreps_init_opt
    else:
        initial_soln = Solution(x0, ref_experiment.problem)
        initial_soln.attach_rngs(rng_list=baseline_rngs, copy=False)
        ref_experiment.problem.simulate(solution=initial_soln, m=n_postreps_init_opt)
        x0_postreps = list(initial_soln.objectives[:n_postreps_init_opt][:, 0])  # 0 <- assuming only one objective
    if crn_across_init_opt:
        # Reset each rng to start of its current substream.
        for rng in baseline_rngs:
            rng.reset_substream()
    # Determine (proxy for) optimal solution and/or (proxy for) its
    # objective function value. If deterministic (proxy for) f(x*),
    # create duplicate post-replicates to facilitate later bootstrapping.
    # If proxy for f(x*) is specified...
    if proxy_opt_val is not None:
        xstar = None
        xstar_postreps = [proxy_opt_val] * n_postreps_init_opt
    # ...else if proxy for x* is specified...
    elif proxy_opt_x is not None:
        xstar = proxy_opt_x
        # Take post-replications at xstar.
        opt_soln = Solution(xstar, ref_experiment.problem)
        opt_soln.attach_rngs(rng_list=baseline_rngs, copy=False)
        ref_experiment.problem.simulate(solution=opt_soln, m=n_postreps_init_opt)
        xstar_postreps = list(opt_soln.objectives[:n_postreps_init_opt][:, 0])  # 0 <- assuming only one objective
    # ...else if f(x*) is known...
    elif ref_experiment.problem.optimal_value is not None:
        xstar = None
        xstar_postreps = [ref_experiment.problem.optimal_value] * n_postreps_init_opt
    # ...else if x* is known...
    elif ref_experiment.problem.optimal_solution is not None:
        xstar = ref_experiment.problem.optimal_solution
        # Take post-replications at xstar.
        opt_soln = Solution(xstar, ref_experiment.problem)
        opt_soln.attach_rngs(rng_list=baseline_rngs, copy=False)
        ref_experiment.problem.simulate(solution=opt_soln, m=n_postreps_init_opt)
        xstar_postreps = list(opt_soln.objectives[:n_postreps_init_opt][:, 0])  # 0 <- assuming only one objective
    # ...else determine x* empirically as estimated best solution
    # found by any solver on any macroreplication.
    else:
        # TO DO: Simplify this block of code.
        best_est_objectives = np.zeros(len(experiments))
        for experiment_idx in range(len(experiments)):
            experiment = experiments[experiment_idx]
            exp_best_est_objectives = np.zeros(experiment.n_macroreps)
            for mrep in range(experiment.n_macroreps):
                exp_best_est_objectives[mrep] = np.max(experiment.problem.minmax[0] * np.array(experiment.all_est_objectives[mrep]))
            best_est_objectives[experiment_idx] = np.max(exp_best_est_objectives)
        best_experiment_idx = np.argmax(best_est_objectives)
        best_experiment = experiments[best_experiment_idx]
        best_exp_best_est_objectives = np.zeros(experiment.n_macroreps)
        for mrep in range(best_experiment.n_macroreps):
            best_exp_best_est_objectives[mrep] = np.max(best_experiment.problem.minmax[0] * np.array(best_experiment.all_est_objectives[mrep]))
        best_mrep = np.argmax(best_exp_best_est_objectives)
        best_budget_idx = np.argmax(best_experiment.all_est_objectives[best_mrep])
        xstar = best_experiment.all_recommended_xs[best_mrep][best_budget_idx]
        # Take post-replications at x*.
        opt_soln = Solution(xstar, ref_experiment.problem)
        opt_soln.attach_rngs(rng_list=baseline_rngs, copy=False)
        ref_experiment.problem.simulate(solution=opt_soln, m=n_postreps_init_opt)
        xstar_postreps = list(opt_soln.objectives[:n_postreps_init_opt][:, 0])  # 0 <- assuming only one objective
    # Compute signed initial optimality gap = f(x0) - f(x*).
    initial_obj_val = np.mean(x0_postreps)
    opt_obj_val = np.mean(xstar_postreps)
    initial_opt_gap = initial_obj_val - opt_obj_val
    # Store x0 and x* info and compute progress curves for each Experiment.
    for experiment in experiments:
        # DOUBLE-CHECK FOR SHALLOW COPY ISSUES.
        experiment.n_postreps_init_opt = n_postreps_init_opt
        experiment.crn_across_init_opt = crn_across_init_opt
        experiment.x0 = x0
        experiment.x0_postreps = x0_postreps
        experiment.xstar = xstar
        experiment.xstar_postreps = xstar_postreps
        # Construct objective and progress curves.
        experiment.objective_curves = []
        experiment.progress_curves = []
        for mrep in range(experiment.n_macroreps):
            est_objectives = []
            # Substitute estimates at x0 and x* (based on N postreplicates)
            # with new estimates (based on L postreplicates).
            for budget in range(len(experiment.all_intermediate_budgets[mrep])):
                if experiment.all_recommended_xs[mrep][budget] == x0:
                    est_objectives.append(np.mean(x0_postreps))
                elif experiment.all_recommended_xs[mrep][budget] == xstar:
                    est_objectives.append(np.mean(xstar_postreps))
                else:
                    est_objectives.append(experiment.all_est_objectives[mrep][budget])
            experiment.objective_curves.append(Curve(x_vals=experiment.all_intermediate_budgets[mrep], y_vals=est_objectives))
            # Normalize by initial optimality gap.
            norm_est_objectives = [(est_objective - opt_obj_val) / initial_opt_gap for est_objective in est_objectives]
            frac_intermediate_budgets = [budget / experiment.problem.factors["budget"] for budget in experiment.all_intermediate_budgets[mrep]]
            experiment.progress_curves.append(Curve(x_vals=frac_intermediate_budgets, y_vals=norm_est_objectives))
        # Save Experiment object to .pickle file.
        experiment.record_experiment_results()


def bootstrap_sample_all(experiments, bootstrap_rng, normalize=True):
    """
    Generate bootstrap samples of estimated progress curves (normalized
    and unnormalized) from a set of experiments.

    Arguments
    ---------
    experiments : list of list of wrapper_base.Experiment objects
        experiments of different solvers and/or problems
    bootstrap_rng : MRG32k3a object
        random number generator to use for bootstrapping
    normalize : bool
        normalize progress curves w.r.t. optimality gaps?
    Returns
    -------
    bootstrap_curves : list of list of list of wrapper_base.Curve objects
        bootstrapped estimated objective curves or estimated progress curves
        of all solutions from all macroreplications
    """
    n_solvers = len(experiments)
    n_problems = len(experiments[0])
    bootstrap_curves = [[[] for _ in range(n_problems)] for _ in range(n_solvers)]
    # Obtain a bootstrap sample from each experiment.
    for solver_idx in range(n_solvers):
        for problem_idx in range(n_problems):
            experiment = experiments[solver_idx][problem_idx]
            bootstrap_curves[solver_idx][problem_idx] = experiment.bootstrap_sample(bootstrap_rng, normalize)
            # Reset substream for next solver-problem pair.
            bootstrap_rng.reset_substream()
    # Advance substream of random number generator to prepare for next bootstrap sample.
    bootstrap_rng.advance_substream()
    return bootstrap_curves


def bootstrap_procedure(experiments, n_bootstraps, plot_type, beta=None, solve_tol=None, estimator=None, normalize=True):
    """
    Parameters
    ----------
    experiments : list of list of wrapper_base.Experiment objects
        experiments of different solvers and/or problems
    n_bootstraps : int > 0
        number of times to generate a bootstrap sample of estimated progress curves
    plot_type : string
        indicates which type of plot to produce
            "mean" : estimated mean progress curve
            "quantile" : estimated beta quantile progress curve
            "area_mean" : mean of area under progress curve
            "area_std_dev" : standard deviation of area under progress curve
            "solve_time_quantile" : beta quantile of solve time
            "solve_time_cdf" : cdf of solve time
            "cdf_solvability" : cdf solvability profile
            "quantile_solvability" : quantile solvability profile
            "diff_cdf_solvability" : difference of cdf solvability profiles
            "diff_quantile_solvability" : difference of quantile solvability profiles
    beta : float in (0,1)
        quantile to plot, e.g., beta quantile
    solve_tol : float in (0,1]
        relative optimality gap definining when a problem is solved
    estimator : float or wrapper_base.Curve object
        main estimator, e.g., mean convergence curve from an experiment
    normalize : bool
        normalize progress curves w.r.t. optimality gaps?

    Returns
    -------
    bs_CI_lower_bounds, bs_CI_upper_bounds = floats or wrapper_base.Curve objects
        lower and upper bound(s) of bootstrap CI(s), as floats or curves
    """
    # Create random number generator for bootstrap sampling.
    # Stream 1 dedicated for bootstrapping.
    bootstrap_rng = MRG32k3a(s_ss_sss_index=[1, 0, 0])
    # Obtain n_bootstrap replications.
    bootstrap_replications = []
    for bs_index in range(n_bootstraps):
        # Generate bootstrap sample of estimated objective/progress curves.
        bootstrap_curves = bootstrap_sample_all(experiments, bootstrap_rng=bootstrap_rng, normalize=normalize)
        # Apply the functional of the bootstrap sample.
        bootstrap_replications.append(functional_of_curves(bootstrap_curves, plot_type, beta=beta, solve_tol=solve_tol))
    # Distinguish cases where functional returns a scalar vs a curve.
    if plot_type in {"area_mean", "area_std_dev", "solve_time_quantile"}:
        # Functional returns a scalar.
        bs_CI_lower_bounds, bs_CI_upper_bounds = compute_bootstrap_CI(bootstrap_replications, conf_level=0.95, bias_correction=True, overall_estimator=estimator)
    elif plot_type in {"mean", "quantile", "solve_time_cdf", "cdf_solvability", "quantile_solvability", "diff_cdf_solvability", "diff_quantile_solvability"}:
        # Functional returns a curve.
        unique_budgets = list(np.unique([budget for curve in bootstrap_replications for budget in curve.x_vals]))
        bs_CI_lbs = []
        bs_CI_ubs = []
        for budget in unique_budgets:
            bootstrap_subreplications = [curve.lookup(x=budget) for curve in bootstrap_replications]
            sub_estimator = estimator.lookup(x=budget)
            bs_CI_lower_bound, bs_CI_upper_bound = compute_bootstrap_CI(bootstrap_subreplications,
                                                                        conf_level=0.95,
                                                                        bias_correction=True,
                                                                        overall_estimator=sub_estimator
                                                                        )
            bs_CI_lbs.append(bs_CI_lower_bound)
            bs_CI_ubs.append(bs_CI_upper_bound)
        bs_CI_lower_bounds = Curve(x_vals=unique_budgets, y_vals=bs_CI_lbs)
        bs_CI_upper_bounds = Curve(x_vals=unique_budgets, y_vals=bs_CI_ubs)
    return bs_CI_lower_bounds, bs_CI_upper_bounds


def functional_of_curves(bootstrap_curves, plot_type, beta=0.5, solve_tol=0.1):
    """
    Compute a functional of the bootstrapped objective/progress curves.

    Parameters
    ----------
    bootstrap_curves : list of list of list of wrapper_base.Curve objects
        bootstrapped estimated objective curves or estimated progress curves
        of all solutions from all macroreplications
    plot_type : string
        indicates which type of plot to produce
            "mean" : estimated mean progress curve
            "quantile" : estimated beta quantile progress curve
            "area_mean" : mean of area under progress curve
            "area_std_dev" : standard deviation of area under progress curve
            "solve_time_quantile" : beta quantile of solve time
            "solve_time_cdf" : cdf of solve time
            "cdf_solvability" : cdf solvability profile
            "quantile_solvability" : quantile solvability profile
            "diff_cdf_solvability" : difference of cdf solvability profiles
            "diff_quantile_solvability" : difference of quantile solvability profiles
    beta : float in (0,1)
        quantile to plot, e.g., beta quantile
    solve_tol : float in (0,1]
        relative optimality gap definining when a problem is solved

    Returns
    -------
    functional : list
        functional of bootstrapped curves, e.g, mean progress curves,
        mean area under progress curve, quantile of crossing time, etc.
    """
    if plot_type == "mean":
        # Single experiment --> returns a curve.
        functional = mean_of_curves(bootstrap_curves[0][0])
    elif plot_type == "quantile":
        # Single experiment --> returns a curve.
        functional = quantile_of_curves(bootstrap_curves[0][0], beta=beta)
    elif plot_type == "area_mean":
        # Single experiment --> returns a scalar.
        functional = np.mean([curve.compute_area_under_curve for curve in bootstrap_curves[0][0]])
    elif plot_type == "area_std_dev":
        # Single experiment --> returns a scalar.
        functional = np.std([curve.compute_area_under_curve for curve in bootstrap_curves[0][0]], ddof=1)
    elif plot_type == "solve_time_quantile":
        # Single experiment --> returns a scalar
        functional = np.quantile([curve.compute_crossing_time(threshold=solve_tol) for curve in bootstrap_curves[0][0]], q=beta)
    elif plot_type == "solver_time_cdf":
        # Single experiment --> returns a curve.
        functional = None  # Placeholder.
    elif plot_type == "cdf_solvability":
        # One solver, multiple problems --> returns a curve.
        functional = None  # Placeholder.
    elif plot_type == "quantile_solvability":
        # One solver, multiple problems --> returns a curve.
        functional = None  # Placeholder.
    elif plot_type == "diff_cdf_solvability":
        # Two solvers, multiple problems --> returns a curve.
        functional = None  # Placeholder.
    elif plot_type == "diff_quantile_solvability":
        # Two solvers, multiple problems --> returns a curve.
        functional = None  # Placeholder.
    else:
        print("Not a valid plot type.")
    return functional


def compute_bootstrap_CI(observations, conf_level=0.95, bias_correction=True, overall_estimator=None):
    """
    Construct a bootstrap confidence interval for an estimator.

    Parameters
    ----------
    observations : list
        estimators from all bootstrap instances
    conf_level : float in (0,1)
        confidence level for confidence intervals, i.e., 1-gamma
    bias_correction : bool
        use bias-corrected bootstrap CIs (via percentile method)?
    overall estimator : float
        estimator to compute bootstrap confidence interval of
        (required for bias corrected CI)

    Returns
    -------
    bs_CI_lower_bound : float
        lower bound of bootstrap CI
    bs_CI_upper_bound : float
        upper bound of bootstrap CI
    """
    # Compute bootstrapping confidence interval via percentile method.
    # See Efron (1981) "Nonparameteric Standard Errors and Confidence Intervals."
    if bias_correction:
        if overall_estimator is None:
            print("Estimator required to compute bias-corrected CIs.")
        # For biased-corrected CIs, see equation (4.4) on page 146.
        z0 = norm.ppf(np.mean(observations < overall_estimator))
        zconflvl = norm.ppf(conf_level)
        q_lower = norm.cdf(2 * z0 - zconflvl)
        q_upper = norm.cdf(2 * z0 + zconflvl)
    else:
        # For uncorrected CIs, see equation (4.3) on page 146.
        q_lower = (1 - conf_level) / 2
        q_upper = 1 - (1 - conf_level) / 2
    bs_CI_lower_bound = np.quantile(observations, q=q_lower)
    bs_CI_upper_bound = np.quantile(observations, q=q_upper)
    return bs_CI_lower_bound, bs_CI_upper_bound


def plot_bootstrap_CIs(bs_CI_lower_bounds, bs_CI_upper_bounds, color_str="C0"):
    """
    Plot bootstrap confidence intervals.

    Parameters
    ----------
    bs_CI_lower_bounds, bs_CI_upper_bounds : wrapper_base.Curve objects
        lower and upper bounds of bootstrap CIs, as curves
    color_str : str
        string indicating line color, e.g., "C0", "C1", etc.
    """
    bs_CI_lower_bounds.plot(color_str=color_str, curve_type="conf_bound")
    bs_CI_upper_bounds.plot(color_str=color_str, curve_type="conf_bound")


def report_max_halfwidth(curve_pairs, normalize):
    """
    Compute and print caption for max halfwidth of one or more bootstrap CI curves

    Parameters
    ----------
    curve_pairs : list of list of wrapper_base.Curve objects
        list of paired bootstrap CI curves
    normalize : bool
        normalize progress curves w.r.t. optimality gaps?
    """
    # Compute max halfwidth of bootstrap confidence intervals.
    min_lower_bound = np.inf
    max_upper_bound = -np.inf
    max_halfwidths = []
    for curve_pair in curve_pairs:
        min_lower_bound = min(min_lower_bound, min(curve_pair[0].y_vals))
        max_upper_bound = max(max_upper_bound, max(curve_pair[1].y_vals))
        max_halfwidths.append(0.5 * max_difference_of_curves(curve_pair[1], curve_pair[0]))
    max_halfwidth = max(max_halfwidths)
    # Print caption about max halfwidth.
    if normalize:
        xloc = 0.05
        yloc = -0.35
    else:
        # xloc = 0.05 * budget of the problem
        xloc = 0.05 * curve_pairs[0][0].x_vals[-1]
        yloc = min_lower_bound - 0.25 * (max_upper_bound - min_lower_bound)
    txt = f"The max halfwidth of the bootstrap CIs is {round(max_halfwidth, 2)}."
    plt.text(x=xloc, y=yloc, s=txt)


def plot_progress_curves(experiments, plot_type, beta=0.50, normalize=True, all_in_one=True, plot_CIs=True, print_max_hw=True):
    """
    Plot individual or aggregate progress curves for one or more solvers
    on a single problem.

    Arguments
    ---------
    experiments : list of wrapper_base.Experiment objects
        experiments of different solvers on a common problem
    plot_type : string
        indicates which type of plot to produce
            "all" : all estimated progress curves
            "mean" : estimated mean progress curve
            "quantile" : estimated beta quantile progress curve
    beta : float in (0,1)
        quantile to plot, e.g., beta quantile
    normalize : bool
        normalize progress curves w.r.t. optimality gaps?
    all_in_one : bool
        plot curves together or separately
    plot_CIs : bool
        plot bootstrapping confidence intervals?
    print_max_hw : bool
        print caption with max half-width
    """
    # Check if problems are the same with the same x0 and x*.
    ref_experiment = experiments[0]
    for experiment in experiments:
        # Check if problems are the same.
        if experiment.problem != ref_experiment.problem:
            print("At least two experiments have different problem instances.")
        if experiment.x0 != ref_experiment.x0:
            print("At least two experiments have different starting solutions.")
        if experiment.xstar != ref_experiment.xstar:
            print("At least two experiments have different optimal solutions.")
    # Set up plot.
    n_experiments = len(experiments)
    if all_in_one:
        ref_experiment = experiments[0]
        stylize_plot(plot_type=plot_type,
                     solver_name="SOLVER SET",
                     problem_name=ref_experiment.problem.name,
                     normalize=normalize,
                     budget=ref_experiment.problem.factors["budget"],
                     beta=beta
                     )
        solver_curve_handles = []
        if print_max_hw:
            curve_pairs = []
        for exp_idx in range(n_experiments):
            experiment = experiments[exp_idx]
            color_str = "C" + str(exp_idx)
            if plot_type == "all":
                # Plot all estimated progress curves.
                if normalize:
                    handle = experiment.progress_curves[0].plot(color_str=color_str)
                    for curve in experiment.progress_curves[1:]:
                        curve.plot(color_str=color_str)
                else:
                    handle = experiment.objective_curves[0].plot(color_str=color_str)
                    for curve in experiment.objective_curves[1:]:
                        curve.plot(color_str=color_str)
            elif plot_type == "mean":
                # Plot estimated mean progress curve.
                if normalize:
                    estimator = mean_of_curves(experiment.progress_curves)
                else:
                    estimator = mean_of_curves(experiment.objective_curves)
                handle = estimator.plot(color_str=color_str)
            elif plot_type == "quantile":
                # Plot estimated beta-quantile progress curve.
                if normalize:
                    estimator = quantile_of_curves(experiment.progress_curves, beta)
                else:
                    estimator = quantile_of_curves(experiment.objective_curves, beta)
                handle = estimator.plot(color_str=color_str)
            else:
                print("Not a valid plot type.")
            solver_curve_handles.append(handle)
            if plot_CIs:
                # Note: "experiments" needs to be a list of list of Experiments.
                bs_CI_lb_curve, bs_CI_ub_curve = bootstrap_procedure(experiments=[[experiment]],
                                                                     n_bootstraps=100,
                                                                     plot_type=plot_type,
                                                                     beta=beta,
                                                                     estimator=estimator,
                                                                     normalize=normalize
                                                                     )
                plot_bootstrap_CIs(bs_CI_lb_curve, bs_CI_ub_curve, color_str=color_str)
                if print_max_hw:
                    curve_pairs.append([bs_CI_lb_curve, bs_CI_ub_curve])
        plt.legend(handles=solver_curve_handles, labels=[experiment.solver.name for experiment in experiments], loc="upper right")
        if print_max_hw:
            report_max_halfwidth(curve_pairs=curve_pairs, normalize=normalize)
        save_plot(solver_name="SOLVER SET",
                  problem_name=ref_experiment.problem.name,
                  plot_type=plot_type,
                  normalize=normalize
                  )
    else:  # Plot separately
        for experiment in experiments:
            stylize_plot(plot_type=plot_type,
                         solver_name=experiment.solver.name,
                         problem_name=experiment.problem.name,
                         normalize=normalize,
                         budget=experiment.problem.factors["budget"],
                         beta=beta
                         )
            if plot_type == "all":
                # Plot all estimated progress curves.
                if normalize:
                    for curve in experiment.progress_curves:
                        curve.plot()
                else:
                    for curve in experiment.objective_curves:
                        curve.plot()
            elif plot_type == "mean":
                # Plot estimated mean progress curve.
                if normalize:
                    estimator = mean_of_curves(experiment.progress_curves)
                else:
                    estimator = mean_of_curves(experiment.objective_curves)
                estimator.plot()
            elif plot_type == "quantile":
                # Plot estimated beta-quantile progress curve.
                if normalize:
                    estimator = quantile_of_curves(experiment.progress_curves, beta)
                else:
                    estimator = quantile_of_curves(experiment.objective_curves, beta)
                estimator.plot()
            else:
                print("Not a valid plot type.")
            if plot_CIs:
                # Note: "experiments" needs to be a list of list of Experiments.
                bs_CI_lb_curve, bs_CI_ub_curve = bootstrap_procedure(experiments=[[experiment]],
                                                                     n_bootstraps=100,
                                                                     plot_type=plot_type,
                                                                     beta=beta,
                                                                     estimator=estimator,
                                                                     normalize=normalize
                                                                     )
                plot_bootstrap_CIs(bs_CI_lb_curve, bs_CI_ub_curve)
                if print_max_hw:
                    report_max_halfwidth(curve_pairs=[[bs_CI_lb_curve, bs_CI_ub_curve]], normalize=normalize)
            save_plot(solver_name=experiment.solver.name,
                      problem_name=experiment.problem.name,
                      plot_type=plot_type,
                      normalize=normalize
                      )


def stylize_plot(plot_type, solver_name, problem_name, normalize, budget=None,
                 beta=None):
    """
    Create new figure. Add labels to plot and reformat axes.

    Arguments
    ---------
    plot_type : string
        indicates which type of plot to produce
            "all" : all estimated progress curves
            "mean" : estimated mean progress curve
            "quantile" : estimated beta quantile progress curve
    solver_name : string
        name of solver
    problem_name : string
        name of problem
    normalize : Boolean
        normalize progress curves w.r.t. optimality gaps?
    budget : int
        budget of problem, measured in function evaluations
    beta : float in (0,1) (optional)
        quantile for quantile aggregate progress curve, e.g., beta quantile
    """
    plt.figure()
    # Format axes, axis labels, title, and tick marks.
    if normalize:
        xlabel = "Fraction of Budget"
        ylabel = "Fraction of Initial Optimality Gap"
        xlim = (0, 1)
        ylim = (-0.1, 1.1)
        title = f"{solver_name} on {problem_name}\n"
    elif not normalize:
        xlabel = "Budget"
        ylabel = "Objective Function Value"
        xlim = (0, budget)
        ylim = None
        title = f"{solver_name} on {problem_name} \n Unnormalized "
    if plot_type == "all":
        title = title + "Estimated Progress Curves"
    elif plot_type == "mean":
        title = title + "Mean Progress Curve"
    elif plot_type == "quantile":
        title = title + f"{round(beta, 2)}-Quantile Progress Curve"
    plt.xlabel(xlabel, size=14)
    plt.ylabel(ylabel, size=14)
    plt.title(title, size=14)
    plt.xlim(xlim)
    if ylim is not None:
        plt.ylim(ylim)
    plt.tick_params(axis="both", which="major", labelsize=12)


def stylize_solvability_plot(solver_name, problem_name, solve_tol, plot_type, beta=0.5):
    """
    Create new figure. Add labels to plot and reformat axes.

    Arguments
    ---------
    solver_name : string
        name of solver
    problem_name : string
        name of problem
    solve_tol : float in (0,1]
        relative optimality gap definining when a problem is solved
    plot_type : string
        type of plot
            - "single"
            - "cdf"
            - "quantile"
    beta : float in (0,1)
        quantile to compute, e.g., beta quantile
    """
    plt.figure()
    # Format axes, axis labels, title, and tick marks.
    xlabel = "Fraction of Budget"
    xlim = (0, 1)
    ylim = (0, 1.05)
    if plot_type == "single":
        ylabel = "Fraction of Macroreplications Solved"
        title = solver_name + " on " + problem_name + "\n"
        title = title + "CDF of " + str(round(solve_tol, 2)) + "-Solve Times"
    elif plot_type == "cdf":
        ylabel = "Mean Solve Percentage"
        title = "CDF Solvability Profile for " + solver_name + "\n"
        title = title + "Profile of CDF of " + str(round(solve_tol, 2)) + "-Solve Times"
    elif plot_type == "quantile":
        ylabel = "Proportion of Problems Solved"
        title = "Quantile Solvability Profile for " + solver_name + "\n"
        title = title + "Profile of " + str(round(beta, 2)) + "-Quantiles of " + str(round(solve_tol, 2)) + "-Solve Times"
    plt.xlabel(xlabel, size=14)
    plt.ylabel(ylabel, size=14)
    plt.title(title, size=14)
    plt.xlim(xlim)
    plt.ylim(ylim)
    plt.tick_params(axis="both", which="major", labelsize=12)


def stylize_difference_plot(solve_tol):
    """
    Create new figure. Add labels to plot and reformat axes.

    Parameters
    ----------
    solve_tol : float in (0,1]
        relative optimality gap definining when a problem is solved
    """
    plt.figure()
    # Format axes, axis labels, title, and tick marks.
    xlabel = "Fraction of Budget"
    xlim = (0, 1)
    ylabel = "Difference in Fraction of Macroreplications Solved"
    title = "SOLVERSET on PROBLEMSET\n"
    title = title + f"Difference of {round(solve_tol, 2)}-Solvability Curves"
    plt.xlabel(xlabel, size=14)
    plt.ylabel(ylabel, size=14)
    plt.title(title, size=14)
    plt.xlim(xlim)
    plt.tick_params(axis="both", which="major", labelsize=12)


def stylize_area_plot(solver_name):
    """
    Create new figure for area plots. Add labels to plot and reformat axes.

    Arguments
    ---------
    solver_name : string
        name of solver
    """
    plt.figure()
    # Format axes, axis labels, title, and tick marks.
    xlabel = "Mean Area"
    ylabel = "Std Dev of Area"
    xlim = (0, 1)
    ylim = (0, 0.5)
    title = solver_name + "\n"
    title = title + "Areas Under Progress Curves"
    plt.xlabel(xlabel, size=14)
    plt.ylabel(ylabel, size=14)
    plt.title(title, size=14)
    plt.xlim(xlim)
    plt.ylim(ylim)
    plt.tick_params(axis="both", which="major", labelsize=12)


def save_plot(solver_name, problem_name, plot_type, normalize, extra=None):
    """
    Create new figure. Add labels to plot and reformat axes.

    Arguments
    ---------
    solver_name : string
        name of solver
    problem_name : string
        name of problem
    plot_type : string
        indicates which type of plot to produce
            "all" : all estimated progress curves
            "mean" : estimated mean progress curve
            "quantile" : estimated beta quantile progress curve
            "cdf solve times" : cdf of solve times
            "cdf solvability" : cdf solvability profile
            "quantile solvability" : quantile solvability profile
            "area" : area scatterplot
            "difference" : difference profile
    normalize : Boolean
        normalize progress curves w.r.t. optimality gaps?
    extra : float (or list of floats)
        extra number(s) specifying quantile (e.g., beta) and/or solve tolerance
    """
    # Form string name for plot filename.
    if plot_type == "all":
        plot_name = "all_prog_curves"
    elif plot_type == "mean":
        plot_name = "mean_prog_curve"
    elif plot_type == "quantile":
        plot_name = "quantile_prog_curve"
    elif plot_type == "cdf solve times":
        plot_name = f"cdf_{extra}_solve_times"
    elif plot_type == "cdf solvability":
        plot_name = f"profile_cdf_{extra}_solve_times"
    elif plot_type == "quantile solvability":
        plot_name = f"profile_{extra[1]}_quantile_{extra[0]}_solve_times"
    elif plot_type == "area":
        plot_name = "area_scatterplot"
    elif plot_type == "difference":
        plot_name = "difference_profile"
    if not normalize:
        plot_name = plot_name + "_unnorm"
    path_name = f"experiments/plots/{solver_name}_on_{problem_name}_{plot_name}.png"
    plt.savefig(path_name, bbox_inches="tight")


def area_under_prog_curve(prog_curve, frac_inter_budgets):
    """
    Compute the area under a normalized estimated progress curve.

    Arguments
    ---------
    prog_curve : numpy array
        normalized estimated progress curve for a macroreplication
    frac_inter_budgets : numpy array
        fractions of budget at which the progress curve is defined

    Returns
    -------
    area : float
        area under the estimated progress curve
    """
    area = np.dot(prog_curve[:-1], np.diff(frac_inter_budgets))
    return area


def solve_time_of_prog_curve(prog_curve, frac_inter_budgets, solve_tol):
    """
    Compute the solve time of a normalized estimated progress curve.

    Arguments
    ---------
    prog_curve : numpy array
        normalized estimated progress curves for a macroreplication
    frac_inter_budgets : numpy array
        fractions of budget at which the progress curve is defined
    solve_tol : float in (0,1]
        relative optimality gap definining when a problem is solved

    Returns
    -------
    solve_time : float
        time at which the normalized progress curve first drops below
        solve_tol, i.e., the "alpha" solve time
    """
    # Alpha solve time defined as infinity if the problem is not solved
    # to within solve_tol.
    solve_time = np.inf
    # Pass over progress curve to find first solve_tol crossing time.
    for i in range(len(prog_curve)):
        if prog_curve[i] < solve_tol:
            solve_time = frac_inter_budgets[i]
            break
    return solve_time


class MetaExperiment(object):
    """
    Base class for running one or more solver on one or more problem.

    Attributes
    ----------
    solver_names : list of strings
        list of solver names
    n_solvers : int > 0
        number of solvers
    problem_names : list of strings
        list of problem names
    n_problems : int > 0
        number of problems
    all_solver_fixed_factors : dict of dict
        fixed solver factors for each solver
            outer key is solver name
            inner key is factor name
    all_problem_fixed_factors : dict of dict
        fixed problem factors for each problem
            outer key is problem name
            inner key is factor name
    all_oracle_fixed_factors : dict of dict
        fixed oracle factors for each problem
            outer key is problem name
            inner key is factor name
    experiments : list of list of Experiment objects
        all problem-solver pairs

    Arguments
    ---------
    solver_names : list of strings
        list of solver names
    problem_names : list of strings
        list of problem names
    fixed_factors_filename : string
        name of .py file containing dictionaries of fixed factors
        for solvers/problems/oracles.
    """
    def __init__(self, solver_names, problem_names, fixed_factors_filename=None):
        self.solver_names = solver_names
        self.n_solvers = len(solver_names)
        self.problem_names = problem_names
        self.n_problems = len(problem_names)
        # Read in fixed solver/problem/oracle factors from .py file in the Experiments folder.
        # File should contain three dictionaries of dictionaries called
        #   - all_solver_fixed_factors
        #   - all_problem_fixed_factors
        #   - all_oracle_fixed_factors
        fixed_factors_filename = "experiments.inputs." + fixed_factors_filename
        all_factors = importlib.import_module(fixed_factors_filename)
        self.all_solver_fixed_factors = getattr(all_factors, "all_solver_fixed_factors")
        self.all_problem_fixed_factors = getattr(all_factors, "all_problem_fixed_factors")
        self.all_oracle_fixed_factors = getattr(all_factors, "all_oracle_fixed_factors")
        # Create all problem-solver pairs (i.e., instances of Experiment class)
        self.experiments = []
        for solver_name in solver_names:
            solver_experiments = []
            for problem_name in problem_names:
                try:
                    # If a file exists, read in Experiment object.
                    with open(f"experiments/outputs/{solver_name}_on_{problem_name}.pickle", "rb") as file:
                        next_experiment = pickle.load(file)
                    # TO DO: Check if the solver/problem/oracle factors in the file match
                    # those for the MetaExperiment.
                except Exception:
                    # If no file exists, create new Experiment object.
                    print(f"No experiment file exists for {solver_name} on {problem_name}. Creating new experiment.")
                    next_experiment = Experiment(solver_name=solver_name,
                                                 problem_name=problem_name,
                                                 solver_fixed_factors=self.all_solver_fixed_factors[solver_name],
                                                 problem_fixed_factors=self.all_problem_fixed_factors[problem_name],
                                                 oracle_fixed_factors=self.all_oracle_fixed_factors[problem_name])
                    # next_experiment.record_experiment_results()
                solver_experiments.append(next_experiment)
            self.experiments.append(solver_experiments)

    def run(self, n_macroreps=10):
        """
        Run n_macroreps of each solver on each problem.

        Arguments
        ---------
        n_macroreps : int
            number of macroreplications of the solver to run on the problem
        """
        for solver_index in range(self.n_solvers):
            for problem_index in range(self.n_problems):
                experiment = self.experiments[solver_index][problem_index]
                # If the problem-solver pair has not been run in this way before,
                # run it now and save result to .pickle file.
                if (getattr(experiment, "n_macroreps", None) != n_macroreps):
                    print(f"Running {experiment.solver.name} on {experiment.problem.name}.")
                    experiment.clear_runs()
                    experiment.run(n_macroreps)

    def post_replicate(self, n_postreps, n_postreps_init_opt, crn_across_budget=True, crn_across_macroreps=False):
        """
        For each problem-solver pair, run postreplications at solutions
        recommended by the solver on each macroreplication.

        Arguments
        ---------
        n_postreps : int
            number of postreplications to take at each recommended solution
        n_postreps_init_opt : int
            number of postreplications to take at initial x0 and optimal x*
        crn_across_budget : bool
            use CRN for post-replications at solutions recommended at different times?
        crn_across_macroreps : bool
            use CRN for post-replications at solutions recommended on different macroreplications?
        """
        for solver_index in range(self.n_solvers):
            for problem_index in range(self.n_problems):
                experiment = self.experiments[solver_index][problem_index]
                # If the problem-solver pair has not been post-processed in this way before,
                # post-process it now.
                if (getattr(experiment, "n_postreps", None) != n_postreps
                        or getattr(experiment, "n_postreps_init_opt", None) != n_postreps_init_opt
                        or getattr(experiment, "crn_across_budget", None) != crn_across_budget
                        or getattr(experiment, "crn_across_macroreps", None) != crn_across_macroreps):
                    print(f"Post-processing {experiment.solver.name} on {experiment.problem.name}.")
                    experiment.clear_postreps()
                    experiment.post_replicate(n_postreps, n_postreps_init_opt, crn_across_budget, crn_across_macroreps)

    def plot_progress_curves(self, plot_type, beta=0.50, normalize=True):
        """
        Produce plots of the solvers' aggregated performances on each problem.

        Arguments
        ---------
        plot_type : string
            indicates which type of plot to produce
                "mean" : estimated mean progress curve
                "quantile" : estimated beta quantile progress curve
        beta : float in (0,1)
            quantile to plot, e.g., beta quantile
        normalize : Boolean
            normalize progress curves w.r.t. optimality gaps?
        """
        for problem_index in range(self.n_problems):
            stylize_plot(plot_type=plot_type, solver_name="SOLVERSET", problem_name=self.problem_names[problem_index], normalize=normalize, budget=self.experiments[0][problem_index].problem.factors["budget"], beta=beta)
            for solver_index in range(self.n_solvers):
                experiment = self.experiments[solver_index][problem_index]
                if plot_type == "mean":
                    # Plot estimated mean progress curve.
                    if normalize:
                        estimator = np.mean(experiment.all_prog_curves, axis=0)
                        plt.step(experiment.unique_frac_budgets, estimator, where="post")
                    else:
                        estimator = np.mean(experiment.all_est_objectives, axis=0)
                        plt.step(experiment.unique_budgets, estimator, where="post")
                elif plot_type == "quantile":
                    # Plot estimated beta-quantile progress curve.
                    if normalize:
                        estimator = np.quantile(experiment.all_prog_curves, q=beta, axis=0)
                        plt.step(experiment.unique_frac_budgets, estimator, where="post")
                    else:
                        estimator = np.quantile(experiment.all_est_objectives, q=beta, axis=0)
                        plt.step(experiment.unique_budgets, estimator, where="post")
                else:
                    print("Not a valid plot type.")
            plt.legend(labels=self.solver_names, loc="upper right")
            save_plot(solver_name="SOLVERSET", problem_name=self.problem_names[problem_index], plot_type=plot_type, normalize=normalize)

    def plot_solvability_curves(self, solve_tols=[0.10]):
        """
        Produce the solvability curve (cdf of the solve times) for solvers
        on each problem.

        Arguments
        ---------
        solve_tols : list of floats in (0,1]
            relative optimality gap(s) definining when a problem is solved
        """
        for problem_index in range(self.n_problems):
            # Compute solve times for each solver at each tolerance
            for solver_index in range(self.n_solvers):
                experiment = self.experiments[solver_index][problem_index]
                experiment.compute_solvability(solve_tols=solve_tols)
            # For each tolerance, plot solvability curves for each solver
            for tol_index in range(len(solve_tols)):
                solve_tol = solve_tols[tol_index]
                stylize_solvability_plot(solver_name="SOLVERSET", problem_name=self.problem_names[problem_index], solve_tol=solve_tol, plot_type="single")
                for solver_index in range(self.n_solvers):
                    experiment = self.experiments[solver_index][problem_index]
                    # Construct matrix showing when macroreplications are solved.
                    solve_matrix = np.zeros((experiment.n_macroreps, len(experiment.unique_frac_budgets)))
                    # Pass over progress curves to find first solve_tol crossing time.
                    for mrep in range(experiment.n_macroreps):
                        for budget_index in range(len(experiment.unique_frac_budgets)):
                            if experiment.solve_times[tol_index][mrep] <= experiment.unique_frac_budgets[budget_index]:
                                solve_matrix[mrep][budget_index] = 1
                    # Compute proportion of macroreplications "solved" by intermediate budget.
                    estimator = np.mean(solve_matrix, axis=0)
                    # Plot solvability curve.
                    plt.step(experiment.unique_frac_budgets, estimator, where="post")
                plt.legend(labels=self.solver_names, loc="lower right")
                save_plot(solver_name="SOLVERSET", problem_name=self.problem_names[problem_index], plot_type="cdf solve times", normalize=True, extra=solve_tol)

    def plot_area_scatterplot(self, plot_CIs=True, all_in_one=True):
        """
        Plot a scatter plot of mean and standard deviation of area under progress curves.
        Either one plot for each solver or one plot for all solvers.
        """
        # Compute areas under progress curves (and summary statistics) for each
        # problem-solver pair.
        for solver_index in range(self.n_solvers):
            for problem_index in range(self.n_problems):
                experiment = self.experiments[solver_index][problem_index]
                experiment.compute_area_stats(compute_CIs=plot_CIs)
                experiment.record_experiment_results()
        # Produce plot(s).
        if all_in_one:
            stylize_area_plot(solver_name="SOLVERSET")
        for solver_index in range(self.n_solvers):
            if not all_in_one:
                stylize_area_plot(solver_name=self.solver_names[solver_index])
            # Aggregate statistics.
            area_means = [self.experiments[solver_index][problem_index].area_mean for problem_index in range(self.n_problems)]
            area_std_devs = [self.experiments[solver_index][problem_index].area_std_dev for problem_index in range(self.n_problems)]
            if plot_CIs:
                area_means_CIs = [self.experiments[solver_index][problem_index].area_mean_CI for problem_index in range(self.n_problems)]
                area_std_devs_CIs = [self.experiments[solver_index][problem_index].area_std_dev_CI for problem_index in range(self.n_problems)]
            # Plot scatter plot.
            if plot_CIs:
                xerr = [np.array(area_means) - np.array(area_means_CIs)[:, 0], np.array(area_means_CIs)[:, 1] - np.array(area_means)]
                yerr = [np.array(area_std_devs) - np.array(area_std_devs_CIs)[:, 0], np.array(area_std_devs_CIs)[:, 1] - np.array(area_std_devs)]
                plt.errorbar(x=area_means,
                             y=area_std_devs,
                             xerr=xerr,
                             yerr=yerr
                             )
            else:
                plt.scatter(x=area_means, y=area_std_devs)
            if not all_in_one:
                save_plot(solver_name=self.solver_names[solver_index], problem_name="PROBLEMSET", plot_type="area", normalize=True)
        if all_in_one:
            plt.legend(labels=self.solver_names, loc="upper right")
            save_plot(solver_name="SOLVERSET", problem_name="PROBLEMSET", plot_type="area", normalize=True)

    def plot_solvability_profiles(self, solve_tol=0.1, beta=0.5, ref_solver=None):
        """
        Plot the solvability profiles for each solver on a set of problems.
        Three types of plots:
            1) cdf solvability profile
            2) quantile solvability profile
            3) difference solvability profile

        Arguments
        ---------
        solve_tol : float in (0,1]
            relative optimality gap definining when a problem is solved
        beta : float in (0,1)
            quantile to compute, e.g., beta quantile
        ref_solver : str
            name of solver used as benchmark for difference profiles
        """
        all_solver_unique_frac_budgets = []
        all_solvability_profiles = []
        stylize_solvability_plot(solver_name="SOLVERSET", problem_name="PROBLEMSET", solve_tol=solve_tol, beta=None, plot_type="cdf")
        for solver_index in range(self.n_solvers):
            solvability_curves = []
            all_budgets = []
            for problem_index in range(self.n_problems):
                experiment = self.experiments[solver_index][problem_index]
                # Compute solve times.
                experiment.compute_solvability(solve_tols=[solve_tol])
                experiment.compute_solvability_quantiles(beta=beta, compute_CIs=False)
                # Construct matrix showing when macroreplications are solved.
                solve_matrix = np.zeros((experiment.n_macroreps, len(experiment.unique_frac_budgets)))
                # Pass over progress curves to find first solve_tol crossing time.
                for mrep in range(experiment.n_macroreps):
                    for budget_index in range(len(experiment.unique_frac_budgets)):
                        # TO DO: HARD-CODED for tol_index=0
                        if experiment.solve_times[0][mrep] <= experiment.unique_frac_budgets[budget_index]:
                            solve_matrix[mrep][budget_index] = 1
                solvability_curves.append(list(np.mean(solve_matrix, axis=0)))
                all_budgets.append(list(experiment.unique_frac_budgets))
            # Compute the solver's solvability profile.
            solver_unique_frac_budgets = np.unique([budget for budgets in all_budgets for budget in budgets])
            all_solve_matrix = np.zeros((self.n_problems, len(solver_unique_frac_budgets)))
            for problem_index in range(self.n_problems):
                for budget_index in range(len(solver_unique_frac_budgets)):
                    problem_budget_index = np.max(np.where(np.array(all_budgets[problem_index]) <= solver_unique_frac_budgets[budget_index]))
                    all_solve_matrix[problem_index][budget_index] = solvability_curves[problem_index][problem_budget_index]
            solvability_profile = np.mean(all_solve_matrix, axis=0)
            # Plot the solver's solvability profile.
            plt.step(solver_unique_frac_budgets, solvability_profile, where="post")
            # Append results.
            all_solver_unique_frac_budgets.append(solver_unique_frac_budgets)
            all_solvability_profiles.append(solvability_profile)
        plt.legend(labels=self.solver_names, loc="lower right")
        # TO DO: Change the y-axis label produced by this helper function.
        save_plot(solver_name="SOLVERSET", problem_name="PROBLEMSET", plot_type="cdf solvability", normalize=True, extra=solve_tol)
        # Plot solvability profiles for each solver.
        stylize_solvability_plot(solver_name="SOLVERSET", problem_name="PROBLEMSET", solve_tol=solve_tol, beta=beta, plot_type="quantile")
        for solver_index in range(self.n_solvers):
            solvability_quantiles = []
            for problem_index in range(self.n_problems):
                experiment = self.experiments[solver_index][problem_index]
                # TO DO: Hard-coded for first tol_index
                solvability_quantiles.append(experiment.solve_time_quantiles[0])
            plt.step(np.sort(solvability_quantiles + [0, 1]), np.append(np.linspace(start=0, stop=1, num=self.n_problems + 1), [1]), where="post")
        save_plot(solver_name="SOLVERSET", problem_name="PROBLEMSET", plot_type="quantile solvability", normalize=True, extra=[solve_tol, beta])
        # Plot difference solvability profiles. (Optional)
        if ref_solver is not None:
            stylize_difference_plot(solve_tol=solve_tol)
            non_ref_solvers = [solver_name for solver_name in self.solver_names if solver_name != ref_solver]
            ref_solver_index = self.solver_names.index(ref_solver)
            for solver_index in range(self.n_solvers):
                solver_name = self.solver_names[solver_index]
                if solver_name is not ref_solver:
                    diff_budgets, diff_solvability_profile = compute_difference_solvability_profile(budgets_1=all_solver_unique_frac_budgets[solver_index],
                                                                                                    solv_profile_1=all_solvability_profiles[solver_index],
                                                                                                    budgets_2=all_solver_unique_frac_budgets[ref_solver_index],
                                                                                                    solv_profile_2=all_solvability_profiles[ref_solver_index]
                                                                                                    )
                    plt.step(diff_budgets, diff_solvability_profile, where="post")
            plt.plot([0, 1], [0, 0], color="black", linestyle="--")
            plt.legend(labels=[non_ref_solver + " - " + ref_solver for non_ref_solver in non_ref_solvers], loc="upper right")
            save_plot(solver_name="SOLVERSET", problem_name="PROBLEMSET", plot_type="difference", normalize=True)


def compute_difference_solvability_profile(budgets_1, solv_profile_1, budgets_2, solv_profile_2):
    """
    Calculate the difference of two solvability profiles (Solver 1 - Solver 2).

    Parameters
    ----------
    budgets_1 : list of floats
        list of intermediate budgets for Solver 1
    solv_profile_1 : list of floats
        solvability profile of Solver 1
    budgets_2 : list of floats
        list of intermediate budgets for Solver 2
    solv_profile_2 : list of floats
        solvability profile of Solver 2
    """
    diff_budgets = np.unique(list(budgets_1) + list(budgets_2))
    diff_solvability_profile = []
    for budget in diff_budgets:
        solv_profile_1_index = np.max(np.where(budgets_1 <= budget))
        solv_profile_2_index = np.max(np.where(budgets_2 <= budget))
        diff_solvability_profile.append(solv_profile_1[solv_profile_1_index] - solv_profile_2[solv_profile_2_index])
    return(diff_budgets, diff_solvability_profile)
