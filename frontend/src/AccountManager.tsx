import { FormEvent, useState } from "react";
import { api } from "./api";
import {
  Badge,
  Banner,
  Button,
  Field,
  Input,
  Select,
  Switch,
} from "./design-system";
import type { Account, CompanyAccess } from "./types";

type Props = {
  accounts: Account[];
  company: CompanyAccess;
  capabilities: Set<string>;
  token: string;
  onChanged: () => Promise<void>;
};

function AccountRow({
  account,
  canUpdate,
  busy,
  onSave,
}: {
  account: Account;
  canUpdate: boolean;
  busy: boolean;
  onSave: (
    account: Account,
    name: string,
    postable: boolean,
    active: boolean,
  ) => Promise<void>;
}) {
  const [name, setName] = useState(account.name);
  const [postable, setPostable] = useState(account.postable);
  const [active, setActive] = useState(account.active);
  const changed =
    name !== account.name ||
    postable !== account.postable ||
    active !== account.active;
  return (
    <tr>
      <td className="mono">{account.code}</td>
      <td>
        {canUpdate ? (
          <Input
            aria-label={`Name for ${account.code}`}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        ) : (
          account.name
        )}
      </td>
      <td>{account.account_type.replaceAll("_", " ")}</td>
      <td>{account.currency_code}</td>
      <td>
        {canUpdate ? (
          <Switch
            checked={postable}
            disabled={account.account_type === "title"}
            onChange={(event) => setPostable(event.target.checked)}
            label="Postable"
          />
        ) : account.postable ? (
          "Postable"
        ) : (
          "Title"
        )}
      </td>
      <td>
        {canUpdate ? (
          <Switch
            checked={active}
            disabled={account.account_type === "retained_earnings"}
            onChange={(event) => setActive(event.target.checked)}
            label="Active"
          />
        ) : (
          <Badge tone={account.active ? "success" : "neutral"}>
            {account.active ? "Active" : "Inactive"}
          </Badge>
        )}
      </td>
      <td>
        {canUpdate ? (
          <Button
            size="sm"
            disabled={busy || !changed || !name.trim()}
            onClick={() => void onSave(account, name, postable, active)}
          >
            Save
          </Button>
        ) : null}
      </td>
    </tr>
  );
}

export function AccountManager({
  accounts,
  company,
  capabilities,
  token,
  onChanged,
}: Props) {
  const canCreate = capabilities.has("accounts.create");
  const canUpdate = capabilities.has("accounts.update");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState("balance_sheet");
  const [currency, setCurrency] = useState(company.base_currency_code);
  const [postable, setPostable] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api(
        "/accounts",
        {
          method: "POST",
          body: JSON.stringify({
            code,
            name,
            account_type: accountType,
            currency_code: currency.toUpperCase(),
            postable: accountType === "title" ? false : postable,
          }),
        },
        token,
        company.id,
      );
      setCode("");
      setName("");
      setMessage("Account created with company-scoped audit evidence.");
      await onChanged();
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Account could not be created",
      );
    } finally {
      setBusy(false);
    }
  }

  async function update(
    account: Account,
    nextName: string,
    nextPostable: boolean,
    active: boolean,
  ) {
    setBusy(true);
    setMessage("");
    try {
      await api(
        `/accounts/${account.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            name: nextName,
            postable: nextPostable,
            active,
          }),
        },
        token,
        company.id,
      );
      setMessage(
        `Account ${account.code} updated. Posted history remains immutable.`,
      );
      await onChanged();
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Account could not be updated",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel account-manager">
      <div className="section-heading">
        <div>
          <p className="eyebrow">CHART OF ACCOUNTS</p>
          <h2>{accounts.length} accounts</h2>
        </div>
        <Badge tone="success" mono>
          {company.base_currency_code} base
        </Badge>
      </div>
      {canCreate ? (
        <form className="account-create" onSubmit={create}>
          <Field label="Account code" htmlFor="account-code" immutable required>
            <Input
              value={code}
              maxLength={30}
              onChange={(event) => setCode(event.target.value)}
              required
            />
          </Field>
          <Field label="Account name" htmlFor="account-name" required>
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </Field>
          <Field label="Type" htmlFor="account-type" immutable>
            <Select
              value={accountType}
              onChange={(event) => {
                setAccountType(event.target.value);
                if (event.target.value === "title") setPostable(false);
              }}
            >
              <option value="balance_sheet">Balance sheet</option>
              <option value="revenue_expense">Revenue / expense</option>
              <option value="retained_earnings">Retained earnings</option>
              <option value="title">Title</option>
            </Select>
          </Field>
          <Field label="Currency" htmlFor="account-currency" immutable required>
            <Input
              aria-label="Account currency"
              value={currency}
              minLength={3}
              maxLength={3}
              onChange={(event) =>
                setCurrency(event.target.value.toUpperCase())
              }
              required
            />
          </Field>
          <Switch
            checked={postable}
            disabled={accountType === "title"}
            onChange={(event) => setPostable(event.target.checked)}
            label="Postable"
          />
          <Button type="submit" variant="primary" busy={busy}>
            Create account
          </Button>
        </form>
      ) : null}
      {message ? (
        <Banner tone={message.includes("could not") ? "danger" : "success"}>
          {message}
        </Banner>
      ) : null}
      <div className="table-wrap">
        <table>
          <caption className="ds-visually-hidden">
            Chart of accounts for {company.name}
          </caption>
          <thead>
            <tr>
              <th>Code</th>
              <th>Account</th>
              <th>Type</th>
              <th>Currency</th>
              <th>Posting</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((account) => (
              <AccountRow
                key={`${account.id}:${account.name}:${account.active}:${account.postable}`}
                account={account}
                canUpdate={canUpdate}
                busy={busy}
                onSave={update}
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
