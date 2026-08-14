import secrets
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    Account,
    AccountType,
    Budget,
    ClosingEvent,
    Company,
    Currency,
    ExchangeRate,
    FiscalPeriod,
    FiscalYear,
    JournalBatch,
    JournalEntry,
    JournalLine,
    JournalStatus,
    Membership,
    Permission,
    Role,
    RolePermission,
    User,
)
from app.schemas import CloseRequest, ReversalRequest
from app.security import hash_password
from app.seed_support import CAPABILITIES, stable_id
from app.services.accounting import post_batch, reverse_entry
from app.services.closing import close_fiscal_year


def add_calendar(db, company: Company, label: str, start: date, periods: int) -> None:  # type: ignore[no-untyped-def]
    fiscal_year = FiscalYear(
        id=stable_id(f"{company.code}:fy:{label}"),
        company_id=company.id,
        label=label,
        start_date=start,
        end_date=start + timedelta(days=periods * 28 - 1),
    )
    db.add(fiscal_year)
    db.flush()
    for period_no in range(1, periods + 1):
        period_start = start + timedelta(days=(period_no - 1) * 28)
        db.add(
            FiscalPeriod(
                id=stable_id(f"{company.code}:{label}:period:{period_no}"),
                company_id=company.id,
                fiscal_year_id=fiscal_year.id,
                period_no=period_no,
                label=f"P{period_no:02d}",
                start_date=period_start,
                end_date=period_start + timedelta(days=27),
            )
        )


DemoLine = tuple[str, str, Decimal, Decimal, Decimal, Decimal, Decimal]


def add_posted_demo(
    db: Session,
    company: Company,
    user: User,
    period: FiscalPeriod,
    key: str,
    description: str,
    lines: list[DemoLine],
) -> uuid.UUID:
    accounts = {
        account.code: account
        for account in db.scalars(select(Account).where(Account.company_id == company.id)).all()
    }
    batch = JournalBatch(
        id=stable_id(f"{company.code}:demo:batch:{key}"),
        company_id=company.id,
        batch_no=f"DEMO-{key}",
        description=description,
        status=JournalStatus.APPROVED,
        created_by_id=user.id,
        approved_by_id=user.id,
    )
    db.add(batch)
    db.flush()
    entry = JournalEntry(
        id=stable_id(f"{company.code}:demo:entry:{key}"),
        company_id=company.id,
        batch_id=batch.id,
        entry_no=f"DEMO-{key}",
        entry_date=period.start_date + timedelta(days=4),
        posting_date=period.start_date + timedelta(days=4),
        fiscal_period_id=period.id,
        reference=key,
        description=description,
        status=JournalStatus.APPROVED,
        created_by_id=user.id,
    )
    db.add(entry)
    db.flush()
    for line_no, (
        account_code,
        currency,
        rate,
        debit_original,
        credit_original,
        debit_base,
        credit_base,
    ) in enumerate(lines, 1):
        db.add(
            JournalLine(
                id=stable_id(f"{company.code}:demo:entry:{key}:line:{line_no}"),
                company_id=company.id,
                entry_id=entry.id,
                line_no=line_no,
                account_id=accounts[account_code].id,
                description=description,
                currency_code=currency,
                exchange_rate=rate,
                debit_original=debit_original,
                credit_original=credit_original,
                debit_base=debit_base,
                credit_base=credit_base,
            )
        )
    db.flush()
    post_batch(db, company.id, batch.id, user.id)
    return entry.id


