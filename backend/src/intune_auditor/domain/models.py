"""Pydantic v2 domain models used across parsing, evaluation, APIs, and reports."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)
from pydantic import (
    JsonValue as PydanticJsonValue,
)

from intune_auditor.domain.enums import (
    AlignmentStatus,
    ApplicabilityState,
    AssignmentTargetType,
    AuditMode,
    ComparisonMode,
    ConflictConfidence,
    DecisionStatus,
    DiagnosticSeverity,
    EvidenceConfidence,
    EvidenceType,
    FilterMode,
    FindingSeverity,
    FindingType,
    KnowledgePackStatus,
    Platform,
    PolicyKind,
    RuntimeState,
    Scope,
    ValueType,
)
from intune_auditor.version import AUDIT_SCHEMA_VERSION

JsonValue = PydanticJsonValue
__all__ = ["JsonValue"]


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, use_enum_values=False)


class UploadedSource(DomainModel):
    source_id: str
    filename: str
    content_type: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    archive_member: str | None = None


class ConfiguredValue(DomainModel):
    value_type: ValueType
    raw: JsonValue = None
    canonical: JsonValue = None
    display: str
    semantic_known: bool = False


class AssignmentFilter(DomainModel):
    filter_id: str | None = None
    display_name: str | None = None
    mode: FilterMode
    rule: str | None = None
    platform: Platform = Platform.UNKNOWN
    definition_available: bool = False


class AssignmentTarget(DomainModel):
    target_type: AssignmentTargetType
    target_id: str | None = None
    display_name: str | None = None
    scope: Scope = Scope.UNKNOWN
    filter: AssignmentFilter | None = None


class ParserDiagnostic(DomainModel):
    source_file: str
    policy: str | None = None
    json_path: str
    code: str
    severity: DiagnosticSeverity
    reason: str
    suggested_action: str


class SettingObservation(DomainModel):
    observation_id: str
    original_setting_id: str
    normalized_setting_id: str
    canonical_setting_id: str
    definition_id: str | None = None
    choice_id: str | None = None
    value_definition_id: str | None = None
    original_value: JsonValue = None
    canonical_value: JsonValue = None
    display_value: str
    technical_json_path: str
    source_policy_id: str
    source_policy_name: str
    source_file: str
    platform: Platform
    scope: Scope
    extraction_confidence: EvidenceConfidence
    parser_name: str
    parser_version: str
    diagnostics: list[ParserDiagnostic] = Field(default_factory=list)


class PolicyDocument(DomainModel):
    policy_id: str
    name: str
    description: str | None = None
    platform: Platform
    kind: PolicyKind
    scope: Scope
    source: UploadedSource
    settings: list[SettingObservation] = Field(default_factory=list)
    assignments: list[AssignmentTarget] = Field(default_factory=list)
    diagnostics: list[ParserDiagnostic] = Field(default_factory=list)
    is_synthetic: bool = False


class ParserResult(DomainModel):
    policies: list[PolicyDocument]
    diagnostics: list[ParserDiagnostic] = Field(default_factory=list)
    input_sha256: str
    parser_version: str


class AuditPreviewPolicy(DomainModel):
    policy_id: str
    name: str
    platform: Platform
    kind: PolicyKind
    setting_count: int = Field(ge=0)


class AuditPreview(DomainModel):
    policy_count: int = Field(ge=0)
    setting_count: int = Field(ge=0)
    policies: list[AuditPreviewPolicy]
    diagnostics: list[ParserDiagnostic]
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    parser_version: str


class EvidenceSource(DomainModel):
    evidence_type: EvidenceType
    title: str
    source_reference: HttpUrl | str
    source_domain: str
    published_at: date | None = None
    verified_at: date
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    confidence: EvidenceConfidence
    is_official: bool

    @field_validator("source_reference")
    @classmethod
    def safe_source_reference(cls, value: HttpUrl | str) -> HttpUrl | str:
        reference = str(value).lower()
        if not (reference.startswith("https://") or reference.startswith("urn:")):
            raise ValueError("source_reference must use https or urn")
        return value


class KnowledgeProvenance(DomainModel):
    input_files: list[str] = Field(default_factory=list)
    input_sha256: list[str] = Field(default_factory=list)
    importer_version: str | None = None
    notes: list[str] = Field(default_factory=list)


class KnowledgePackManifest(DomainModel):
    schema_version: str
    pack_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]+$")
    vendor: str = Field(min_length=1)
    product: str = Field(min_length=1)
    baseline_name: str = Field(min_length=1)
    baseline_version: str = Field(min_length=1)
    platform: Platform
    source_type: EvidenceType
    source_title: str = Field(min_length=1)
    source_domain: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    published_at: date | None = None
    verified_at: date
    imported_at: datetime
    data_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    application_version: str
    status: KnowledgePackStatus
    setting_count: int = Field(ge=0)
    exact_value_count: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list)
    settings_file: str = Field(pattern=r"^[^/\\]+\.json$")
    provenance: KnowledgeProvenance = Field(default_factory=KnowledgeProvenance)

    @field_validator("source_reference")
    @classmethod
    def safe_source_reference(cls, value: str) -> str:
        lowered = value.lower()
        if not (lowered.startswith("https://") or lowered.startswith("urn:")):
            raise ValueError("source_reference must use https or urn")
        return value


class ValueDefinition(DomainModel):
    value_type: ValueType
    allowed_values: list[JsonValue] = Field(default_factory=list)
    value_labels: dict[str, dict[str, str]] = Field(default_factory=dict)
    semantic_mapping: dict[str, JsonValue] = Field(default_factory=dict)


class ComparisonRule(DomainModel):
    mode: ComparisonMode
    ordered_values: list[JsonValue] = Field(default_factory=list)
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    custom_rule_id: str | None = None

    @model_validator(mode="after")
    def validate_mode_parameters(self) -> ComparisonRule:
        if self.mode is ComparisonMode.ORDERED and not self.ordered_values:
            raise ValueError("ordered comparison requires ordered_values")
        if self.mode is ComparisonMode.NUMERIC_MINIMUM and self.minimum is None:
            raise ValueError("numeric_minimum requires minimum")
        if self.mode is ComparisonMode.NUMERIC_MAXIMUM and self.maximum is None:
            raise ValueError("numeric_maximum requires maximum")
        if self.minimum is not None and not self.minimum.is_finite():
            raise ValueError("comparison minimum must be finite")
        if self.maximum is not None and not self.maximum.is_finite():
            raise ValueError("comparison maximum must be finite")
        if self.mode is ComparisonMode.NUMERIC_RANGE:
            if self.minimum is None or self.maximum is None:
                raise ValueError("numeric_range requires minimum and maximum")
            if self.minimum > self.maximum:
                raise ValueError("numeric_range minimum must not exceed maximum")
        if self.mode is ComparisonMode.CUSTOM and not self.custom_rule_id:
            raise ValueError("custom comparison requires custom_rule_id")
        return self


class ApplicabilityRule(DomainModel):
    platforms: list[Platform]
    scopes: list[Scope]
    minimum_os: str | None = None
    maximum_os: str | None = None
    editions: list[str] = Field(default_factory=list)
    architectures: list[str] = Field(default_factory=list)
    enrollment_types: list[str] = Field(default_factory=list)
    supervised_required: bool | None = None
    physical_device_required: bool | None = None
    vdi_supported: bool | None = None
    shared_device_supported: bool | None = None
    licensing_requirements: list[str] = Field(default_factory=list)
    deprecated: bool = False
    unsupported: bool = False
    source: EvidenceSource | None = None


class KnowledgeSetting(DomainModel):
    canonical_setting_id: str
    platform: Platform
    scope: Scope
    display_name: dict[str, str]
    category: dict[str, str]
    description: dict[str, str]
    baseline_value: JsonValue
    value_definition: ValueDefinition
    comparison_rule: ComparisonRule
    applicability: ApplicabilityRule
    impact_less_restrictive: dict[str, str]
    impact_more_restrictive: dict[str, str]
    restart_behavior: dict[str, str] | None = None
    new_sign_in_behavior: dict[str, str] | None = None
    connectivity_risk: dict[str, str] | None = None
    aliases: list[str] = Field(default_factory=list)
    evidence_sources: list[EvidenceSource]
    severity_if_less_restrictive: FindingSeverity = FindingSeverity.INFORMATION


class DecisionTraceStep(DomainModel):
    order: int = Field(ge=1)
    gate: str
    outcome: str
    explanation: dict[str, str]
    evidence_ids: list[str] = Field(default_factory=list)


class SettingEvaluation(DomainModel):
    observation: SettingObservation
    raw_alignment_status: AlignmentStatus
    effective_alignment_status: AlignmentStatus
    microsoft_value: JsonValue = None
    baseline_product: str | None = None
    baseline_version: str | None = None
    evidence: list[EvidenceSource] = Field(default_factory=list)
    evidence_confidence: EvidenceConfidence
    applicability: ApplicabilityState
    applicability_reasons: list[str] = Field(default_factory=list)
    not_evaluable_reasons: list[str] = Field(default_factory=list)
    trace: list[DecisionTraceStep] = Field(default_factory=list)


class RuntimeEvidence(DomainModel):
    state: RuntimeState
    targeted_count: int | None = Field(default=None, ge=0)
    success_count: int | None = Field(default=None, ge=0)
    error_count: int | None = Field(default=None, ge=0)
    conflict_count: int | None = Field(default=None, ge=0)
    pending_count: int | None = Field(default=None, ge=0)
    not_applicable_count: int | None = Field(default=None, ge=0)
    report_timestamp: datetime | None = None
    source: EvidenceSource | None = None
    api_version: str | None = None


class Finding(DomainModel):
    finding_id: str
    severity: FindingSeverity
    finding_type: FindingType
    policy_id: str
    policy_name: str
    setting_id: str
    setting_name: dict[str, str]
    configured_value: JsonValue
    microsoft_value: JsonValue = None
    alignment: AlignmentStatus
    raw_alignment: AlignmentStatus | None = None
    title: dict[str, str]
    explanation: dict[str, str]
    why_it_matters: dict[str, str]
    user_impact: dict[str, str]
    business_impact: dict[str, str]
    recommended_action: dict[str, str]
    pilot_suggestion: dict[str, str]
    rollback_suggestion: dict[str, str]
    evidence_confidence: EvidenceConfidence
    evidence: list[EvidenceSource]
    baseline_product: str | None = None
    baseline_version: str | None = None
    verification_date: date | None = None
    decision_trace: list[DecisionTraceStep]
    assignments: list[AssignmentTarget]
    affected_device_count: int | None = Field(default=None, ge=0)
    deviation_state: str | None = None
    accepted_deviation: AcceptedDeviation | None = None
    applicability: ApplicabilityState
    runtime_evidence: RuntimeEvidence | None = None
    not_evaluable_reasons: list[str] = Field(default_factory=list)


class ConflictResult(DomainModel):
    conflict_id: str
    confidence: ConflictConfidence
    classification: str
    canonical_setting_id: str
    policy_a_id: str
    policy_a_name: str
    policy_a_value: JsonValue
    policy_b_id: str
    policy_b_name: str
    policy_b_value: JsonValue
    assignments_a: list[AssignmentTarget]
    assignments_b: list[AssignmentTarget]
    overlap_result: str
    reasoning: dict[str, str]
    affected_device_count: int | None = Field(default=None, ge=0)
    recommended_action: dict[str, str]


class AssignmentRisk(DomainModel):
    risk_id: str
    policy_id: str
    risk_type: str
    severity: FindingSeverity
    explanation: dict[str, str]
    recommended_action: dict[str, str]


class PolicyEvaluation(DomainModel):
    policy: PolicyDocument
    settings: list[SettingEvaluation]
    findings: list[Finding]
    assignment_risks: list[AssignmentRisk] = Field(default_factory=list)
    runtime_evidence: RuntimeEvidence | None = None


class CoverageMetrics(DomainModel):
    parser_coverage: float | None = Field(default=None, ge=0, le=1)
    technical_extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    exact_setting_coverage: float | None = Field(default=None, ge=0, le=1)
    exact_value_semantic_coverage: float | None = Field(default=None, ge=0, le=1)
    microsoft_baseline_coverage: float | None = Field(default=None, ge=0, le=1)
    documentation_coverage: float | None = Field(default=None, ge=0, le=1)
    assignment_analysis_coverage: float | None = Field(default=None, ge=0, le=1)
    conflict_analysis_coverage: float | None = Field(default=None, ge=0, le=1)
    runtime_evidence_coverage: float | None = Field(default=None, ge=0, le=1)
    evaluable_settings: int = Field(ge=0)
    not_evaluable_settings: int = Field(ge=0)


class DecisionResult(DomainModel):
    status: DecisionStatus
    title: dict[str, str]
    reason: dict[str, str]
    blocking_conditions: list[str]
    nonblocking_warnings: list[str]
    next_action: dict[str, str]
    evidence_summary: dict[str, str]
    failed_gates: list[str]
    decision_trace: list[DecisionTraceStep]


class AcceptedDeviation(DomainModel):
    deviation_id: str = Field(min_length=1)
    schema_version: str = Field(pattern=r"^1\.0$")
    canonical_setting_id: str = Field(min_length=5)
    policy_id: str | None = None
    accepted_value: JsonValue
    reason: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    approver: str = Field(min_length=1)
    ticket: str = Field(min_length=1)
    valid_from: date
    valid_until: date

    @model_validator(mode="after")
    def validate_dates(self) -> AcceptedDeviation:
        if self.valid_until < self.valid_from:
            raise ValueError("valid_until must not be earlier than valid_from")
        return self


class OrganizationRequirement(DomainModel):
    requirement_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    applies_to: list[str] = Field(default_factory=list)


class AuditContext(DomainModel):
    os_version: str | None = None
    edition: str | None = None
    architecture: str | None = None
    enrollment_type: str | None = None
    supervised: bool | None = None
    granted_licenses: list[str] = Field(default_factory=list)
    physical_device: bool | None = None
    vdi: bool | None = None
    shared_device: bool | None = None
    pilot_context: str | None = None
    environment_notes: str | None = None


class AuditConfiguration(DomainModel):
    language: str = Field(default="de", pattern=r"^(de|en)$")
    active_pack_ids: list[str]
    exact_only: bool = True
    history_enabled: bool = False
    save_reports: bool = False
    context: AuditContext = Field(default_factory=AuditContext)
    organization_requirements: list[OrganizationRequirement] = Field(default_factory=list)


class ReportMetadata(DomainModel):
    generated_at: datetime
    application_version: str
    audit_schema_version: str
    report_schema_version: str
    selected_pack_ids: list[str]
    selected_pack_versions: list[str]
    pack_hashes: list[str]
    verification_dates: list[date]
    audit_mode: AuditMode
    runtime_data_age_seconds: int | None = None
    limitations: list[str]
    independent_project_disclaimer: str


class AuditResult(DomainModel):
    audit_id: str
    schema_version: str = AUDIT_SCHEMA_VERSION
    created_at: datetime
    mode: AuditMode
    is_synthetic: bool
    configuration: AuditConfiguration
    policies: list[PolicyEvaluation]
    findings: list[Finding]
    conflicts: list[ConflictResult]
    assignment_risks: list[AssignmentRisk]
    diagnostics: list[ParserDiagnostic]
    coverage: CoverageMetrics
    decision: DecisionResult
    selected_pack_manifests: list[KnowledgePackManifest]
