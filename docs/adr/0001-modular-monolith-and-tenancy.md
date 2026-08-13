# ADR 0001: Modular monolith and explicit tenant keys

Status: accepted

The initial system is one FastAPI codebase split into domain modules, one React
frontend, PostgreSQL, and a separately runnable worker process. This keeps
transactions and accounting invariants inside one deployable boundary while
preserving seams for later extraction.

Every company-owned table includes `company_id`. Relationships use composite
foreign keys containing `company_id`, and API queries always receive company
context from an authenticated membership. PostgreSQL row-level security is a
defense-in-depth production option, but application correctness does not depend on
session state that can be accidentally omitted.

