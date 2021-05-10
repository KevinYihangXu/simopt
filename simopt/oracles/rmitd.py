"""
Summary
-------
Simulate a multi-stage revenue management system with inter-temporal dependence
"""
import numpy as np

from base import Oracle


class RMITD(Oracle):
    """
    An oracle that simulates a multi-stage revenue management system with
    inter-temporal dependence.
    Returns the total revenue.

    Attributes
    ----------
    name : string
        name of oracle
    n_rngs : int
        number of random-number generators used to run a simulation replication
    n_responses : int
        number of responses (performance measures)
    factors : dict
        changeable factors of the simulation model
    specifications : dict
        details of each factor (for GUI and data validation)
    check_factor_list : dict
        switch case for checking factor simulatability

    Arguments
    ---------
    fixed_factors : nested dict
        fixed factors of the simulation model

    See also
    --------
    base.Oracle
    """
    def __init__(self, fixed_factors={}):
        self.name = "RMITD"
        self.n_rngs = 2
        self.n_responses = 1
        self.specifications = {
            "time_horizon": {
                "description": "Time horizon.",
                "datatype": int,
                "default": 3
            },
            "prices": {
                "description": "Prices for each period.",
                "datatype": list,
                "default": [100, 300, 400]
            },
            "demand_means": {
                "description": "Mean demand for each period.",
                "datatype": list,
                "default": [50, 20, 30]
            },
            "cost": {
                "description": "Cost per unit of capacity at t = 0.",
                "datatype": float,
                "default": 80.0
            },
            "gamma_shape": {
                "description": "Shape parameter of gamma distribution.",
                "datatype": float,
                "default": 1.0
            },
            "gamma_scale": {
                "description": "Scale parameter of gamma distribution.",
                "datatype": float,
                "default": 1.0
            },
            "initial_inventory": {
                "description": "Initial inventory.",
                "datatype": int,
                "default": 100
            },
            "reservation_qtys": {
                "description": "Inventory to reserve going into periods 2, 3, ..., T.",
                "datatype": list,
                "default": [50, 30]
            }
        }
        self.check_factor_list = {
            "time_horizon": self.check_time_horizon,
            "prices": self.check_prices,
            "demand_means": self.check_demand_means,
            "cost": self.check_cost,
            "gamma_shape": self.check_gamma_shape,
            "gamma_scale": self.check_gamma_scale,
            "initial_inventory": self.check_initial_inventory,
            "reservation_qtys": self.check_reservation_qtys
        }
        # Set factors of the simulation oracle.
        super().__init__(fixed_factors)

    def check_time_horizon(self):
        return self.factors["time_horizon"] > 0

    def check_prices(self):
        return all(price > 0 for price in self.factors["prices"])

    def check_demand_means(self):
        return all(demand_mean > 0 for demand_mean in self.factors["demand_means"])

    def check_cost(self):
        return self.factors["cost"] > 0

    def check_gamma_shape(self):
        return self.factors["gamma_shape"] > 0

    def check_gamma_scale(self):
        return self.factors["gamma_scale"] > 0

    def check_initial_inventory(self):
        return self.factors["initial_inventory"] > 0

    def check_reservation_qtys(self):
        return all(reservation_qty > 0 for reservation_qty in self.factors["reservation_qtys"])

    def check_simulatable_factors(self):
        # Check for matching number of periods.
        if len(self.factors["prices"]) != self.factors["time_horizon"]:
            return False
        elif len(self.factors["demand_means"]) != self.factors["time_horizon"]:
            return False
        elif len(self.factors["reservation_qtys"]) != self.factors["time_horizon"] - 1:
            return False
        # Check that first reservation level is less than initial inventory.
        elif self.factors["initial_inventory"] < self.factors["reservation_qtys"][0]:
            return False
        # Check for non-increasing reservation levels.
        elif any(self.factors["reservation_qtys"][idx] < self.factors["reservation_qtys"][idx + 1] for idx in range(self.factors["time_horizon"] - 2)):
            return False
        # Check that gamma_shape*gamma_scale = 1.
        elif np.isclose(self.factors["gamma_shape"] * self.factors["gamma_scale"], 1) is False:
            return False
        else:
            return True

    def replicate(self, rng_list):
        """
        Simulate a single replication for the current oracle factors.

        Arguments
        ---------
        rng_list : list of rng.MRG32k3a objects
            rngs for oracle to use when simulating a replication

        Returns
        -------
        responses : dict
            performance measures of interest
            "revenue" = total revenue
        gradients : dict of dicts
            gradient estimates for each response
        """
        # Designate separate random number generators.
        # Outputs will be coupled when generating demand.
        X_rng = rng_list[0]
        Y_rng = rng_list[1]
        # Generate X and Y (to use for computing demand).
        # random.gammavariate takes two inputs: alpha and beta.
        #     alpha = k = gamma_shape
        #     beta = 1/theta = 1/gamma_scale
        X = X_rng.gammavariate(alpha=self.factors["gamma_shape"], beta=1./self.factors["gamma_scale"])
        Y = [Y_rng.expovariate(1) for _ in range(self.factors["time_horizon"])]
        # Track inventory over time horizon.
        remaining_inventory = self.factors["initial_inventory"]
        # Append "no reservations" for decision-making in final period.
        reservations = self.factors["reservation_qtys"]
        reservations.append(0)
        # Simulate over the time horizon and calculate the realized revenue.
        revenue = 0
        for period in range(self.factors["time_horizon"]):
            demand = self.factors["demand_means"][period]*X*Y[period]
            sell = min(max(remaining_inventory-reservations[period], 0), demand)
            remaining_inventory = remaining_inventory - sell
            revenue += sell*self.factors["prices"][period]
        revenue -= self.factors["cost"]*self.factors["initial_inventory"]
        # Compose responses and gradients.
        responses = {"revenue": revenue}
        gradients = {response_key: {factor_key: np.nan for factor_key in self.specifications} for response_key in responses}
        return responses, gradients