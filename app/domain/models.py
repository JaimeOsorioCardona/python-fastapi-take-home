from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import (
    GenderEnum,
    HealthIssuesEnum,
    OccupationEnum,
    SleepQualityEnum,
    StressLevelEnum,
)


@dataclass(frozen=True, slots=True)
class CoffeeRecord:
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
