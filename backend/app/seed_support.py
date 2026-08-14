import uuid

NAMESPACE = uuid.UUID("58987ab5-ebf4-47c8-80ed-bf1d894a8040")


def stable_id(name: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, name)


CAPABILITIES = [
    ("accounts.create", "Create accounts", 1),
    ("accounts.update", "Modify accounts", 2),
    ("accounts.delete", "Deactivate unused accounts", 3),
    ("accounts.view", "View chart and account inquiry", 4),
    ("journals.inquire", "View posted transactions", 5),
    ("budgets.manage", "Compare and edit budgets", 6),
    ("accounts.import", "Import accounts", 7),
    ("journals.create", "Create journal batches", 8),
    ("journals.update", "Modify draft batches", 9),
    ("journals.import", "Import journal batches", 10),
    ("journals.delete", "Delete draft batches", 11),
    ("journals.view", "Browse journal batches", 12),
    ("journals.post", "Post approved journals", 13),
    ("reports.saved", "View saved report runs", 14),
    ("reports.chart", "Run chart of accounts", 15),
    ("reports.trial_balance", "Run trial balance", 16),
    ("reports.gl", "Run general ledger report", 17),
    ("reports.groups", "Run journal group reports", 18),
    ("reports.custom.run", "Run custom reports", 19),
    ("reports.custom.design", "Design custom reports", 20),
    ("fiscal.close", "Close and reopen fiscal years", 21),
    ("integrity.run", "Run integrity and reconciliation checks", 22),
    ("administration.organize", "Run maintenance jobs", 23),
    ("migration.run", "Run legacy migration tools", 24),
    ("company.manage", "Manage company options", 25),
    ("users.manage", "Manage users and roles", 26),
    ("preferences.manage", "Manage display preferences", 27),
    ("audit.view", "View audit and operation history", 28),
    ("fiscal.view", "View fiscal calendars", None),
    ("fiscal.manage", "Manage fiscal calendars", None),
    ("journals.validate", "Validate journal batches", None),
    ("journals.approve", "Approve journal batches", None),
    ("journals.self_approve", "Allow controlled self approval", None),
    ("journals.reverse", "Reverse posted journal entries", None),
    ("reports.run", "Run standard reports", None),
]