def add_deterministic_accounting_cycle(db: Session, company: Company, user: User) -> None:
    years = list(
        db.scalars(
            select(FiscalYear)
            .where(FiscalYear.company_id == company.id)
            .order_by(FiscalYear.start_date)
        ).all()
    )
    periods = {
        (period.fiscal_year_id, period.period_no): period
        for period in db.scalars(
            select(FiscalPeriod).where(FiscalPeriod.company_id == company.id)
        ).all()
    }
    first_year, next_year = years
    p1 = periods[(first_year.id, 1)]
    p2 = periods[(first_year.id, 2)]
    p3 = periods[(first_year.id, 3)]
    p4 = periods[(first_year.id, 4)]
    next_p1 = periods[(next_year.id, 1)]
    next_p2 = periods[(next_year.id, 2)]
    accounts = {
        account.code: account
        for account in db.scalars(select(Account).where(Account.company_id == company.id)).all()
    }
    db.add(
        ExchangeRate(
            id=stable_id(f"{company.code}:demo:eur-rate"),
            company_id=company.id,
            currency_code="EUR",
            effective_date=p2.start_date,
            rate_to_base=Decimal("1.5000000000"),
            source="deterministic demo",
        )
    )
    for period_no in range(1, 19):
        period = periods[(first_year.id, period_no)]
        db.add_all(
            [
                Budget(
                    id=stable_id(f"{company.code}:demo:budget:revenue:{period_no}"),
                    company_id=company.id,
                    fiscal_period_id=period.id,
                    account_id=accounts["4000"].id,
                    scenario="Approved FY2026",
                    currency_code=company.base_currency_code,
                    amount=Decimal("-18000.000000"),
                ),
                Budget(
                    id=stable_id(f"{company.code}:demo:budget:expense:{period_no}"),
                    company_id=company.id,
                    fiscal_period_id=period.id,
                    account_id=accounts["5000"].id,
                    scenario="Approved FY2026",
                    currency_code=company.base_currency_code,
                    amount=Decimal("3500.000000"),
                ),
            ]
        )
    db.commit()
    add_posted_demo(
        db,
        company,
        user,
        p1,
        "SALE-001",
        "Normal cash sale",
        [
            (
                "1000",
                company.base_currency_code,
                Decimal("1"),
                Decimal("20000"),
                Decimal("0"),
                Decimal("20000"),
                Decimal("0"),
            ),
            (
                "4000",
                company.base_currency_code,
                Decimal("1"),
                Decimal("0"),
                Decimal("20000"),
                Decimal("0"),
                Decimal("20000"),
            ),
        ],
    )
    add_posted_demo(
        db,
        company,
        user,
        p2,
        "FX-001",
        "EUR expense at a fixed demonstration rate",
        [
            (
                "6100",
                "EUR",
                Decimal("1.5"),
                Decimal("1000"),
                Decimal("0"),
                Decimal("1500"),
                Decimal("0"),
            ),
            (
                "1000",
                company.base_currency_code,
                Decimal("1"),
                Decimal("0"),
                Decimal("1500"),
                Decimal("0"),
                Decimal("1500"),
            ),
        ],
    )
    adjustment_id = add_posted_demo(
        db,
        company,
        user,
        p3,
        "ADJ-001",
        "Accrual adjustment to be reversed",
        [
            (
                "1100",
                company.base_currency_code,
                Decimal("1"),
                Decimal("500"),
                Decimal("0"),
                Decimal("500"),
                Decimal("0"),
            ),
            (
                "4000",
                company.base_currency_code,
                Decimal("1"),
                Decimal("0"),
                Decimal("500"),
                Decimal("0"),
                Decimal("500"),
            ),
        ],
    )
    reverse_entry(
        db,
        company.id,
        adjustment_id,
        user.id,
        ReversalRequest(
            posting_date=p4.start_date + timedelta(days=4),
            fiscal_period_id=p4.id,
            reason="Deterministic next-period accrual reversal",
        ),
    )
    close_fiscal_year(
        db,
        company.id,
        first_year.id,
        user.id,
        CloseRequest(
            opening_period_id=next_p1.id,
            reason="Deterministic demonstration fiscal close",
        ),
    )
    draft_batch = JournalBatch(
        id=stable_id(f"{company.code}:demo:draft:batch"),
        company_id=company.id,
        batch_no="DEMO-PENDING",
        description="Pending maker-checker accrual",
        status=JournalStatus.DRAFT,
        created_by_id=user.id,
    )
    db.add(draft_batch)
    db.flush()
    draft_entry = JournalEntry(
        id=stable_id(f"{company.code}:demo:draft:entry"),
        company_id=company.id,
        batch_id=draft_batch.id,
        entry_no="DEMO-PENDING",
        entry_date=next_p2.start_date + timedelta(days=2),
        posting_date=next_p2.start_date + timedelta(days=2),
        fiscal_period_id=next_p2.id,
        reference="PENDING",
        description="Pending maker-checker accrual",
        status=JournalStatus.DRAFT,
        created_by_id=user.id,
    )
    db.add(draft_entry)
    db.flush()
    for line_no, account_code, debit, credit in (
        (1, "5000", Decimal("275"), Decimal("0")),
        (2, "2000", Decimal("0"), Decimal("275")),
    ):
        db.add(
            JournalLine(
                id=stable_id(f"{company.code}:demo:draft:line:{line_no}"),
                company_id=company.id,
                entry_id=draft_entry.id,
                line_no=line_no,
                account_id=accounts[account_code].id,
                description="Pending maker-checker accrual",
                currency_code=company.base_currency_code,
                exchange_rate=Decimal("1"),
                debit_original=debit,
                credit_original=credit,
                debit_base=debit,
                credit_base=credit,
            )
        )
    db.commit()
    assert db.scalar(select(ClosingEvent.id).where(ClosingEvent.company_id == company.id))


