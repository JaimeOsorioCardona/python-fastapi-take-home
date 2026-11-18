-- 002_coffee_records.sql
-- Schema for coffee consumption and health metrics dataset.

CREATE TABLE IF NOT EXISTS public.coffee_records (
    id INTEGER PRIMARY KEY,
    age SMALLINT NOT NULL CHECK (age >= 18 AND age <= 120),
    gender VARCHAR(16) NOT NULL CHECK (gender IN ('Male', 'Female', 'Other')),
    country VARCHAR(64) NOT NULL,
    coffee_intake NUMERIC(4, 2) NOT NULL CHECK (coffee_intake >= 0 AND coffee_intake <= 25),
    caffeine_mg NUMERIC(6, 2) NOT NULL CHECK (caffeine_mg >= 0 AND caffeine_mg <= 3000),
    sleep_hours NUMERIC(4, 2) NOT NULL CHECK (sleep_hours >= 0 AND sleep_hours <= 24),
    sleep_quality VARCHAR(16) NOT NULL CHECK (sleep_quality IN ('Poor', 'Fair', 'Good', 'Excellent')),
    bmi NUMERIC(5, 2) NOT NULL CHECK (bmi >= 10 AND bmi <= 70),
    heart_rate SMALLINT NOT NULL CHECK (heart_rate >= 35 AND heart_rate <= 220),
    stress_level VARCHAR(16) NOT NULL CHECK (stress_level IN ('Low', 'Medium', 'High')),
    physical_activity_hours NUMERIC(5, 2) NOT NULL CHECK (physical_activity_hours >= 0 AND physical_activity_hours <= 168),
    health_issues VARCHAR(16) NOT NULL CHECK (health_issues IN ('None', 'Mild', 'Moderate', 'Severe')),
    occupation VARCHAR(32) NOT NULL CHECK (occupation IN ('Office', 'Healthcare', 'Service', 'Student', 'Other')),
    smoking BOOLEAN NOT NULL,
    alcohol_consumption BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Strategic B-tree indexes for API filtering and analytical queries:
CREATE INDEX IF NOT EXISTS idx_coffee_country ON public.coffee_records (country);
CREATE INDEX IF NOT EXISTS idx_coffee_gender ON public.coffee_records (gender);
CREATE INDEX IF NOT EXISTS idx_coffee_stress_sleep ON public.coffee_records (stress_level, sleep_quality);
CREATE INDEX IF NOT EXISTS idx_coffee_age ON public.coffee_records (age);
CREATE INDEX IF NOT EXISTS idx_coffee_intake ON public.coffee_records (coffee_intake);
CREATE INDEX IF NOT EXISTS idx_coffee_bmi ON public.coffee_records (bmi);
CREATE INDEX IF NOT EXISTS idx_coffee_sleep_hours ON public.coffee_records (sleep_hours);

-- Extended statistics for correlated categorical attributes:
-- PostgreSQL by default assumes column independence. Sleep quality and stress levels
-- are strongly correlated; multivariate statistics (MCV) prevent plan misestimations.
CREATE STATISTICS IF NOT EXISTS coffee_records_categories_stats (mcv)
    ON country, gender, stress_level, sleep_quality
    FROM public.coffee_records;
