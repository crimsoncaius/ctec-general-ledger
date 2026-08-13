import React from "react";
import { AppShell } from "./AppShell.jsx";
import { SignIn } from "./SignIn.jsx";
import { OverviewScreen } from "./OverviewScreen.jsx";
import { JournalsScreen } from "./JournalsScreen.jsx";
import { InquiryScreen } from "./InquiryScreen.jsx";
import { CloseScreen } from "./CloseScreen.jsx";
import { ReportsScreen } from "./ReportsScreen.jsx";
import { MigrationScreen } from "./MigrationScreen.jsx";
import { PageHeader } from "../../components/navigation/PageHeader.jsx";
import { Card } from "../../components/core/Card.jsx";
import { Banner } from "../../components/feedback/Banner.jsx";
import { EmptyState } from "../../components/feedback/EmptyState.jsx";

const REFERENCE_PLACEHOLDERS = {
  accounts: { title: "Chart of accounts", eyebrow: "Books", section: "4.3" },
  fiscal: { title: "Fiscal calendar", eyebrow: "Books", section: "4.6" },
  designer: { title: "Custom report designer", eyebrow: "Output", section: "4.9" },
  admin: { title: "Administration", eyebrow: "Company", section: "4.10" },
};

function ReferencePlaceholder({ id }) {
  const item = REFERENCE_PLACEHOLDERS[id];
  return (
    <>
      <PageHeader
        eyebrow={item.eyebrow}
        title={item.title}
        meta={<>Reference coverage · frontend design brief §{item.section}</>}
        dataState="current"
      />
      <Banner tone="info" title="Specified but not prototyped" style={{ marginBottom: "var(--stack-gap)" }}>
        This destination remains part of the approved product scope. Its functional requirements are recorded
        in the canonical frontend design brief, but this first-pass click-through does not implement the screen.
      </Banner>
      <Card>
        <EmptyState
          kind="no-data"
          icon="file-clock"
          title="Reference screen pending"
          description="Use the design-system components and the linked brief section when this workspace is designed."
        />
      </Card>
    </>
  );
}

const ROLES = {
  Administrator: {
    user: "A. Mensah",
    caps: ["journals.view","journals.create","journals.update","journals.validate","journals.approve","journals.post","journals.inquire","journals.reverse","accounts.view","accounts.update","fiscal.view","fiscal.close","integrity.run","reports.run","reports.custom.design","company.manage","migration.run"],
  },
  Preparer: {
    user: "L. Osei",
    caps: ["journals.view","journals.create","journals.update","journals.validate","journals.inquire","accounts.view","fiscal.view","reports.run"],
  },
  Approver: {
    user: "R. Vance",
    caps: ["journals.view","journals.approve","journals.post","journals.inquire","journals.reverse","accounts.view","fiscal.view","fiscal.close","integrity.run","reports.run"],
  },
  "Restricted viewer": {
    user: "T. Iqbal",
    caps: ["journals.view","journals.inquire","accounts.view","fiscal.view"],
  },
};

const MEMBERSHIPS = [
  { company: "Northstar Manufacturing", code: "NORTHSTAR-01", role: "Approver" },
  { company: "Harbour Logistics", code: "HARBOUR-02", role: "Preparer" },
];

function App() {
  const [signedIn, setSignedIn] = React.useState(false);
  const [role, setRole] = React.useState("Administrator");
  const [screen, setScreen] = React.useState("overview");
  const [density, setDensity] = React.useState("comfortable");
  const [company, setCompany] = React.useState(MEMBERSHIPS[0]);
  const caps = ROLES[role].caps;

  if (!signedIn) return <SignIn onSignIn={() => setSignedIn(true)} />;

  const screens = {
    overview: <OverviewScreen capabilities={caps} onGo={setScreen} />,
    accounts: <ReferencePlaceholder id="accounts" />,
    fiscal: <ReferencePlaceholder id="fiscal" />,
    journals: <JournalsScreen capabilities={caps} user={ROLES[role].user} onGo={setScreen} />,
    inquiry: <InquiryScreen capabilities={caps} />,
    close: <CloseScreen capabilities={caps} />,
    reports: <ReportsScreen capabilities={caps} />,
    designer: <ReferencePlaceholder id="designer" />,
    admin: <ReferencePlaceholder id="admin" />,
    migration: <MigrationScreen capabilities={caps} />,
  };

  const available = Object.keys(screens);
  const current = available.includes(screen) ? screen : "overview";

  return (
    <>
      <div style={{ position: "fixed", right: 12, bottom: 12, zIndex: 80, display: "flex", alignItems: "center", gap: 8, background: "var(--surface-raised)", boxShadow: "var(--shadow-menu)", borderRadius: "var(--radius-md)", padding: "6px 10px" }}>
        <span style={{ font: "var(--type-overline)", letterSpacing: "var(--tracking-caps)", textTransform: "uppercase", color: "var(--text-muted)" }}>Capability set</span>
        <select
          value={role}
          onChange={(e) => { setRole(e.target.value); setScreen("overview"); }}
          style={{ height: 26, font: "var(--type-body-sm)", border: "1px solid var(--border-input)", borderRadius: "var(--radius-sm)", padding: "0 6px", background: "var(--surface-card)" }}
        >
          {Object.keys(ROLES).map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>
      <AppShell
        user={ROLES[role].user}
        company={company.company}
        code={company.code}
        role={role}
        capabilities={caps}
        memberships={MEMBERSHIPS}
        activeId={current}
        onNavigate={setScreen}
        onSwitch={(m) => { setCompany(m); setScreen("overview"); }}
        density={density}
        onDensity={setDensity}
      >
        {screens[current]}
      </AppShell>
    </>
  );
}

window.__CTecApp = App;
