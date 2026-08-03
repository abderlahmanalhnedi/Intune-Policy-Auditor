"""Closed vocabularies used by deterministic analysis."""

from enum import StrEnum


class StringEnum(StrEnum):
    def __str__(self) -> str:
        return self.value


class Platform(StringEnum):
    WINDOWS = "windows"
    MACOS = "macos"
    IOS = "ios"
    IPADOS = "ipados"
    ANDROID = "android"
    LINUX = "linux"
    UNKNOWN = "unknown"


class PolicyKind(StringEnum):
    SETTINGS_CATALOG = "settings_catalog"
    ENDPOINT_SECURITY = "endpoint_security"
    SECURITY_BASELINE = "security_baseline"
    DEVICE_CONFIGURATION = "device_configuration"
    COMPLIANCE = "compliance"
    ADMINISTRATIVE_TEMPLATES = "administrative_templates"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class Scope(StringEnum):
    DEVICE = "device"
    USER = "user"
    BOTH = "both"
    UNKNOWN = "unknown"


class EvidenceType(StringEnum):
    MICROSOFT_SECURITY_BASELINE = "microsoft_security_baseline"
    MICROSOFT_CSP_DOCUMENTATION = "microsoft_csp_documentation"
    MICROSOFT_INTUNE_DOCUMENTATION = "microsoft_intune_documentation"
    MICROSOFT_GRAPH_METADATA = "microsoft_graph_metadata"
    MICROSOFT_RUNTIME_REPORT = "microsoft_runtime_report"
    MICROSOFT_SECURITY_COMPLIANCE_TOOLKIT = "microsoft_security_compliance_toolkit"
    APPLE_PLATFORM_DOCUMENTATION = "apple_platform_documentation"
    ORGANIZATIONAL_REQUIREMENT = "organizational_requirement"
    ACCEPTED_DEVIATION = "accepted_deviation"
    CATEGORY_ONLY = "category_only"
    UNKNOWN = "unknown"


class EvidenceConfidence(StringEnum):
    EXACT = "exact"
    STRONG = "strong"
    PARTIAL = "partial"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class AlignmentStatus(StringEnum):
    ALIGNED = "aligned"
    MORE_RESTRICTIVE = "more_restrictive"
    LESS_RESTRICTIVE = "less_restrictive"
    DIFFERENT = "different"
    ACCEPTED_DEVIATION = "accepted_deviation"
    EXPIRED_DEVIATION = "expired_deviation"
    NOT_IN_SELECTED_BASELINE = "not_in_selected_baseline"
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED = "unsupported"
    NOT_EVALUABLE = "not_evaluable"


class FindingSeverity(StringEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATION = "information"
    NONE = "none"


class FindingType(StringEnum):
    BASELINE_DEVIATION = "baseline_deviation"
    CONFIRMED_CONFLICT = "confirmed_conflict"
    PROBABLE_CONFLICT = "probable_conflict"
    POSSIBLE_CONFLICT = "possible_conflict"
    ASSIGNMENT_RISK = "assignment_risk"
    BROAD_ASSIGNMENT = "broad_assignment"
    MISSING_ASSIGNMENT = "missing_assignment"
    UNSUPPORTED_SETTING = "unsupported_setting"
    DEPRECATED_SETTING = "deprecated_setting"
    RUNTIME_ERROR = "runtime_error"
    RUNTIME_CONFLICT = "runtime_conflict"
    EXPIRED_DEVIATION = "expired_deviation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ConflictConfidence(StringEnum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    NONE = "none"


class RuntimeState(StringEnum):
    SUCCEEDED = "succeeded"
    ERROR = "error"
    CONFLICT = "conflict"
    PENDING = "pending"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ApplicabilityState(StringEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ValueType(StringEnum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DECIMAL = "decimal"
    STRING = "string"
    ENUM = "enum"
    CHOICE = "choice"
    LIST = "list"
    SET = "set"
    RANGE = "range"
    OBJECT = "object"
    NOT_CONFIGURED = "not_configured"
    UNKNOWN = "unknown"


class ComparisonMode(StringEnum):
    EXACT = "exact"
    ORDERED = "ordered"
    NUMERIC_MINIMUM = "numeric_minimum"
    NUMERIC_MAXIMUM = "numeric_maximum"
    NUMERIC_RANGE = "numeric_range"
    SET_EQUALS = "set_equals"
    SET_CONTAINS = "set_contains"
    LIST_EQUALS = "list_equals"
    CUSTOM = "custom"
    NOT_ORDERABLE = "not_orderable"


class AssignmentTargetType(StringEnum):
    ALL_USERS = "all_users"
    ALL_DEVICES = "all_devices"
    GROUP = "group"
    EXCLUSION_GROUP = "exclusion_group"
    UNKNOWN = "unknown"


class FilterMode(StringEnum):
    INCLUDE = "include"
    EXCLUDE = "exclude"


class DiagnosticSeverity(StringEnum):
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


class DecisionStatus(StringEnum):
    ALIGNED_WITH_SELECTED_BASELINE = "aligned_with_selected_baseline"
    ALIGNED_WITH_ACCEPTED_DEVIATIONS = "aligned_with_accepted_deviations"
    CHANGES_REQUIRED_BEFORE_PILOT = "changes_required_before_pilot"
    PILOT_RECOMMENDED = "pilot_recommended"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    RUNTIME_REMEDIATION_REQUIRED = "runtime_remediation_required"


class AuditMode(StringEnum):
    OFFLINE = "offline"
    TENANT = "tenant"
    DEMO = "demo"


class KnowledgePackStatus(StringEnum):
    SYNTHETIC = "synthetic"
    VERIFIED = "verified"
    PENDING_REVIEW = "pending_review"
    INVALID = "invalid"
