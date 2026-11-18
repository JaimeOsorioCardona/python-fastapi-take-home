"""Unit tests for the data cleaning, normalization and validation logic.

These tests run completely in-memory without needing a database.
"""

from app.domain.enums import (
    GenderEnum,
    HealthIssuesEnum,
    OccupationEnum,
    SleepQualityEnum,
    StressLevelEnum,
)
from scripts.data_cleaner import clean_and_validate_row, parse_boolean


def test_parse_boolean_truthy_falsy() -> None:
    # Standard numbers
    val, norm = parse_boolean("1")
    assert val is True
    assert norm is False

    val, norm = parse_boolean("0")
    assert val is False
    assert norm is False

    # Normalized text variants
    val, norm = parse_boolean("yes")
    assert val is True
    assert norm is True

    val, norm = parse_boolean("NO")
    assert val is False
    assert norm is True

    val, norm = parse_boolean("true")
    assert val is True
    assert norm is True

    val, norm = parse_boolean("false")
    assert val is False
    assert norm is True

    val, norm = parse_boolean("Y")
    assert val is True
    assert norm is True

    # Invalid booleans
    val, norm = parse_boolean("-1")
    assert val is None
    assert norm is False

    val, norm = parse_boolean("2")
    assert val is None
    assert norm is False

    val, norm = parse_boolean(None)
    assert val is None
    assert norm is False


def test_clean_and_validate_valid_clean_row() -> None:
    row = {
        "ID": "1",
        "Age": "40",
        "Gender": "Male",
        "Country": "Germany",
        "Coffee_Intake": "3.5",
        "Caffeine_mg": "328.1",
        "Sleep_Hours": "7.5",
        "Sleep_Quality": "Good",
        "BMI": "24.9",
        "Heart_Rate": "78",
        "Stress_Level": "Low",
        "Physical_Activity_Hours": "14.5",
        "Health_Issues": "None",
        "Occupation": "Other",
        "Smoking": "0",
        "Alcohol_Consumption": "0",
    }
    result = clean_and_validate_row(row, line_number=2)
    assert result.is_valid
    assert result.was_fixed is False
    assert result.record is not None
    assert result.record.id == 1
    assert result.record.gender == GenderEnum.MALE
    assert result.record.country == "Germany"
    assert result.record.sleep_quality == SleepQualityEnum.GOOD
    assert result.record.stress_level == StressLevelEnum.LOW
    assert result.record.health_issues == HealthIssuesEnum.NONE
    assert result.record.occupation == OccupationEnum.OTHER
    assert result.record.smoking is False
    assert result.record.alcohol_consumption is False


def test_clean_and_validate_normalization_of_casing_and_whitespace() -> None:
    row = {
        "ID": "12",
        "Age": "29",
        "Gender": "  male  ",
        "Country": "\tusa ",
        "Coffee_Intake": "4.1",
        "Caffeine_mg": "385.2",
        "Sleep_Hours": "6.5",
        "Sleep_Quality": "good",
        "BMI": "23.1",
        "Heart_Rate": "80",
        "Stress_Level": "LOW",
        "Physical_Activity_Hours": "8.9",
        "Health_Issues": "none",
        "Occupation": "office",
        "Smoking": "no",
        "Alcohol_Consumption": "yes",
    }
    result = clean_and_validate_row(row, line_number=13)
    assert result.is_valid
    assert result.was_fixed is True
    assert result.record is not None
    assert result.record.gender == GenderEnum.MALE
    assert result.record.country == "USA"
    assert result.record.sleep_quality == SleepQualityEnum.GOOD
    assert result.record.stress_level == StressLevelEnum.LOW
    assert result.record.health_issues == HealthIssuesEnum.NONE
    assert result.record.occupation == OccupationEnum.OFFICE
    assert result.record.smoking is False
    assert result.record.alcohol_consumption is True


def test_clean_and_validate_rejects_out_of_range_values() -> None:
    # Negative age
    row_bad_age = {
        "ID": "100",
        "Age": "-5",
        "Gender": "Male",
        "Country": "Canada",
        "Coffee_Intake": "2.0",
        "Caffeine_mg": "150.0",
        "Sleep_Hours": "7.0",
        "Sleep_Quality": "Good",
        "BMI": "22.0",
        "Heart_Rate": "70",
        "Stress_Level": "Low",
        "Physical_Activity_Hours": "5.0",
        "Health_Issues": "None",
        "Occupation": "Office",
        "Smoking": "0",
        "Alcohol_Consumption": "0",
    }
    res = clean_and_validate_row(row_bad_age, line_number=10)
    assert not res.is_valid
    assert any("out_of_range_age" in r for r in res.rejection_reasons)

    # Impossible sleep hours (25 hours/day)
    row_bad_sleep = dict(row_bad_age, Age="30", Sleep_Hours="25.0")
    res = clean_and_validate_row(row_bad_sleep, line_number=11)
    assert not res.is_valid
    assert any("out_of_range_sleep_hours" in r for r in res.rejection_reasons)

    # Impossible resting heart rate (350 bpm)
    row_bad_hr = dict(row_bad_age, Age="30", Heart_Rate="350")
    res = clean_and_validate_row(row_bad_hr, line_number=12)
    assert not res.is_valid
    assert any("out_of_range_heart_rate" in r for r in res.rejection_reasons)


def test_clean_and_validate_rejects_unparseable_text_in_numeric_columns() -> None:
    row_text_age = {
        "ID": "101",
        "Age": "thirty",
        "Gender": "Female",
        "Country": "Spain",
        "Coffee_Intake": "2.0",
        "Caffeine_mg": "150.0",
        "Sleep_Hours": "7.0",
        "Sleep_Quality": "Good",
        "BMI": "22.0",
        "Heart_Rate": "70",
        "Stress_Level": "Low",
        "Physical_Activity_Hours": "5.0",
        "Health_Issues": "None",
        "Occupation": "Office",
        "Smoking": "0",
        "Alcohol_Consumption": "0",
    }
    res = clean_and_validate_row(row_text_age, line_number=15)
    assert not res.is_valid
    assert any("unparseable_age" in r for r in res.rejection_reasons)


def test_clean_and_validate_rejects_malformed_columns() -> None:
    row_missing_cols = {
        "ID": "102",
        "Age": "30",
        "Gender": "Male",
        "Country": "France",
        None: ["extra_unexpected_value"],
    }
    res = clean_and_validate_row(row_missing_cols, line_number=20)
    assert not res.is_valid
    assert any("malformed_row" in r for r in res.rejection_reasons)
