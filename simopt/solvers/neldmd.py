"""
Summary
-------
Nelder-Mead
The algorithm maintains a simplex of points that moves around the feasible 
region according to certain geometric operations: reflection, expansion, 
scontraction, and shrinking.
"""
from base import Solution, Solver
import numpy as np
import math
import warnings
warnings.filterwarnings("ignore")

class NELDMD(Solver):
    """
    REFERENCE		
    Russell R. Barton, John S. Ivey, Jr., (1996)
    Nelder-Mead Simplex Modifications for Simulation 
    Optimization. Management Science 42(7):954-973.

    Attributes
    ----------
    name : string
        name of solver
    objective_type : string
        description of objective types:
            "single" or "multi"
    constraint_type : string
        description of constraints types:
            "unconstrained", "box", "deterministic", "stochastic"
    variable_type : string
        description of variable types:
            "discrete", "continuous", "mixed"
    gradient_needed : bool
        indicates if gradient of objective function is needed
    factors : dict
        changeable factors (i.e., parameters) of the solver
    specifications : dict
        details of each factor (for GUI, data validation, and defaults)
    rng_list : list of rng.MRG32k3a objects
        list of RNGs used for the solver's internal purposes

    Arguments
    ---------
    name : str
        user-specified name for solver
    fixed_factors : dict
        fixed_factors of the solver

    See also
    --------
    base.Solver
    """
    def __init__(self, name="NELDMD", fixed_factors={}):
        self.name = name
        self.objective_type = "single"
        self.constraint_type = "deterministic"
        self.variable_type = "continuous"
        self.gradient_needed = False
        self.specifications = {
            "crn_across_solns": {
                "description": "Use CRN across solutions?",
                "datatype": bool,
                "default": True
            },
            "r": {
                "description": "number of replications taken at each solution",
                "datatype": int,
                "default": 30
            },
            "alpha": {
                "description": "reflection coefficient > 0",
                "datatype": float,
                "default": 1.
            },
            "gammap": {
                "description": "expansion coefficient > 1",
                "datatype": float,
                "default": 2.
            },
            "betap": {
                "description": "contraction coefficient > 0, < 1",
                "datatype": float,
                "default": 0.5
            },
            "delta": {
                "description": "shrink factor > 0, < 1",
                "datatype": float,
                "default": 0.5
            },
            "sensitivity": {
                "description": "shrinking scale for VarBds (bounds)",
                "datatype": float,
                "default": 10**(-7)
            }
        }
        self.check_factor_list = {
            "crn_across_solns": self.check_crn_across_solns,
            "r": self.check_r,
            "alpha": self.check_alpha,
            "gammap": self.check_gammap,
            "betap": self.check_betap,
            "delta": self.check_delta,
            "sensitivity": self.check_sensitivity
        }
        super().__init__(fixed_factors)

    def check_r(self):
        return self.factors["r"] > 0

    def check_alpha(self):
        return self.factors["alpha"] > 0

    def check_gammap(self):
        return self.factors["gammap"] > 1

    def check_betap(self):
        return (self.factors["betap"] > 0) & (self.factors["betap"] < 1)

    def check_delta(self):
        return (self.factors["delta"] > 0) & (self.factors["delta"] < 1)

    def check_sensitivity(self):
        return self.factors["sensitivity"] > 0
    
    def solve(self, problem):
        """
        Run a single macroreplication of a solver on a problem.

        Arguments
        ---------
        problem : Problem object
            simulation-optimization problem to solve

        Returns
        -------
        recommended_solns : list of Solution objects
            list of solutions recommended throughout the budget
        intermediate_budgets : list of ints
            list of intermediate budgets when recommended solutions changes
        """
        n_pts = problem.dim + 1
        # Check for sufficiently large budget
        if problem.factors["budget"] <  self.factors["r"]*n_pts:
            print('Budget is too small for a good quality run of Nelder-Mead.')
            return
        # Determine max number of solutions that can be sampled within budget
        max_num_sol = int(np.floor(problem.factors["budget"]/self.factors["r"]))
        # Shrink variable bounds to avoid floating errors
        if problem.lower_bounds != None:
            lower_bounds = tuple(map(lambda i: i + self.factors["sensitivity"], problem.lower_bounds))
        else:
            lower_bounds = None
        if problem.upper_bounds != None:
            upper_bounds = tuple(map(lambda i: i - self.factors["sensitivity"], problem.upper_bounds))
        else:
            upper_bounds = None
        # Initial dim + 1 random points
        sol = []
        sol.append(self.create_new_solution(problem.factors["initial_solution"], problem))
        for i in range(1, n_pts):
            rand_x = problem.get_random_solution(self.rng_list[1])
            sol.append(self.create_new_solution(rand_x, problem))
        # print("initial sol", [i.x for i in sol])   # DELETE

        # Initialize larger than necessary (extra point for end of budget)
        n_calls = np.zeros(max_num_sol)
        A = np.empty((max_num_sol+1), dtype=object)
        fn_mean = np.empty(max_num_sol, dtype=object)
        fn_var = np.empty(max_num_sol, dtype=object)
        # Track overall budget spent
        budget_spent = 0
        r = self.factors["r"]  # FOR INCREASING REPLICATIONS

        # Start Solving
        # Evaluate solutions in initial structure
        fn_val = np.empty(n_pts, dtype=object)
        fn_var_val = np.empty(n_pts, dtype=object)
        for i in range(n_pts):
            problem.simulate(sol[i], self.factors["r"])
            budget_spent += self.factors["r"]
            fn_val[i] = tuple([-1*x for x in problem.minmax])*sol[i].objectives_mean
            fn_var_val[i] = sol[i].objectives_var
        # Record initial solution data
        n_calls[0] = 0
        A[0] = sol[0]
        fn_mean[0] = tuple([-1*x for x in problem.minmax])*fn_val[0]
        fn_var[0] = fn_var_val[0]
        # Sort solutions by obj function estimate
        sort_fn_val, sort_fn_var_val, sort_sol = self.sort_and_end_update(fn_val, fn_var_val, sol)
        # Record only when recommended solution changes
        record_idx = 1

        # Reflect worst and update sort_sol
        # Maximization problem is converted to minimization by -z
        loop = 0   # DELETE
        while budget_spent <= problem.factors["budget"]:
            loop += 1    # DELETE
            print("loop", loop)   # DELETE
            # print([i.x for i in sort_sol])   # DELETE
            # Reflect worse point
            p_high = sort_sol[-1]  # current worst point
            p_cent = tuple(np.mean(tuple([s.x for s in sort_sol[0:-1]]), axis=0))  # centroid for other pts
            print("centroid", p_cent)   # DELETE
            orig_pt = p_high  # save the original point
            p_refl = tuple(map(lambda i, j: i - j, tuple((1 + self.factors["alpha"])* x for x in p_cent), 
                                                   tuple(self.factors["alpha"]* x for x in p_high.x)))  # reflection
            p_refl_copy = p_refl
            p_refl = self.check_const(lower_bounds, upper_bounds, p_refl, orig_pt.x)
            # # Reflect next worst point if out of bounds
            # if p_refl != p_refl_copy:  # out of bounds
            #     next_idx = -2
            #     while (p_refl != p_refl_copy) and (-next_idx <= len(sort_sol)):
            #         print("next worst", next_idx)
            #         p_next = sort_sol[next_idx]  # next worst point
            #         p_cent = tuple(np.mean(tuple([s.x for s in list(np.append(sort_sol[0:-2], sort_sol[next_idx+1:]))]), axis=0))  # centroid for other pts
            #         print("centroid", p_cent)   # DELETE
            #         orig_pt = p_next  # save the original point
            #         p_refl = tuple(map(lambda i, j: i - j, tuple((1 + self.factors["alpha"])* x for x in p_cent), 
            #                                             tuple(self.factors["alpha"]* x for x in p_next.x)))  # reflection
            #         p_refl_copy = p_refl
            #         p_refl = self.check_const(lower_bounds, upper_bounds, p_refl, orig_pt.x)
            #         next_idx += 1

            # Reflect less
            if p_refl != p_refl_copy:  # out of bounds
                print("reflect less")  # DELETE
                while p_refl != p_refl_copy:

                    # Attempt contraction or shrinking
                    p_refl2 = p_high
                    p_refl = tuple(map(lambda i, j: i + j, tuple(self.factors["betap"]* x for x in p_high.x), 
                                                        tuple((1-self.factors["betap"])* x for x in p_cent)))
                    p_refl_copy = p_refl
                    p_refl = self.check_const(lower_bounds, upper_bounds, p_refl, p_refl2.x)
                    # print('bound: copy', p_refl_copy)  # DELETE
                    # print('bound: refl', p_refl)  # DELETE

            
            # Evaluate reflected point
            p_refl = Solution(p_refl, problem)
            p_refl.attach_rngs(rng_list=self.solution_progenitor_rngs, copy=True)
            problem.simulate(p_refl, self.factors["r"])   # STUCK HERE when solution is lb for chessmm (min)
            budget_spent += self.factors["r"]
            refl_fn_val = tuple([-1*x for x in problem.minmax])*p_refl.objectives_mean
            refl_fn_var_val = p_refl.objectives_var
            
            # Track best, worst, and second worst points
            p_low = sort_sol[0]  # current best pt
            fn_low = sort_fn_val[0]
            fn_sec = sort_fn_val[-2]  # current 2nd worst z
            fn_high = sort_fn_val[-1]  # worst z from unreflected structure

            # print("sort_fn_val", sort_fn_val)   # DELETE
            # print("best", fn_low)   # DELETE
            # print("-2", fn_sec)     # DELETE
            # print("refl", refl_fn_val)   # DELETE

            # Check if accept reflection
            if fn_low <= refl_fn_val and refl_fn_val <= fn_sec:
                print("accept reflection")   # DELETE
                sort_sol[-1] = p_refl  # the new point replaces the previous worst
                sort_fn_val[-1] = refl_fn_val
                sort_fn_var_val[-1] = refl_fn_var_val

                # Sort & end updating
                sort_fn_val, sort_fn_var_val, sort_sol = self.sort_and_end_update(sort_fn_val, sort_fn_var_val, sort_sol)

                # Best solution remains the same, so no reporting

            # Check if accept expansion (of reflection in the same direction)
            elif refl_fn_val < fn_low:
                print("accept expansion")   # DELETE
                p_exp2 = p_refl
                p_exp = tuple(map(lambda i, j: i + j, tuple(self.factors["gammap"]* x for x in p_refl.x), 
                                                      tuple((1-self.factors["gammap"])* x for x in p_cent)))
                p_exp = self.check_const(lower_bounds, upper_bounds, p_exp, p_exp2.x)

                # Evaluate expansion point
                p_exp= Solution(p_exp, problem)
                p_exp.attach_rngs(rng_list=self.solution_progenitor_rngs, copy=True)
                problem.simulate(p_exp, self.factors["r"])
                budget_spent += self.factors["r"]
                exp_fn_val = tuple([-1*x for x in problem.minmax])*p_exp.objectives_mean
                exp_fn_var_val = p_exp.objectives_var

                # Check if expansion point is an improvement relative to simplex
                if exp_fn_val < fn_low:
                    sort_sol[-1] = p_exp  # p_exp replaces p_high
                    sort_fn_val[-1] = exp_fn_val
                    sort_fn_var_val[-1] = exp_fn_var_val

                    # Sort & end updating
                    sort_fn_val, sort_fn_var_val, sort_sol = self.sort_and_end_update(sort_fn_val, sort_fn_var_val, sort_sol)

                    # Record data from expansion point (new best)
                    if budget_spent <= problem.factors["budget"]:
                        n_calls[record_idx] = budget_spent
                        A[record_idx] = p_exp
                        fn_mean[record_idx] = tuple([-1*x for x in problem.minmax])*exp_fn_val  # flip sign back
                        fn_var[record_idx] = exp_fn_var_val
                        record_idx += 1
                else:
                    sort_sol[-1] = p_refl  # p_refl replaces p_high
                    sort_fn_val[-1] = refl_fn_val
                    sort_fn_var_val[-1] = refl_fn_var_val

                    # Sort & end updating
                    sort_fn_val, sort_fn_var_val, sort_sol = self.sort_and_end_update(sort_fn_val, sort_fn_var_val, sort_sol)

                    # Record data from expansion point (new best)
                    if budget_spent <= problem.factors["budget"]:
                        n_calls[record_idx] = budget_spent
                        A[record_idx] = p_refl
                        fn_mean[record_idx] = tuple([-1*x for x in problem.minmax])*refl_fn_val  # flip sign back
                        fn_var[record_idx] = refl_fn_var_val
                        record_idx += 1
            
            # Check if accept contraction or shrink
            elif refl_fn_val > fn_sec:
                print("accept contraction")   # DELETE
                if refl_fn_val <= fn_high:
                    p_high = p_refl  # p_refl replaces p_high
                    fn_high = refl_fn_val  # replace fn_high
                
                # Attempt contraction or shrinking
                p_cont2 = p_high
                p_cont = tuple(map(lambda i, j: i + j, tuple(self.factors["betap"]* x for x in p_high.x), 
                                                       tuple((1-self.factors["betap"])* x for x in p_cent)))
                p_cont = self.check_const(lower_bounds, upper_bounds, p_cont, p_cont2.x)

                # Evaluate contraction point
                p_cont= Solution(p_cont, problem)
                p_cont.attach_rngs(rng_list=self.solution_progenitor_rngs, copy=True)
                problem.simulate(p_cont, r)  # FOR INCREASING REPLICATIONS
                budget_spent += r  # FOR INCREASING REPLICATIONS
                cont_fn_val = tuple([-1*x for x in problem.minmax])*p_cont.objectives_mean
                cont_fn_var_val = p_cont.objectives_var
                # Increase replications
                r += self.factors["r"]  # FOR INCREASING REPLICATIONS

                # Accept contraction
                if cont_fn_val <= fn_high:
                    sort_sol[-1] = p_cont  # p_cont replaces p_high
                    sort_fn_val[-1] = cont_fn_val
                    sort_fn_var_val[-1] = cont_fn_var_val

                    # Sort & end updating
                    sort_fn_val, sort_fn_var_val, sort_sol = self.sort_and_end_update(sort_fn_val, sort_fn_var_val, sort_sol)

                    # Check if contraction point is new best
                    if cont_fn_val < fn_low:
                        # Record data from contraction point (new best)
                        if budget_spent <= problem.factors["budget"]:
                            n_calls[record_idx] = budget_spent
                            A[record_idx] = p_cont
                            fn_mean[record_idx] = tuple([-1*x for x in problem.minmax])*cont_fn_val  # flip sign back
                            fn_var[record_idx] = cont_fn_var_val
                            record_idx += 1
                else:  # Contraction fails -> Simplex shrinks by delta with p_low fixed
                    sort_sol[-1] = p_high  # Replaced by p_refl

                    # Check for new best
                    new_best = 0

                    for i in range(1, len(sort_sol)):
                        p_new2 = p_low
                        p_new = tuple(map(lambda i, j: i + j, tuple(self.factors["delta"]* x for x in sort_sol[i].x), 
                                                       tuple((1-self.factors["delta"])* x for x in p_low.x)))
                        p_new = self.check_const(lower_bounds, upper_bounds, p_new, p_new2.x)
                        p_new= Solution(p_new, problem)
                        p_new.attach_rngs(rng_list=self.solution_progenitor_rngs, copy=True)
                        problem.simulate(p_new, r)  # FOR INCREASING REPLICATIONS
                        budget_spent += r  # FOR INCREASING REPLICATIONS
                        new_fn_val = tuple([-1*x for x in problem.minmax])*p_new.objectives_mean
                        new_fn_var_val = p_new.objectives_var

                        # Check for new best
                        if new_fn_val <= fn_low:
                            new_best = 1
                        
                        # Update sort_sol
                        sort_sol[i] = p_new  # p_new replaces pi
                        sort_fn_val[i] = new_fn_val
                        sort_fn_var_val[i] = new_fn_var_val
                    
                    # Sort & end updating
                    sort_fn_val, sort_fn_var_val, sort_sol = self.sort_and_end_update(sort_fn_val, sort_fn_var_val, sort_sol)

                    # Record data if there is a new best solution in the contraction
                    if new_best == 1 and budget_spent <= problem.factors["budget"]:
                        n_calls[record_idx] = budget_spent
                        A[record_idx] = sort_sol[0]
                        fn_mean[record_idx] = tuple([-1*x for x in problem.minmax])*sort_fn_val[0]  # flip sign back
                        fn_var[record_idx] = sort_fn_var_val[0]
                        record_idx += 1

        # Record solution at max budget
        n_calls[record_idx] = problem.factors["budget"]
        A[record_idx] = A[record_idx-1]
        fn_mean[record_idx] = fn_mean[record_idx-1]
        fn_var[record_idx] = fn_var[record_idx-1]
        
        # Trim empty rows from data
        n_calls = n_calls[:record_idx]
        A = A[:record_idx]
        fn_mean = fn_mean[:record_idx]
        fn_var = fn_var[:record_idx]

        recommended_solns = list(A)
        intermediate_budgets = list(n_calls)
        return recommended_solns, intermediate_budgets


    ### HELPER FUNCTIONS
    def sort_and_end_update(self, fn_val, fn_val_var, sol):
        fn_val_idx = np.argsort(fn_val)
        sort_fn_val = fn_val[fn_val_idx]
        sort_fn_var_val = fn_val_var[fn_val_idx]
        sort_sol = [s for _, s in sorted(zip(fn_val_idx, sol))]
        return sort_fn_val, sort_fn_var_val, sort_sol

    # Check & modify (if needed) the new point based on bounds
    def check_const(self, lb, ub, pt, pt2):
        col = len(pt2)
        step = tuple(map(lambda i, j: i - j, pt, pt2))
        tmax = np.ones(col)
        for i in range(col):
            if step[i] > 0 and ub != None:
                tmax[i] = (ub[i] - pt2[i]) / step[i]
            elif step[i] < 0 and lb != None:
                tmax[i] = (lb[i] - pt2[i]) / step[i]
        t = min(1, min(tmax))
        modified = list(map(lambda i, j: i + t*j, pt2, step))
        # Remove rounding error
        for i in range(col):
            if abs(modified[i]) < 0.00000005:
                modified[i] = 0
        print("modified", modified, "pt", pt)   # DELETE
        return tuple(modified)