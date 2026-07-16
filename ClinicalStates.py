from dataclasses import dataclass
from typing import Optional
from pprint import pprint

from transitions import direct_transition, distributed_transition, conditional_transition


@dataclass
class Code:
    system: str
    code: str
    display: str

    def to_dict(self):
        return {"system": self.system, "code": self.code, "display": self.display}


def _as_code(c):
    return c if isinstance(c, Code) else Code(**c)


def _normalize_codes(codes):
    return [_as_code(c) for c in codes] if codes else codes


class _ClinicalState:
    """
    Shared plumbing for the 5 clinical state types. Not a dataclass itself -
    the actual field lists live on each subclass since they differ (Encounter
    needs encounter_class, Procedure needs duration, etc).

    The transition methods below just call straight into transitions.py and
    stash the result. Since those functions already return the full
    {name: {"type": ..., "...transition": ...}} dict, to_dict() on each
    subclass just needs to pull that dict out and add its own clinical
    fields on top before handing it back.
    """

    state_type = None

    def direct_to(self, destination_state):
        self.transition = direct_transition(self.name, self.state_type, destination_state)
        return self

    def distributed_to(self, distribution, states):
        self.transition = distributed_transition(self.name, self.state_type, distribution, states)
        return self

    def conditional_on(self, condition_type, conditions, transition_to):
        self.transition = conditional_transition(self.name, self.state_type, condition_type, conditions, transition_to)
        return self

    def _start_dict(self):
        if getattr(self, "transition", None) is None:
            raise ValueError(
                f"{self.name}: no transition set yet - call direct_to(), "
                f"distributed_to(), or conditional_on() before to_dict()"
            )
        return dict(self.transition[self.name])


@dataclass
class ConditionOnset(_ClinicalState):
    state_type = "ConditionOnset"

    name: str
    codes: list[Code]
    target_encounter: Optional[str] = None
    assign_to_attribute: Optional[str] = None
    remarks: Optional[list[str]] = None
    transition: Optional[dict] = None

    def __post_init__(self):
        self.codes = _normalize_codes(self.codes)

    def to_dict(self):
        d = self._start_dict()
        d["codes"] = [c.to_dict() for c in self.codes]
        if self.target_encounter:
            d["target_encounter"] = self.target_encounter
        if self.assign_to_attribute:
            d["assign_to_attribute"] = self.assign_to_attribute
        if self.remarks:
            d["remarks"] = self.remarks
        return {self.name: d}

    def check(self):
        errors = []
        if not self.codes:
            errors.append(f"{self.name}: needs at least one code")
        if not self.target_encounter:
            # not a hard error - Synthea just won't record the condition
            # until some later Encounter names this state as its target
            errors.append(f"{self.name}: no target_encounter set, condition won't get recorded until some Encounter claims it")
        return errors


@dataclass
class ConditionEnd(_ClinicalState):
    state_type = "ConditionEnd"

    name: str
    condition_onset: Optional[str] = None
    codes: Optional[list[Code]] = None
    referenced_by_attribute: Optional[str] = None
    remarks: Optional[list[str]] = None
    transition: Optional[dict] = None

    def __post_init__(self):
        self.codes = _normalize_codes(self.codes)

    def to_dict(self):
        d = self._start_dict()
        if self.condition_onset:
            d["condition_onset"] = self.condition_onset
        if self.codes:
            d["codes"] = [c.to_dict() for c in self.codes]
        if self.referenced_by_attribute:
            d["referenced_by_attribute"] = self.referenced_by_attribute
        if self.remarks:
            d["remarks"] = self.remarks
        return {self.name: d}

    def check(self):
        if not (self.condition_onset or self.codes or self.referenced_by_attribute):
            return [f"{self.name}: needs condition_onset, codes, or referenced_by_attribute to know what it's ending"]
        return []


VALID_ENCOUNTER_CLASSES = {"ambulatory", "emergency", "inpatient", "wellness", "urgentcare", "outpatient", "virtual"}


