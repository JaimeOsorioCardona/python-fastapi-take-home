"""Repository for coffee records using raw psycopg3 parameterized queries."""

from typing import Any

from psycopg import Connection, sql
from psycopg.rows import DictRow

from app.schemas.filters import CoffeeFilterParams

ALLOWED_SUMMARY_GROUPS = {
    "country",
    "gender",
    "sleep_quality",
    "stress_level",
    "occupation",
    "health_issues",
}


class CoffeeRecordRepository:
    def __init__(self, conn: Connection[DictRow]) -> None:
        self.conn = conn

    def _build_where_clause(
        self, filters: CoffeeFilterParams
    ) -> tuple[sql.Composable, dict[str, Any]]:
        conditions: list[sql.Composable] = []
        params: dict[str, Any] = {}

        if filters.country:
            conditions.append(sql.SQL("country = ANY(%(countries)s)"))
            params["countries"] = filters.country

        if filters.gender:
            conditions.append(sql.SQL("gender = ANY(%(genders)s)"))
            params["genders"] = [g.value for g in filters.gender]

        if filters.sleep_quality:
            conditions.append(sql.SQL("sleep_quality = ANY(%(sleep_qualities)s)"))
            params["sleep_qualities"] = [sq.value for sq in filters.sleep_quality]

        if filters.stress_level:
            conditions.append(sql.SQL("stress_level = ANY(%(stress_levels)s)"))
            params["stress_levels"] = [sl.value for sl in filters.stress_level]

        if filters.occupation:
            conditions.append(sql.SQL("occupation = ANY(%(occupations)s)"))
            params["occupations"] = [occ.value for occ in filters.occupation]

        if filters.health_issues:
            conditions.append(sql.SQL("health_issues = ANY(%(health_issues)s)"))
            params["health_issues"] = [hi.value for hi in filters.health_issues]

        if filters.smoking is not None:
            conditions.append(sql.SQL("smoking = %(smoking)s"))
            params["smoking"] = filters.smoking

        if filters.alcohol_consumption is not None:
            conditions.append(sql.SQL("alcohol_consumption = %(alcohol_consumption)s"))
            params["alcohol_consumption"] = filters.alcohol_consumption

        # Ranges
        if filters.min_age is not None:
            conditions.append(sql.SQL("age >= %(min_age)s"))
            params["min_age"] = filters.min_age

        if filters.max_age is not None:
            conditions.append(sql.SQL("age <= %(max_age)s"))
            params["max_age"] = filters.max_age

        if filters.min_coffee_intake is not None:
            conditions.append(sql.SQL("coffee_intake >= %(min_coffee_intake)s"))
            params["min_coffee_intake"] = filters.min_coffee_intake

        if filters.max_coffee_intake is not None:
            conditions.append(sql.SQL("coffee_intake <= %(max_coffee_intake)s"))
            params["max_coffee_intake"] = filters.max_coffee_intake

        if filters.min_bmi is not None:
            conditions.append(sql.SQL("bmi >= %(min_bmi)s"))
            params["min_bmi"] = filters.min_bmi

        if filters.max_bmi is not None:
            conditions.append(sql.SQL("bmi <= %(max_bmi)s"))
            params["max_bmi"] = filters.max_bmi

        if filters.min_sleep_hours is not None:
            conditions.append(sql.SQL("sleep_hours >= %(min_sleep_hours)s"))
            params["min_sleep_hours"] = filters.min_sleep_hours

        if filters.max_sleep_hours is not None:
            conditions.append(sql.SQL("sleep_hours <= %(max_sleep_hours)s"))
            params["max_sleep_hours"] = filters.max_sleep_hours

        where_sql: sql.Composable
        if conditions:
            where_sql = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
        else:
            where_sql = sql.SQL("")

        return where_sql, params

    def get_by_id(self, record_id: int) -> dict[str, Any] | None:
        query = sql.SQL("SELECT * FROM public.coffee_records WHERE id = %(id)s;")
        with self.conn.cursor() as cur:
            cur.execute(query, {"id": record_id})
            row = cur.fetchone()
            return dict(row) if row else None

    def find_records(
        self,
        filters: CoffeeFilterParams,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        where_sql, params = self._build_where_clause(filters)

        # 1. Count query
        count_query = sql.SQL("SELECT COUNT(*) AS total FROM public.coffee_records") + where_sql
        with self.conn.cursor() as cur:
            cur.execute(count_query, params)
            count_row = cur.fetchone()
            total: int = count_row["total"] if count_row else 0

        if total == 0:
            return [], 0

        # 2. Records query with offset and limit
        offset = (page - 1) * page_size
        params_with_paging = dict(params, limit=page_size, offset=offset)

        records_query = (
            sql.SQL(
                """
                SELECT
                    id, age, gender, country, coffee_intake, caffeine_mg,
                    sleep_hours, sleep_quality, bmi, heart_rate, stress_level,
                    physical_activity_hours, health_issues, occupation,
                    smoking, alcohol_consumption, created_at
                FROM public.coffee_records
                """
            )
            + where_sql
            + sql.SQL(" ORDER BY id ASC LIMIT %(limit)s OFFSET %(offset)s;")
        )

        with self.conn.cursor() as cur:
            cur.execute(records_query, params_with_paging)
            rows = cur.fetchall()
            return [dict(r) for r in rows], total

    def get_summary(
        self,
        filters: CoffeeFilterParams,
        group_by: str = "country",
    ) -> list[dict[str, Any]]:
        if group_by not in ALLOWED_SUMMARY_GROUPS:
            raise ValueError(
                f"Invalid group_by '{group_by}'. Allowed: {sorted(ALLOWED_SUMMARY_GROUPS)}"
            )

        where_sql, params = self._build_where_clause(filters)
        group_identifier = sql.Identifier(group_by)

        summary_query = sql.SQL(
            """
            SELECT
                {group_col}::text AS group_value,
                COUNT(*)::int AS record_count,
                ROUND(AVG(sleep_hours)::numeric, 2)::float AS avg_sleep_hours,
                ROUND(AVG(caffeine_mg)::numeric, 2)::float AS avg_caffeine_mg,
                ROUND(AVG(bmi)::numeric, 2)::float AS avg_bmi,
                ROUND(AVG(coffee_intake)::numeric, 2)::float AS avg_coffee_intake
            FROM public.coffee_records
            {where_clause}
            GROUP BY {group_col}
            ORDER BY record_count DESC, group_value ASC;
            """
        ).format(
            group_col=group_identifier,
            where_clause=where_sql,
        )

        with self.conn.cursor() as cur:
            cur.execute(summary_query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
