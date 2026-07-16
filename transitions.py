from typing import List, Dict
from pprint import pprint

def direct_transition(name, type, destination_state) -> Dict:
    return {
        name:{
            "type": type,
            "direct_transition" : destination_state
        }
    }

def distributed_transition(name, type, distribution:List[float], distributed_states:List) -> Dict:

    # distribution should sum up to 1.0, if they dont, add to last defined ,
    # if distribution is over 1.0, stop at the last aggregation
    # just assert, let the user figure it out :)

    assert sum(distribution) == 1, "Distribution must sum up to 1.0"
    assert len(distribution) == len(distributed_states), "Length of Distributions and Distribution states must match"

    return {
        name: {
            "type": type,
            "distribution_transition" : [{"distribution": prob, "transition": state} for prob, state in zip(distribution, distributed_states)]

        }

    }


condition_types = ["gender", "prior state"]

def conditional_transition(name, type, condition_type, conditions:List,  transition_to:List) -> Dict:
    """
    transition_to: states we're going to
    condition: the transition condition
    """

    # condition type must exist
    assert condition_type.lower() in condition_types, "Condition type specified doesnt exist"

    # condition type must be the same length as conditions
    assert len(conditions) == len(transition_to), "Conditions and Transitions sizes must match"

    conditional_transition = []

                
    for condition, transition in zip(conditions, transition_to):
        conditional_transition.append(
            {
                "condition" : {
                    "condition_type" : condition_type,
                    "condition": condition
                },
                "transition":transition
            }
        )

    return {
        name: {
            "type" : type,
            "conditional_transition": conditional_transition            
        }
    }


def main():
    name = "init"
    type = "init"
    condition_type = "gender"
    conditions = ["is_male", "is_female"]
    transition_to = ["Male", "Female"]

    distribution = [0.2, 0.4, 0.8]
    distributed_states = ["med 1", "med 2", "med 3"]

    # direct transitions
    direct_trans = direct_transition(name, type, destination_state="terminal")
    print("--- Direct Transition ---")
    pprint(direct_trans)
    print()

    # conditional transitions
    cond_trans = conditional_transition(name, type, condition_type, conditions, transition_to)
    print("--- Conditional Transition ---")
    pprint(cond_trans)
    print()

    # distributed transitions
    dist_trans = distributed_transition(name, type, distribution, distributed_states)
    print("--- Distributed Transition ---")
    pprint(dist_trans)
    print()


if __name__ == "__main__":
    main()