def seed(
    *,
    admin_email: str = "admin@example.com",
    admin_password: str = "CTec-Demo-Admin-2026!",
    admin_display_name: str = "Demo Administrator",
    disable_non_admin: bool = False,
) -> None:
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Seed skipped: data already exists")
            return
        for code, name, units in (
            ("SGD", "Singapore Dollar", 2),
            ("USD", "US Dollar", 2),
            ("EUR", "Euro", 2),
        ):
            db.add(Currency(code=code, name=name, minor_units=units))
        db.flush()
        companies = [
            Company(
                id=stable_id("company:acme"),
                code="ACME",
                name="Acme Trading Pte Ltd",
                base_currency_code="SGD",
            ),
            Company(
                id=stable_id("company:northstar"),
                code="NORTH",
                name="Northstar Services Ltd",
                base_currency_code="USD",
            ),
            Company(
                id=stable_id("company:edge-cycle"),
                code="EDGE",
                name="ZZ Edge Cycle Demonstration Ltd",
                base_currency_code="SGD",
            ),
        ]
        db.add_all(companies)
        for code, description, legacy in CAPABILITIES:
            db.add(Permission(code=code, description=description, legacy_number=legacy))
        users = {
            "admin": User(
                id=stable_id("user:admin"),
                email=admin_email.lower(),
                display_name=admin_display_name,
                password_hash=hash_password(admin_password),
            ),
            "preparer": User(
                id=stable_id("user:preparer"),
                email="preparer@example.com",
                display_name="Priya Preparer",
                password_hash=hash_password(
                    secrets.token_urlsafe(32) if disable_non_admin else "CTec-Demo-Prepare-2026!"
                ),
                active=not disable_non_admin,
            ),
            "approver": User(
                id=stable_id("user:approver"),
                email="approver@example.com",
                display_name="Alex Approver",
                password_hash=hash_password(
                    secrets.token_urlsafe(32) if disable_non_admin else "CTec-Demo-Approve-2026!"
                ),
                active=not disable_non_admin,
            ),
        }
        db.add_all(users.values())
        db.flush()
        for company in companies:
            admin_role = Role(
                id=stable_id(f"{company.code}:role:admin"),
                company_id=company.id,
                name="Administrator",
                system=True,
            )
            preparer_role = Role(
                id=stable_id(f"{company.code}:role:preparer"),
                company_id=company.id,
                name="Preparer",
                system=True,
            )
            approver_role = Role(
                id=stable_id(f"{company.code}:role:approver"),
                company_id=company.id,
                name="Approver",
                system=True,
            )
            db.add_all([admin_role, preparer_role, approver_role])
            db.flush()
            db.add(
                Membership(company_id=company.id, user_id=users["admin"].id, role_id=admin_role.id)
            )
            if company.code != "EDGE":
                db.add(
                    Membership(
                        company_id=company.id,
                        user_id=users["preparer"].id,
                        role_id=preparer_role.id,
                    )
                )
                db.add(
                    Membership(
                        company_id=company.id,
                        user_id=users["approver"].id,
                        role_id=approver_role.id,
                    )
                )
            for code, _, _ in CAPABILITIES:
                db.add(
                    RolePermission(
                        company_id=company.id, role_id=admin_role.id, permission_code=code
                    )
                )
            for code in (
                "accounts.view",
                "fiscal.view",
                "journals.create",
                "journals.update",
                "journals.view",
                "journals.validate",
                "journals.inquire",
                "reports.run",
            ):
                db.add(
                    RolePermission(
                        company_id=company.id, role_id=preparer_role.id, permission_code=code
                    )
                )
            for code in (
                "accounts.view",
                "fiscal.view",
                "journals.view",
                "journals.approve",
                "journals.post",
                "journals.reverse",
                "journals.inquire",
                "reports.run",
                "integrity.run",
            ):
                db.add(
                    RolePermission(
                        company_id=company.id, role_id=approver_role.id, permission_code=code
                    )
                )
            periods = 12 if company.code == "ACME" else 18
            add_calendar(db, company, "FY2026", date(2026, 1, 1), periods)
            add_calendar(
                db,
                company,
                "FY2027",
                date(2026, 1, 1) + timedelta(days=periods * 28),
                periods,
            )
            account_specs = [
                (
                    "1000",
                    "Cash at Bank",
                    AccountType.BALANCE_SHEET,
                    company.base_currency_code,
                    True,
                ),
                (
                    "1100",
                    "Trade Receivables",
                    AccountType.BALANCE_SHEET,
                    company.base_currency_code,
                    True,
                ),
                (
                    "2000",
                    "Trade Payables",
                    AccountType.BALANCE_SHEET,
                    company.base_currency_code,
                    True,
                ),
                (
                    "3000",
                    "Retained Earnings",
                    AccountType.RETAINED_EARNINGS,
                    company.base_currency_code,
                    True,
                ),
                ("4000", "Revenue", AccountType.REVENUE_EXPENSE, company.base_currency_code, True),
                (
                    "5000",
                    "Operating Expenses",
                    AccountType.REVENUE_EXPENSE,
                    company.base_currency_code,
                    True,
                ),
                (
                    "9000",
                    "STATEMENT OF PROFIT OR LOSS",
                    AccountType.TITLE,
                    company.base_currency_code,
                    False,
                ),
                ("6100", "Foreign Currency Expense", AccountType.REVENUE_EXPENSE, "EUR", True),
            ]
            for code, name, account_type, currency, postable in account_specs:
                db.add(
                    Account(
                        id=stable_id(f"{company.code}:account:{code}"),
                        company_id=company.id,
                        code=code,
                        name=name,
                        account_type=account_type,
                        currency_code=currency,
                        postable=postable,
                    )
                )
        db.commit()
        add_deterministic_accounting_cycle(db, companies[2], users["admin"])
        print("Seeded deterministic demo companies, users, and accounting cycles")


if __name__ == "__main__":
    seed()
