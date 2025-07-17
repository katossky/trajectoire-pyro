"""Configuration validator for synthetic career generator."""

import yaml
from typing import Dict, Any, List
import torch


class ConfigValidator:
    """Validates configuration parameters for the career generator."""
    
    @staticmethod
    def validate_transition_params(params: Dict[str, Any]) -> None:
        """Validate transition probability parameters."""
        states = ['inactive', 'employed', 'retired', 'deceased']
        
        # Validate transition matrix
        if 'transitions' not in params:
            raise ValueError("Missing 'transitions' in parameters")
        
        transitions = params['transitions']
        for state in states:
            if state not in transitions:
                raise ValueError(f"Missing state '{state}' in transitions")
            
            # Check that transitions are probabilities between 0 and 1
            for target_state, prob in transitions[state].items():
                if not isinstance(prob, (int, float)) or prob < 0 or prob > 1:
                    raise ValueError(f"Invalid probability for {state}->{target_state}: {prob}")
        
        # Validate retirement age
        if 'retirement_age' not in params:
            raise ValueError("Missing 'retirement_age' in parameters")
        if not isinstance(params['retirement_age'], int) or params['retirement_age'] < 0:
            raise ValueError("Invalid retirement age")

    @staticmethod
    def validate_income_params(params: Dict[str, Any]) -> None:
        """Validate income distribution parameters."""
        if 'income_dist' not in params:
            raise ValueError("Missing 'income_dist' in parameters")
        
        income = params['income_dist']
        if 'log_mu' not in income or 'log_sigma' not in income:
            raise ValueError("Missing income distribution parameters 'log_mu' or 'log_sigma'")
        
        if not isinstance(income['log_mu'], (int, float)):
            raise ValueError("Invalid log_mu parameter")
        if not isinstance(income['log_sigma'], (int, float)) or income['log_sigma'] <= 0:
            raise ValueError("Invalid log_sigma parameter")

    @staticmethod
    def validate_mortality_params(params: Dict[str, Any]) -> None:
        """Validate mortality curve parameters."""
        if 'mortality' not in params:
            raise ValueError("Missing 'mortality' parameters")
        
        mort = params['mortality']
        required_keys = ['baseline_mortality', 'age_factor', 'max_age']
        for key in required_keys:
            if key not in mort:
                raise ValueError(f"Missing mortality parameter '{key}'")
        
        if not isinstance(mort['baseline_mortality'], (int, float)) or \
           mort['baseline_mortality'] < 0 or mort['baseline_mortality'] > 1:
            raise ValueError("Invalid mortality baseline")
        
        if not isinstance(mort['age_factor'], (int, float)) or mort['age_factor'] <= 0:
            raise ValueError("Invalid age factor")
        
        if not isinstance(mort['max_age'], int) or mort['max_age'] <= 0:
            raise ValueError("Invalid max age")

    @staticmethod
    def load_and_validate(config_path: str) -> Dict[str, Any]:
        """Load and validate configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                params = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        
        ConfigValidator.validate_transition_params(params)
        ConfigValidator.validate_income_params(params)
        ConfigValidator.validate_mortality_params(params)
        
        return params

    @staticmethod
    def get_transition_matrix(params: Dict[str, Any]) -> torch.Tensor:
        """Convert transition parameters to Pyro transition matrix."""
        states = ['inactive', 'employed', 'retired', 'deceased']
        num_states = len(states)
        matrix = torch.zeros((num_states, num_states))
        
        for i, from_state in enumerate(states):
            row_sum = 0.0
            for j, to_state in enumerate(states):
                prob = params['transitions'][from_state].get(to_state, 0.0)
                matrix[i, j] = prob
                row_sum += prob
            
            # Normalize to ensure valid probabilities
            if row_sum > 0:
                matrix[i] = matrix[i] / row_sum
        
        return matrix