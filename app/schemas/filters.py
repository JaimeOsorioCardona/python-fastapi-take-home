from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import (
    GenderEnum,
    HealthIssuesEnum,
    OccupationEnum,
    SleepQualityEnum,
    StressLevelEnum,
)


class CoffeeFilterParams(BaseModel):
    country: list[str] | None = Field(
        default=None,
        description="Filter by one or more countries (exact match)",
    )
    gender: list[GenderEnum] | None = Field(
        default=None,
        description="Filter by one or more genders",
    )
    sleep_quality: list[SleepQualityEnum] | None = Field(
        default=None,
        description="Filter by sleep quality (Poor, Fair, Good, Excellent)",
    )
    stress_level: list[StressLevelEnum] | None = Field(
        default=None,
        description="Filter by stress level (Low, Medium, High)",
    )
    occupation: list[OccupationEnum] | None = Field(
        default=None,
        description="Filter by occupation",
    )
    health_issues: list[HealthIssuesEnum] | None = Field(
        default=None,
        description="Filter by health issues",
    )
    smoking: bool | None = Field(
        default=None,
        description="Filter by smoking status (true/false)",
    )
    alcohol_consumption: bool | None = Field(
        default=None,
        description="Filter by alcohol consumption status (true/false)",
    )

    # Numeric range filters
    min_age: int | None = Field(default=None, ge=18, le=120, description="Minimum age (>= 18)")
    max_age: int | None = Field(default=None, ge=18, le=120, description="Maximum age (<= 120)")

    min_coffee_intake: float | None = Field(
        default=None, ge=0.0, le=25.0, description="Minimum coffee intake in cups/day"
    )
    max_coffee_intake: float | None = Field(
        default=None, ge=0.0, le=25.0, description="Maximum coffee intake in cups/day"
    )

    min_bmi: float | None = Field(default=None, ge=10.0, le=70.0, description="Minimum BMI")
    max_bmi: float | None = Field(default=None, ge=10.0, le=70.0, description="Maximum BMI")

    min_sleep_hours: float | None = Field(
        default=None, ge=0.0, le=24.0, description="Minimum sleep hours"
    )
    max_sleep_hours: float | None = Field(
        default=None, ge=0.0, le=24.0, description="Maximum sleep hours"
    )

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError(
                f"min_age ({self.min_age}) cannot be greater than max_age ({self.max_age})"
            )

        if (
            self.min_coffee_intake is not None
            and self.max_coffee_intake is not None
            and self.min_coffee_intake > self.max_coffee_intake
        ):
            raise ValueError(
                f"min_coffee_intake ({self.min_coffee_intake}) cannot be "
                f"greater than max_coffee_intake ({self.max_coffee_intake})"
            )

        if self.min_bmi is not None and self.max_bmi is not None and self.min_bmi > self.max_bmi:
            raise ValueError(
                f"min_bmi ({self.min_bmi}) cannot be greater than max_bmi ({self.max_bmi})"
            )

        if (
            self.min_sleep_hours is not None
            and self.max_sleep_hours is not None
            and self.min_sleep_hours > self.max_sleep_hours
        ):
            raise ValueError(
                f"min_sleep_hours ({self.min_sleep_hours}) cannot be "
                f"greater than max_sleep_hours ({self.max_sleep_hours})"
            )

        return self