@dataclass
class Encounter(_ClinicalState):
    state_type = "Encounter"

    name: str
    encounter_class: str = "ambulatory"
    codes: Optional[list[Code]] = None
    reason: Optional[str] = None
    wellness: bool = False
    remarks: Optional[list[str]] = None
    transition: Optional[dict] = None

    def __post_init__(self):
        self.codes = _normalize_codes(self.codes)

    def to_dict(self):
        d = self._start_dict()
        d["encounter_class"] = self.encounter_class
        if self.wellness:
            d["wellness"] = True
        if self.codes:
            d["codes"] = [c.to_dict() for c in self.codes]
        if self.reason:
            d["reason"] = self.reason
        if self.remarks:
            d["remarks"] = self.remarks
        return {self.name: d}

    def check(self):
        errors = []
        if self.encounter_class not in VALID_ENCOUNTER_CLASSES:
            errors.append(f"{self.name}: unrecognized encounter_class '{self.encounter_class}'")
        if not self.wellness and not self.codes:
            errors.append(f"{self.name}: non-wellness encounter should have codes")
        return errors


@dataclass
class EncounterEnd(_ClinicalState):
    state_type = "EncounterEnd"

    name: str
    discharge_disposition: Optional[Code] = None
    remarks: Optional[list[str]] = None
    transition: Optional[dict] = None

    def __post_init__(self):
        if self.discharge_disposition is not None:
            self.discharge_disposition = _as_code(self.discharge_disposition)

    def to_dict(self):
        d = self._start_dict()
        if self.discharge_disposition:
            d["discharge_disposition"] = self.discharge_disposition.to_dict()
        if self.remarks:
            d["remarks"] = self.remarks
        return {self.name: d}

    def check(self):
        return []


@dataclass
class Procedure(_ClinicalState):
    state_type = "Procedure"

    name: str
    codes: list[Code]
    reason: Optional[str] = None
    duration_low: Optional[float] = None
    duration_high: Optional[float] = None
    duration_unit: str = "minutes"
    remarks: Optional[list[str]] = None
    transition: Optional[dict] = None

    def __post_init__(self):
        self.codes = _normalize_codes(self.codes)

    def to_dict(self):
        d = self._start_dict()
        d["codes"] = [c.to_dict() for c in self.codes]
        if self.reason:
            d["reason"] = self.reason
        if self.duration_low is not None and self.duration_high is not None:
            d["duration"] = {"low": self.duration_low, "high": self.duration_high, "unit": self.duration_unit}
        if self.remarks:
            d["remarks"] = self.remarks
        return {self.name: d}

    def check(self):
        if not self.codes:
            return [f"{self.name}: needs at least one code"]
        return []


def check_all(*states):
    errors = []
    for s in states:
        errors += s.check()
    return errors


def main():
    onset = ConditionOnset(
        name="Typhoid_Onset",
        codes=[Code("SNOMED-CT", "4834000", "Typhoid fever")],
        target_encounter="Clinic_Visit",
        assign_to_attribute="typhoid",
    ).direct_to("Clinic_Visit")

    visit = Encounter(
        name="Clinic_Visit",
        encounter_class="ambulatory",
        codes=[Code("SNOMED-CT", "185347001", "Encounter for symptom")],
        reason="typhoid",
    ).direct_to("Blood_Culture")

    culture = Procedure(
        name="Blood_Culture",
        codes=[Code("SNOMED-CT", "104177005", "Blood culture")],
        reason="typhoid",
        duration_low=10,
        duration_high=15,
    ).direct_to("End_Visit")

    end_visit = EncounterEnd(name="End_Visit").direct_to("Outcome")

    # Recovered/Relapsed would be Terminal states from control_states.py -
    # just placeholders here since that file isn't wired in yet
    outcome = ConditionEnd(
        name="Outcome",
        condition_onset="Typhoid_Onset",
    ).distributed_to([0.7, 0.3], ["Recovered", "Relapsed"])

    states = [onset, visit, culture, end_visit, outcome]

    print("--- Validation ---")
    problems = check_all(*states)
    if problems:
        for p in problems:
            print(" -", p)
    else:
        print("clean, no issues")
    print()

    print("--- State Dicts ---")
    for s in states:
        pprint(s.to_dict())
        print()

    # quick sanity check that conditional_on() also works through this class
    print("--- Conditional transition sanity check (not part of the chain above) ---")
    scratch = Encounter(name="Scratch", codes=[Code("SNOMED-CT", "1", "x")])
    scratch.conditional_on("gender", ["is_male", "is_female"], ["Male_Path", "Female_Path"])
    pprint(scratch.to_dict())


if __name__ == "__main__":
    main()
