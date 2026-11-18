from enum import StrEnum


class GenderEnum(StrEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class SleepQualityEnum(StrEnum):
    POOR = "Poor"
    FAIR = "Fair"
    GOOD = "Good"
    EXCELLENT = "Excellent"


class StressLevelEnum(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class HealthIssuesEnum(StrEnum):
    NONE = "None"
    MILD = "Mild"
    MODERATE = "Moderate"
    SEVERE = "Severe"


class OccupationEnum(StrEnum):
    OFFICE = "Office"
    HEALTHCARE = "Healthcare"
    SERVICE = "Service"
    STUDENT = "Student"
    OTHER = "Other"
