"""Create deterministic high-volume ledger fixtures in the guarded Stage 6 database."""

from __future__ import annotations

import argparse
import math
import os
import uuid
from datetime import timedelta

import psycopg
from stage6_guard import psycopg_url

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://ctec_stage6:stage6_local_only@127.0.0.1:25432/ctec_gl_stage6"
)
NAMESPACE = uuid.UUID("5051d41f-8892-4ff9-979c-e8676904945f")


def ensure_three_years(
    connection: psycopg.Connection[tuple[object, ...]], company_id: uuid.UUID
) -> None:
    years = connection.execute(
        "SELECT id, end_date FROM fiscal_years WHERE company_id = %s ORDER BY start_date",
        (company_id,),
    ).fetchall()
    while len(years) < 3:
        start_date = years[-1][1] + timedelta(days=1)
        year_id = uuid.uuid5(NAMESPACE, f"{company_id}:stage6-year:{len(years) + 1}")
        end_date = start_date + timedelta(days=(12 * 28) - 1)
        label = f"STAGE6-FY{len(years) + 1}"
        connection.execute(
            """
            INSERT INTO fiscal_years (id, company_id, label, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (year_id, company_id, label, start_date, end_date),
        )
        for period_no in range(1, 13):
            period_start = start_date + timedelta(days=(period_no - 1) * 28)
            connection.execute(
                """
                INSERT INTO fiscal_periods
                    (id, company_id, fiscal_year_id, period_no, label, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'open')
                """,
                (
                    uuid.uuid5(NAMESPACE, f"{year_id}:period:{period_no}"),
                    company_id,
                    year_id,
                    period_no,
                    f"{label}-P{period_no:02d}",
                    period_start,
                    period_start + timedelta(days=27),
                ),
            )
        years.append((year_id, end_date))


def prepare_company(
    connection: psycopg.Connection[tuple[object, ...]],
    company_id: uuid.UUID,
    code: str,
    target: int,
) -> dict[str, object]:
    ensure_three_years(connection, company_id)
    current_lines = connection.execute(
        "SELECT count(*) FROM journal_lines WHERE company_id = %s", (company_id,)
    ).fetchone()[0]
    entries_needed = max(0, math.ceil((target - current_lines) / 2))
    start = (
        connection.execute(
            "SELECT count(*) FROM journal_batches WHERE company_id = %s AND batch_no LIKE 'S6-%%'",
            (company_id,),
        ).fetchone()[0]
        + 1
    )
    end = start + entries_needed - 1
    if entries_needed:
        admin_id = connection.execute(
            "SELECT id FROM users WHERE email = 'admin@example.com'"
        ).fetchone()[0]
        accounts = dict(
            connection.execute(
                "SELECT code, id FROM accounts WHERE company_id = %s AND code IN ('1000', '4000')",
                (company_id,),
            ).fetchall()
        )
        if set(accounts) != {"1000", "4000"}:
            raise RuntimeError(f"{code} is missing postable fixture accounts 1000/4000")
        periods = [
            row[0]
            for row in connection.execute(
                """
                SELECT p.id FROM fiscal_periods p
                JOIN fiscal_years y ON y.id = p.fiscal_year_id AND y.company_id = p.company_id
                WHERE p.company_id = %s ORDER BY y.start_date, p.period_no
                """,
                (company_id,),
            ).fetchall()
        ]
        currency = connection.execute(
            "SELECT base_currency_code FROM companies WHERE id = %s", (company_id,)
        ).fetchone()[0]
        batch_key = f"stage6-{code}-batch-"
        entry_key = f"stage6-{code}-entry-"
        line_key = f"stage6-{code}-line-"

        connection.execute(
            """
            INSERT INTO journal_batches
                (id, company_id, batch_no, description, status, created_by_id,
                 approved_by_id, approved_at, posted_at, version)
            SELECT md5(%s || g::text)::uuid, %s, 'S6-' || lpad(g::text, 9, '0'),
                   'Stage 6 generated volume fixture', 'posted', %s, %s, now(), now(), 1
            FROM generate_series(%s, %s) AS g
            """,
            (batch_key, company_id, admin_id, admin_id, start, end),
        )
        connection.execute(
            """
            INSERT INTO journal_entries
                (id, company_id, batch_id, entry_no, entry_date, posting_date,
                 fiscal_period_id, reference, description, status, created_by_id, posted_at)
            SELECT md5(%s || g::text)::uuid, %s, md5(%s || g::text)::uuid,
                   'S6-' || lpad(g::text, 9, '0'), p.start_date, p.start_date, p.id,
                   'STAGE6', 'Stage 6 generated volume fixture', 'posted', %s, now()
            FROM generate_series(%s, %s) AS g
            JOIN fiscal_periods p
              ON p.company_id = %s
             AND p.id = (%s::uuid[])[((g - 1) %% %s) + 1]
            """,
            (
                entry_key,
                company_id,
                batch_key,
                admin_id,
                start,
                end,
                company_id,
                periods,
                len(periods),
            ),
        )
        connection.execute(
            """
            INSERT INTO journal_lines
                (id, company_id, entry_id, line_no, account_id, description, currency_code,
                 exchange_rate, debit_original, credit_original, debit_base, credit_base)
            SELECT md5(%s || g::text || '-' || side::text)::uuid, %s,
                   md5(%s || g::text)::uuid, side,
                   CASE WHEN side = 1 THEN %s ELSE %s END,
                   'Stage 6 generated volume fixture', %s, 1,
                   CASE WHEN side = 1 THEN 1 ELSE 0 END,
                   CASE WHEN side = 2 THEN 1 ELSE 0 END,
                   CASE WHEN side = 1 THEN 1 ELSE 0 END,
                   CASE WHEN side = 2 THEN 1 ELSE 0 END
            FROM generate_series(%s, %s) AS g CROSS JOIN generate_series(1, 2) AS side
            """,
            (
                line_key,
                company_id,
                entry_key,
                accounts["1000"],
                accounts["4000"],
                currency,
                start,
                end,
            ),
        )
        connection.execute(
            """
            INSERT INTO posting_events
                (id, company_id, entry_id, posted_by_id, debit_total, credit_total, digest)
            SELECT md5(%s || 'posting-' || g::text)::uuid, %s,
                   md5(%s || g::text)::uuid, %s, 1, 1,
                   md5(%s || g::text) || md5(%s || g::text)
            FROM generate_series(%s, %s) AS g
            """,
            (
                entry_key,
                company_id,
                entry_key,
                admin_id,
                entry_key,
                batch_key,
                start,
                end,
            ),
        )

        connection.execute(
            """
            INSERT INTO period_balances
                (company_id, fiscal_period_id, account_id, currency_code,
                 debit_base, credit_base, debit_original, credit_original)
            SELECT e.company_id, e.fiscal_period_id, l.account_id, l.currency_code,
                   sum(l.debit_base), sum(l.credit_base),
                   sum(l.debit_original), sum(l.credit_original)
            FROM journal_entries e
            JOIN journal_lines l ON l.company_id = e.company_id AND l.entry_id = e.id
            WHERE e.company_id = %s AND e.status = 'posted'
            GROUP BY e.company_id, e.fiscal_period_id, l.account_id, l.currency_code
            ON CONFLICT (company_id, fiscal_period_id, account_id, currency_code)
            DO UPDATE SET debit_base = EXCLUDED.debit_base,
                          credit_base = EXCLUDED.credit_base,
                          debit_original = EXCLUDED.debit_original,
                          credit_original = EXCLUDED.credit_original,
                          updated_at = now()
            """,
            (company_id,),
        )
    final_lines = connection.execute(
        "SELECT count(*) FROM journal_lines WHERE company_id = %s", (company_id,)
    ).fetchone()[0]
    year_count = connection.execute(
        "SELECT count(*) FROM fiscal_years WHERE company_id = %s", (company_id,)
    ).fetchone()[0]
    debit, credit = connection.execute(
        """
        SELECT coalesce(sum(l.debit_base), 0), coalesce(sum(l.credit_base), 0)
        FROM journal_lines l JOIN journal_entries e
          ON e.company_id = l.company_id AND e.id = l.entry_id
        WHERE e.company_id = %s AND e.status = 'posted'
        """,
        (company_id,),
    ).fetchone()
    return {
        "company": code,
        "lines": final_lines,
        "fiscal_years": year_count,
        "posted_debit": str(debit),
        "posted_credit": str(credit),
        "balanced": debit == credit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-lines", type=int, default=100_000)
    parser.add_argument("--company-code", action="append", default=[])
    parser.add_argument(
        "--database-url", default=os.getenv("STAGE6_DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    args = parser.parse_args()
    if args.target_lines < 2:
        raise RuntimeError("--target-lines must be at least 2")
    with psycopg.connect(psycopg_url(args.database_url)) as connection:
        statement = "SELECT id, code FROM companies WHERE active IS TRUE"
        parameters: tuple[object, ...] = ()
        if args.company_code:
            statement += " AND code = ANY(%s)"
            parameters = (args.company_code,)
        statement += " ORDER BY code"
        companies = connection.execute(statement, parameters).fetchall()
        if not companies:
            raise RuntimeError("No matching seeded companies found")
        evidence = [
            prepare_company(connection, company_id, code, args.target_lines)
            for company_id, code in companies
        ]
        connection.commit()
    for item in evidence:
        print(
            f"{item['company']}: {item['lines']} lines, {item['fiscal_years']} years, "
            f"balanced={item['balanced']}"
        )


if __name__ == "__main__":
    main()
