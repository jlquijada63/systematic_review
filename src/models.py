from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceDataType(str, Enum):
    cohort = "cohort"
    case_control = "case_control"
    randomized_trial_participants = "randomized_trial_participants"
    registry_data = "registry_data"
    other = "other"


class OutcomeType(str, Enum):
    single_endpoint = "single_endpoint"
    combined_endpoint = "combined_endpoint"
    other = "other"


class ModelingMethod(str, Enum):
    linear = "linear"
    logistic = "logistic"
    cox = "cox"
    parametric_survival = "parametric_survival"
    competing_risks_regression = "competing_risks_regression"
    other = "other"


class EffectMeasureType(str, Enum):
    risk_ratio = "risk_ratio"
    odds_ratio = "odds_ratio"
    hazard_ratio = "hazard_ratio"
    mean_difference = "mean_difference"
    other = "other"


class MissingDataMethod(str, Enum):
    complete_case_analysis = "complete_case_analysis"
    imputation = "imputation"
    other = "other"


class CharmsBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class SourceOfDataSection(CharmsBaseModel):
    source_of_data_type: Optional[SourceDataType] = Field(
        default=None,
        description="Source of data (e.g., cohort, case-control, randomized trial participants, registry data).",
    )
    source_of_data_other_detail: Optional[str] = Field(default=None)


class ParticipantsSection(CharmsBaseModel):
    participant_eligibility_and_recruitment_method: Optional[str] = Field(default=None)
    participants_description: Optional[str] = Field(default=None)
    treatments_received_details: Optional[str] = Field(default=None)
    study_dates: Optional[str] = Field(default=None)


class OutcomesSection(CharmsBaseModel):
    outcome_definition_and_measurement: Optional[str] = Field(default=None)
    same_outcome_definition_for_all_participants: Optional[bool] = Field(default=None)
    outcome_type: Optional[OutcomeType] = Field(default=None)
    outcome_assessed_blinded_to_prognostic_factors: Optional[bool] = Field(default=None)
    candidate_prognostic_factors_part_of_outcome: Optional[bool] = Field(default=None)
    outcome_time_or_followup_duration: Optional[str] = Field(default=None)


class PrognosticFactorsSection(CharmsBaseModel):
    number_of_prognostic_factors: Optional[int] = Field(default=None, ge=0)
    type_of_prognostic_factors: Optional[list[str]] = Field(default=None)
    prognostic_factor_definition_and_measurement: Optional[str] = Field(default=None)
    timing_of_prognostic_factor_measurement: Optional[str] = Field(default=None)
    prognostic_factors_assessed_blinded: Optional[bool] = Field(default=None)
    prognostic_factors_handling_in_modeling: Optional[str] = Field(default=None)


class SampleSizeSection(CharmsBaseModel):
    sample_size_calculation_conducted: Optional[bool] = Field(default=None)
    sample_size_calculation_method: Optional[str] = Field(default=None)
    number_of_participants: Optional[int] = Field(default=None, ge=0)
    number_of_outcomes_or_events: Optional[int] = Field(default=None, ge=0)
    events_per_variable: Optional[float] = Field(default=None, ge=0)


class PrognosticFactorMissingCount(CharmsBaseModel):
    prognostic_factor_name: str = Field(..., min_length=1)
    missing_count: int = Field(..., ge=0)


class MissingDataSection(CharmsBaseModel):
    participants_with_any_missing_values: Optional[int] = Field(default=None, ge=0)
    participants_missing_by_prognostic_factor: Optional[list[PrognosticFactorMissingCount]] = Field(
        default=None
    )
    attrition_and_censoring_details: Optional[str] = Field(default=None)
    missing_data_handling_method: Optional[MissingDataMethod] = Field(default=None)
    missing_data_handling_other_detail: Optional[str] = Field(default=None)


class AnalysisSection(CharmsBaseModel):
    modeling_method: Optional[ModelingMethod] = Field(default=None)
    modeling_method_other_detail: Optional[str] = Field(default=None)
    modeling_assumptions_check_method: Optional[str] = Field(default=None)
    non_proportional_hazards_assessment_method: Optional[str] = Field(default=None)
    prognostic_factor_selection_for_multivariable_modeling: Optional[str] = Field(default=None)
    selection_or_exclusion_during_multivariable_modeling: Optional[str] = Field(default=None)
    selection_or_exclusion_criteria: Optional[str] = Field(default=None)
    continuous_factor_handling_method: Optional[str] = Field(default=None)
    cut_points_and_justification: Optional[str] = Field(default=None)
    non_linear_relationship_identification_method: Optional[str] = Field(default=None)


class ResultsSection(CharmsBaseModel):
    effect_measure_types_reported: Optional[list[EffectMeasureType]] = Field(default=None)
    unadjusted_and_adjusted_effect_estimates: Optional[str] = Field(default=None)
    effect_estimate_precision_ci_or_se: Optional[str] = Field(default=None)
    non_linear_relationship_results: Optional[str] = Field(default=None)
    non_proportional_hazards_evidence: Optional[str] = Field(default=None)
    adjustment_factors_for_each_adjusted_estimate: Optional[str] = Field(default=None)


class InterpretationDiscussionSection(CharmsBaseModel):
    interpretation_of_presented_results: Optional[str] = Field(default=None)
    comparison_generalizability_strengths_limitations: Optional[str] = Field(default=None)


class ExtractionMetadataSection(CharmsBaseModel):
    notes: Optional[str] = Field(default=None)
    source_quote_or_location: Optional[str] = Field(
        default=None,
        description="Source reference (page, section, or quote location in the PDF).",
    )


class CharmsPfRecord(CharmsBaseModel):
    source_of_data: SourceOfDataSection = Field(default_factory=SourceOfDataSection)
    participants: ParticipantsSection = Field(default_factory=ParticipantsSection)
    outcomes: OutcomesSection = Field(default_factory=OutcomesSection)
    prognostic_factors: PrognosticFactorsSection = Field(default_factory=PrognosticFactorsSection)
    sample_size: SampleSizeSection = Field(default_factory=SampleSizeSection)
    missing_data: MissingDataSection = Field(default_factory=MissingDataSection)
    analysis: AnalysisSection = Field(default_factory=AnalysisSection)
    results: ResultsSection = Field(default_factory=ResultsSection)
    interpretation_and_discussion: InterpretationDiscussionSection = Field(
        default_factory=InterpretationDiscussionSection
    )
    extraction_metadata: ExtractionMetadataSection = Field(default_factory=ExtractionMetadataSection)
