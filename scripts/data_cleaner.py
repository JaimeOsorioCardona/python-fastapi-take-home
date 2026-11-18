"""Data cleaning and validation module for the coffee health dataset."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import (
    GenderEnum,
    HealthIssuesEnum,
    OccupationEnum,
    SleepQualityEnum,
    StressLevelEnum,
)
from app.domain.models import CoffeeRecord

# Plausible biological and physical bounds (documented for Part 1 & Part 4)
AGE_MIN = 18
AGE_MAX = 120
COFFEE_INTAKE_MIN = 0.0
COFFEE_INTAKE_MAX = 25.0
CAFFEINE_MG_MIN = 0.0
CAFFEINE_MG_MAX = 3000.0
SLEEP_HOURS_MIN = 0.0
SLEEP_HOURS_MAX = 24.0
BMI_MIN = 10.0
BMI_MAX = 70.0
HEART_RATE_MIN = 35
HEART_RATE_MAX = 220
PHYSICAL_ACTIVITY_MIN = 0.0
PHYSICAL_ACTIVITY_MAX = 168.0  # max hours in a week

# Canonical country mapping to fix case and whitespace
CANONICAL_COUNTRIES: dict[str, str] = {
    "australia": "Australia",
    "belgium": "Belgium",
    "brazil": "Brazil",
    "canada": "Canada",
    "china": "China",
    "finland": "Finland",
    "france": "France",
    "germany": "Germany",
    "india": "India",
    "italy": "Italy",
    "japan": "Japan",
    "mexico": "Mexico",
    "netherlands": "Netherlands",
    "norway": "Norway",
    "south korea": "South Korea",
    "spain": "Spain",
    "sweden": "Sweden",
    "switzerland": "Switzerland",
    "uk": "UK",
    "usa": "USA",
}

BOOLEAN_TRUE_STRINGS = {"1", "true", "yes", "y"}
BOOLEAN_FALSE_STRINGS = {"0", "false", "no", "n"}


@dataclass(frozen=True, slots=True)
class ValidationResult:
    record: CoffeeRecord | None
    line_number: int
    raw_id: str | None
    was_fixed: bool = False
    rejection_reasons: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.record is not None and len(self.rejection_reasons) == 0


def parse_boolean(val: Any) -> tuple[bool | None, bool]:
    """Parse a flexible boolean representation.

    Returns:
        (parsed_bool, was_normalized)
    """
    if val is None:
        return None, False
    cleaned = str(val).strip().lower()
    if cleaned in BOOLEAN_TRUE_STRINGS:
        was_normalized = cleaned != "1"
        return True, was_normalized
    if cleaned in BOOLEAN_FALSE_STRINGS:
        was_normalized = cleaned != "0"
        return False, was_normalized
    return None, False


def clean_and_validate_row(raw: Mapping[Any, Any], line_number: int) -> ValidationResult:
    """Validate and normalize a raw CSV row dictionary into a domain CoffeeRecord.

    Records that cannot be physically or logically validated are rejected with reasons.
    Records with whitespace, case or boolean text variations are normalized.
    """
    reasons: list[str] = []
    was_fixed = False

    # Check for malformed row (extra or missing columns)
    if None in raw or any(v is None for v in raw.values()):
        return ValidationResult(
            record=None,
            line_number=line_number,
            raw_id=str(raw.get("ID") or raw.get("\ufeffID") or "unknown"),
            was_fixed=False,
            rejection_reasons=["malformed_row: column count mismatch or missing required fields"],
        )

    # 1. ID
    raw_id_str = str(raw.get("ID") or raw.get("\ufeffID") or "").strip()
    try:
        record_id = int(raw_id_str)
        if record_id <= 0:
            reasons.append(f"invalid_id: must be a positive integer, got '{raw_id_str}'")
    except (ValueError, TypeError):
        reasons.append(f"unparseable_id: could not convert '{raw_id_str}' to integer")
        record_id = -1

    # 2. Age
    raw_age = str(raw.get("Age", "")).strip()
    try:
        age = int(raw_age)
        if age < AGE_MIN or age > AGE_MAX:
            reasons.append(f"out_of_range_age: {age} (expected {AGE_MIN}-{AGE_MAX})")
    except (ValueError, TypeError):
        reasons.append(f"unparseable_age: '{raw_age}'")
        age = -1

    # 3. Gender
    raw_gender = str(raw.get("Gender", "")).strip()
    gender_lower = raw_gender.lower()
    gender: GenderEnum | None = None
    if gender_lower in ("male", "m"):
        gender = GenderEnum.MALE
        if raw_gender != "Male":
            was_fixed = True
    elif gender_lower in ("female", "f"):
        gender = GenderEnum.FEMALE
        if raw_gender != "Female":
            was_fixed = True
    elif gender_lower == "other":
        gender = GenderEnum.OTHER
        if raw_gender != "Other":
            was_fixed = True
    else:
        reasons.append(f"invalid_gender: '{raw_gender}'")

    # 4. Country
    raw_country = str(raw.get("Country", "")).strip()
    country_key = raw_country.lower()
    if country_key in CANONICAL_COUNTRIES:
        country = CANONICAL_COUNTRIES[country_key]
        if raw_country != country:
            was_fixed = True
    elif raw_country:
        country = raw_country.title()
        if raw_country != country:
            was_fixed = True
    else:
        reasons.append("missing_country")
        country = ""

    # 5. Coffee_Intake
    raw_coffee = str(raw.get("Coffee_Intake", "")).strip()
    try:
        coffee_intake = round(float(raw_coffee), 2)
        if coffee_intake < COFFEE_INTAKE_MIN or coffee_intake > COFFEE_INTAKE_MAX:
            reasons.append(
                f"out_of_range_coffee_intake: {coffee_intake} "
                f"(expected {COFFEE_INTAKE_MIN}-{COFFEE_INTAKE_MAX})"
            )
    except (ValueError, TypeError):
        reasons.append(f"unparseable_coffee_intake: '{raw_coffee}'")
        coffee_intake = -1.0

    # 6. Caffeine_mg
    raw_caffeine = str(raw.get("Caffeine_mg", "")).strip()
    try:
        caffeine_mg = round(float(raw_caffeine), 2)
        if caffeine_mg < CAFFEINE_MG_MIN or caffeine_mg > CAFFEINE_MG_MAX:
            reasons.append(
                f"out_of_range_caffeine_mg: {caffeine_mg} "
                f"(expected {CAFFEINE_MG_MIN}-{CAFFEINE_MG_MAX})"
            )
    except (ValueError, TypeError):
        reasons.append(f"unparseable_caffeine_mg: '{raw_caffeine}'")
        caffeine_mg = -1.0

    # 7. Sleep_Hours
    raw_sleep = str(raw.get("Sleep_Hours", "")).strip()
    try:
        sleep_hours = round(float(raw_sleep), 2)
        if sleep_hours < SLEEP_HOURS_MIN or sleep_hours > SLEEP_HOURS_MAX:
            reasons.append(
                f"out_of_range_sleep_hours: {sleep_hours} "
                f"(expected {SLEEP_HOURS_MIN}-{SLEEP_HOURS_MAX})"
            )
    except (ValueError, TypeError):
        reasons.append(f"unparseable_sleep_hours: '{raw_sleep}'")
        sleep_hours = -1.0

    # 8. Sleep_Quality
    raw_sleep_q = str(raw.get("Sleep_Quality", "")).strip()
    sq_map = {
        "poor": SleepQualityEnum.POOR,
        "fair": SleepQualityEnum.FAIR,
        "good": SleepQualityEnum.GOOD,
        "excellent": SleepQualityEnum.EXCELLENT,
    }
    sleep_quality = sq_map.get(raw_sleep_q.lower())
    if sleep_quality is None:
        reasons.append(f"invalid_sleep_quality: '{raw_sleep_q}'")
    elif raw_sleep_q != sleep_quality.value:
        was_fixed = True

    # 9. BMI
    raw_bmi = str(raw.get("BMI", "")).strip()
    try:
        bmi = round(float(raw_bmi), 2)
        if bmi < BMI_MIN or bmi > BMI_MAX:
            reasons.append(f"out_of_range_bmi: {bmi} (expected {BMI_MIN}-{BMI_MAX})")
    except (ValueError, TypeError):
        reasons.append(f"unparseable_bmi: '{raw_bmi}'")
        bmi = -1.0

    # 10. Heart_Rate
    raw_hr = str(raw.get("Heart_Rate", "")).strip()
    try:
        heart_rate = int(float(raw_hr))
        if heart_rate < HEART_RATE_MIN or heart_rate > HEART_RATE_MAX:
            reasons.append(
                f"out_of_range_heart_rate: {heart_rate} "
                f"(expected {HEART_RATE_MIN}-{HEART_RATE_MAX})"
            )
    except (ValueError, TypeError):
        reasons.append(f"unparseable_heart_rate: '{raw_hr}'")
        heart_rate = -1

    # 11. Stress_Level
    raw_stress = str(raw.get("Stress_Level", "")).strip()
    stress_map = {
        "low": StressLevelEnum.LOW,
        "medium": StressLevelEnum.MEDIUM,
        "high": StressLevelEnum.HIGH,
    }
    stress_level = stress_map.get(raw_stress.lower())
    if stress_level is None:
        reasons.append(f"invalid_stress_level: '{raw_stress}'")
    elif raw_stress != stress_level.value:
        was_fixed = True

    # 12. Physical_Activity_Hours
    raw_pa = str(raw.get("Physical_Activity_Hours", "")).strip()
    try:
        physical_activity = round(float(raw_pa), 2)
        if physical_activity < PHYSICAL_ACTIVITY_MIN or physical_activity > PHYSICAL_ACTIVITY_MAX:
            reasons.append(
                f"out_of_range_physical_activity: {physical_activity} "
                f"(expected {PHYSICAL_ACTIVITY_MIN}-{PHYSICAL_ACTIVITY_MAX})"
            )
    except (ValueError, TypeError):
        reasons.append(f"unparseable_physical_activity: '{raw_pa}'")
        physical_activity = -1.0

    # 13. Health_Issues
    raw_hi = str(raw.get("Health_Issues", "")).strip()
    hi_map = {
        "none": HealthIssuesEnum.NONE,
        "mild": HealthIssuesEnum.MILD,
        "moderate": HealthIssuesEnum.MODERATE,
        "severe": HealthIssuesEnum.SEVERE,
    }
    health_issues = hi_map.get(raw_hi.lower())
    if health_issues is None:
        reasons.append(f"invalid_health_issues: '{raw_hi}'")
    elif raw_hi != health_issues.value:
        was_fixed = True

    # 14. Occupation
    raw_occ = str(raw.get("Occupation", "")).strip()
    occ_map = {
        "office": OccupationEnum.OFFICE,
        "healthcare": OccupationEnum.HEALTHCARE,
        "service": OccupationEnum.SERVICE,
        "student": OccupationEnum.STUDENT,
        "other": OccupationEnum.OTHER,
    }
    occupation = occ_map.get(raw_occ.lower())
    if occupation is None:
        reasons.append(f"invalid_occupation: '{raw_occ}'")
    elif raw_occ != occupation.value:
        was_fixed = True

    # 15. Smoking
    smoking, smoking_norm = parse_boolean(raw.get("Smoking"))
    if smoking is None:
        reasons.append(f"invalid_smoking: '{raw.get('Smoking')}'")
    elif smoking_norm:
        was_fixed = True

    # 16. Alcohol_Consumption
    alcohol, alcohol_norm = parse_boolean(raw.get("Alcohol_Consumption"))
    if alcohol is None:
        reasons.append(f"invalid_alcohol: '{raw.get('Alcohol_Consumption')}'")
    elif alcohol_norm:
        was_fixed = True

    if reasons:
        return ValidationResult(
            record=None,
            line_number=line_number,
            raw_id=raw_id_str,
            was_fixed=False,
            rejection_reasons=reasons,
        )

    # All fields valid!
    assert gender is not None
    assert sleep_quality is not None
    assert stress_level is not None
    assert health_issues is not None
    assert occupation is not None
    assert smoking is not None
    assert alcohol is not None

    record = CoffeeRecord(
        id=record_id,
        age=age,
        gender=gender,
        country=country,
        coffee_intake=coffee_intake,
        caffeine_mg=caffeine_mg,
        sleep_hours=sleep_hours,
        sleep_quality=sleep_quality,
        bmi=bmi,
        heart_rate=heart_rate,
        stress_level=stress_level,
        physical_activity_hours=physical_activity,
        health_issues=health_issues,
        occupation=occupation,
        smoking=smoking,
        alcohol_consumption=alcohol,
    )

    return ValidationResult(
        record=record,
        line_number=line_number,
        raw_id=raw_id_str,
        was_fixed=was_fixed,
        rejection_reasons=[],
    )
