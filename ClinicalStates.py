import json
from typing import List, Dict, Any, Optional


from transitions import direct_transition, distributed_transition, conditional_transition

class ClinicalState:
    # Base class for all clinical states to handle merging withs transitions.
    def __init__(self, name: str, state_type: str):
        self.name = name
        self.type = state_type
        self.transition_data = {}

    def apply_transition(self, transition_output: Dict):
        """
        Daniel's transition dictionary.
        Expected format from Daniel: { "StateName": {"type": "...", "transition_logic": "..."} }
        """
        if self.name in transition_output:
            self.transition_data = transition_output[self.name]
        else:
            raise ValueError(f"State name '{self.name}' not found in transition data.")

    def build(self) -> Dict:
        state_body = self.transition_data.copy() if self.transition_data else {}
        # Ensure the type is correctly set based on the clinical state class
        state_body["type"] = self.type
        return {self.name: state_body}


class ConditionOnset(ClinicalState):
    def __init__(self, name: str, codes: List[Dict[str, str]], target_encounter: Optional[str] = None):
        super().__init__(name, "ConditionOnset")
        self.codes = codes
        self.target_encounter = target_encounter

    def build(self) -> Dict:
        data = super().build()
        data[self.name]["codes"] = self.codes
        if self.target_encounter:
            data[self.name]["target_encounter"] = self.target_encounter
        return data


class ConditionEnd(ClinicalState):
    def __init__(self, name: str, condition_onset: str):
        super().__init__(name, "ConditionEnd")
        self.condition_onset = condition_onset

    def build(self) -> Dict:
        data = super().build()
        data[self.name]["condition_onset"] = self.condition_onset
        return data


class Encounter(ClinicalState):
    def __init__(self, name: str, encounter_class: str, codes: List[Dict[str, str]], wellness: bool = False):
        super().__init__(name, "Encounter")
        self.encounter_class = encounter_class
        self.codes = codes
        self.wellness = wellness

    def build(self) -> Dict:
        data = super().build()
        data[self.name]["encounter_class"] = self.encounter_class
        data[self.name]["codes"] = self.codes
        data[self.name]["wellness"] = self.wellness
        return data


class EncounterEnd(ClinicalState):
    def __init__(self, name: str):
        super().__init__(name, "EncounterEnd")

    def build(self) -> Dict:
        return super().build()


class Procedure(ClinicalState):
    def __init__(self, name: str, codes: List[Dict[str, str]], duration: Optional[Dict[str, Any]] = None):
        super().__init__(name, "Procedure")
        self.codes = codes
        # Duration format expected: {"low": 15, "high": 30, "unit": "minutes"}
        self.duration = duration

    def build(self) -> Dict:
        data = super().build()
        data[self.name]["codes"] = self.codes
        if self.duration:
            data[self.name]["duration"] = self.duration
        return data


# LOCAL TESTING BLOCK
if __name__ == "__main__":
    print("Building Clinical Module for Nigeria Context...\n")

    # 1. ConditionOnset with a Direct Transition
    malaria_codes = [{"system": "SNOMED-CT", "code": "61462000", "display": "Malaria"}]
    onset = ConditionOnset("Get_Malaria", codes=malaria_codes)
    
    
    onset_trans = direct_transition("Get_Malaria", "ConditionOnset", "Malaria_Encounter")
    onset.apply_transition(onset_trans)

    # 2. Encounter with a Distributed Transition (e.g., 80% Treated, 20% Referred)
    encounter_codes = [{"system": "SNOMED-CT", "code": "185349003", "display": "Encounter for symptom"}]
    encounter = Encounter("Malaria_Encounter", encounter_class="ambulatory", codes=encounter_codes)
    

    enc_trans = distributed_transition(
        "Malaria_Encounter", 
        "Encounter", 
        distribution=[0.8, 0.2], 
        distributed_states=["Treated_Procedure", "Terminal"]
    )
    encounter.apply_transition(enc_trans)

    # 3. Combine and print the states as they would appear in the Synthea module
    module_states = {}
    module_states.update(onset.build())
    module_states.update(encounter.build())

    print(json.dumps({"states": module_states}, indent=4))
