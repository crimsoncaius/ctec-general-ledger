import React from "react";
import { Button } from "../../components/core/Button.jsx";
import { Field } from "../../components/forms/Field.jsx";
import { Input } from "../../components/forms/Input.jsx";
import { Banner } from "../../components/feedback/Banner.jsx";

export function SignIn({ onSignIn, state = "idle" }) {
  const [email, setEmail] = React.useState("a.mensah@northstar.example");
  return (
    <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "minmax(0,1fr) 420px", background: "var(--surface-page)" }}>
      <section style={{ background: "var(--surface-header)", padding: "var(--space-12) var(--space-11)", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <span style={{ font: "var(--weight-semibold) var(--text-xl)/1 var(--font-sans)", letterSpacing: "0.04em", color: "var(--text-inverse)" }}>
          CTec <span style={{ color: "var(--blue-300)" }}>Ledger</span>
        </span>
        <div style={{ maxWidth: "40ch", display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
          <h1 style={{ font: "var(--type-display)", color: "var(--text-inverse)", letterSpacing: "var(--tracking-tight)" }}>
            Financial truth, with a trail behind it.
          </h1>
          <p style={{ font: "var(--type-body)", color: "var(--n-300)" }}>
            Every posting, close and migration in this ledger records who acted, what changed, and whether it reconciled.
          </p>
        </div>
        <p style={{ font: "var(--type-caption)", color: "var(--n-500)" }}>Access is scoped to your company memberships.</p>
      </section>
      <section style={{ background: "var(--surface-card)", padding: "var(--space-11) var(--space-9)", display: "flex", flexDirection: "column", justifyContent: "center", gap: "var(--stack-gap)", borderLeft: "1px solid var(--border-hairline)" }}>
        <div>
          <h2 style={{ font: "var(--type-h2)" }}>Sign in</h2>
          <p style={{ font: "var(--type-caption)", color: "var(--text-muted)", marginTop: "var(--space-3)" }}>Your workspace opens once memberships have loaded.</p>
        </div>
        {state === "invalid" && (
          <Banner tone="danger" title="Sign-in failed">Those credentials are not valid. Check the email address and password and try again.</Banner>
        )}
        {state === "locked" && (
          <Banner tone="warning" title="Temporarily locked">Too many failed attempts. Sign-in is unavailable for 15 minutes.</Banner>
        )}
        {state === "no-company" && (
          <Banner tone="info" title="No company access" actions={<Button size="sm" variant="secondary">Sign out</Button>}>
            Your account is authenticated but has no active company membership. An administrator must grant one.
          </Banner>
        )}
        <form
          onSubmit={(e) => { e.preventDefault(); onSignIn && onSignIn(); }}
          style={{ display: "flex", flexDirection: "column", gap: "var(--field-gap)" }}
        >
          <Field label="Email" htmlFor="email" required>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </Field>
          <Field label="Password" htmlFor="password" required>
            <Input type="password" defaultValue="hunter22hunter" autoComplete="current-password" />
          </Field>
          <Button variant="primary" size="lg" fullWidth busy={state === "pending"} onClick={() => onSignIn && onSignIn()}>
            {state === "pending" ? "Signing in" : "Sign in"}
          </Button>
        </form>
        <p style={{ font: "var(--type-caption)", color: "var(--text-muted)" }}>
          Credentials are never stored in this browser session.
        </p>
      </section>
    </div>
  );
}
