import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import {
  Banner,
  Button,
  Checkbox,
  Field,
  Input,
  Select,
  Switch,
} from "./design-system";
import type {
  AdminRole,
  CompanyAccess,
  CompanySettings,
  Permission,
} from "./types";

export function AdministrationSettings({
  token,
  company,
  capabilities,
}: {
  token: string;
  company: CompanyAccess;
  capabilities: Set<string>;
}) {
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [roleId, setRoleId] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const canCompany = capabilities.has("company.manage");
  const canUsers = capabilities.has("users.manage");

  const load = useCallback(async () => {
    const [nextSettings, nextRoles, nextPermissions] = await Promise.all([
      canCompany
        ? api<CompanySettings>("/administration/company", {}, token, company.id)
        : Promise.resolve(null),
      canUsers
        ? api<AdminRole[]>("/administration/roles", {}, token, company.id)
        : Promise.resolve([]),
      canUsers
        ? api<Permission[]>(
            "/administration/permissions",
            {},
            token,
            company.id,
          )
        : Promise.resolve([]),
    ]);
    setSettings(nextSettings);
    setRoles(nextRoles);
    setPermissions(nextPermissions);
  }, [canCompany, canUsers, company.id, token]);

  useEffect(() => {
    const handle = window.setTimeout(
      () =>
        void load().catch((caught: unknown) =>
          setMessage(
            caught instanceof Error
              ? caught.message
              : "Settings could not be loaded",
          ),
        ),
      0,
    );
    return () => window.clearTimeout(handle);
  }, [load]);

  async function chooseRole(nextRoleId: string) {
    setRoleId(nextRoleId);
    if (!nextRoleId) {
      setSelected(new Set());
      return;
    }
    const result = await api<{ permissions: string[] }>(
      `/administration/roles/${nextRoleId}/permissions`,
      {},
      token,
      company.id,
    );
    setSelected(new Set(result.permissions));
  }

  async function saveCompany(event: FormEvent) {
    event.preventDefault();
    if (!settings) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await api<CompanySettings>(
        "/administration/company",
        {
          method: "PUT",
          body: JSON.stringify({
            name: settings.name,
            timezone: settings.timezone,
            rounding_places: settings.rounding_places,
            use_bankers_rounding: settings.use_bankers_rounding,
          }),
        },
        token,
        company.id,
      );
      setSettings(result);
      setMessage(
        "Company presentation and rounding controls saved with audit evidence.",
      );
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Company settings could not be saved",
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveRole() {
    if (!roleId) return;
    setBusy(true);
    setMessage("");
    try {
      await api(
        `/administration/roles/${roleId}/permissions`,
        {
          method: "PUT",
          body: JSON.stringify({ permissions: [...selected].sort() }),
        },
        token,
        company.id,
      );
      setMessage(
        "Role capabilities replaced atomically and recorded in the audit trail.",
      );
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Role capabilities could not be saved",
      );
    } finally {
      setBusy(false);
    }
  }

  function toggle(code: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  if (!canCompany && !canUsers) return null;
  return (
    <section className="panel administration-settings">
      <div>
        <p className="eyebrow">GOVERNED CONFIGURATION</p>
        <h2>Company and capabilities</h2>
      </div>
      {settings ? (
        <form className="company-settings" onSubmit={saveCompany}>
          <Field label="Company name" htmlFor="company-name">
            <Input
              value={settings.name}
              onChange={(event) =>
                setSettings({ ...settings, name: event.target.value })
              }
            />
          </Field>
          <Field label="IANA timezone" htmlFor="company-timezone">
            <Input
              value={settings.timezone}
              onChange={(event) =>
                setSettings({ ...settings, timezone: event.target.value })
              }
            />
          </Field>
          <Field label="Rounding places" htmlFor="rounding-places">
            <Input
              numeric
              type="number"
              min={0}
              max={6}
              value={settings.rounding_places}
              onChange={(event) =>
                setSettings({
                  ...settings,
                  rounding_places: Number(event.target.value),
                })
              }
            />
          </Field>
          <Switch
            checked={settings.use_bankers_rounding}
            onChange={(event) =>
              setSettings({
                ...settings,
                use_bankers_rounding: event.target.checked,
              })
            }
            label="Bankers rounding"
          />
          <Button type="submit" busy={busy}>
            Save company settings
          </Button>
        </form>
      ) : null}
      {canUsers ? (
        <div className="capability-editor">
          <Field label="Role to configure" htmlFor="role-configure">
            <Select
              aria-label="Role to configure"
              value={roleId}
              onChange={(event) => void chooseRole(event.target.value)}
            >
              <option value="">Choose a role</option>
              {roles.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.name}
                  {role.system ? " · system" : ""}
                </option>
              ))}
            </Select>
          </Field>
          {roleId ? (
            <fieldset>
              <legend>Granted capabilities</legend>
              {permissions.map((permission) => (
                <Checkbox
                  key={permission.code}
                  title={permission.description}
                  checked={selected.has(permission.code)}
                  onChange={() => toggle(permission.code)}
                  label={permission.code}
                  description={permission.description}
                />
              ))}
            </fieldset>
          ) : null}
          {roleId ? (
            <Button
              variant="primary"
              busy={busy}
              onClick={() => void saveRole()}
            >
              Save role capabilities
            </Button>
          ) : null}
        </div>
      ) : null}
      {message ? (
        <Banner tone={message.includes("could not") ? "danger" : "success"}>
          {message}
        </Banner>
      ) : null}
    </section>
  );
}
