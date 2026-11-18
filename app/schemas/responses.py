from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import (
    GenderEnum,
    HealthIssuesEnum,
    OccupationEnum,
    SleepQualityEnum,
    StressLevelEnum,
)


class CoffeeRecordResponse(BaseModel):
    id: int
    age: int
    gender: GenderEnum
    country: str
    coffee_intake: float
    caffeine_mg: float
    sleep_hours: float
    sleep_quality: SleepQualityEnum
    bmi: float
    heart_rate: int
    stress_level: StressLevelEnum
    physical_activity_hours: float
    health_issues: HealthIssuesEnum
    occupation: OccupationEnum
    smoking: bool
    alcohol_consumption: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int = Field(description="Total number of records matching the filter criteria")
    page: int = Field(description="Current page index (1-based)")
    page_size: int = Field(description="Number of records returned per page")
    total_pages: int = Field(description="Total number of available pages")
    has_next: bool = Field(description="Whether there is a subsequent page")
    has_previous: bool = Field(description="Whether there is a preceding page")


class SummaryItem(BaseModel):
    group_value: str = Field(description="The value of the grouping key (e.g. Germany)")
    record_count: int = Field(description="Number of individuals in this group")
    avg_sleep_hours: float = Field(description="Average sleep hours in this group")
    avg_caffeine_mg: float = Field(description="Average caffeine consumption in mg")
    avg_bmi: float = Field(description="Average BMI in this group")
    avg_coffee_intake: float = Field(description="Average coffee intake in cups/day")


class SummaryResponse(BaseModel):
    group_by: str = Field(description="Field used for grouping (e.g. country, sleep_quality)")
    total_groups: int = Field(description="Number of distinct groups returned")
    results: list[SummaryItem]
