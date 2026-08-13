import { FormEvent, useMemo, useState } from "react";
import { api } from "./api";
import {
  Badge,
  Banner,
  Button,
  Field,
  Input,
  StatusPill,
} from "./design-system";
import type { CompanyAccess, FiscalYear, Period } from "./types";

type DraftPeriod = {
  period_no: number;
  label: string;
  start_date: string;
  end_date: string;
};

function addDays(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function initialStart(years: FiscalYear[]): string {
  const last = [...years]
    .sort((left, right) => left.end_date.localeCompare(right.end_date))
    .at(-1);
  return last
    ? addDays(last.end_date, 1)
    : `${new Date().getUTCFullYear()}-01-01`;
}

export function FiscalCalendarManager({
  token,
  company,
  years,
  periods,
  canManage,
  onChanged,
}: {
  token: string;
  company: CompanyAccess;
  years: FiscalYear[];
  periods: Period[];
  canManage: boolean;
  onChanged: () => Promise<void>;
}) {
  const defaultStart = useMemo(() => initialStart(years), [years]);
  const [label, setLabel] = useState(`FY${defaultStart.slice(0, 4)}`);
  const [start, setStart] = useState(defaultStart);
  const [count, setCount] = useState(13);
  const [days, setDays] = useState(28);
  const [draft, setDraft] = useState<DraftPeriod[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  function generate() {
    setDraft(
      Array.from({ length: count }, (_, index) => {
        const periodStart = addDays(start, index * days);
        return {
          period_no: index + 1,
          label: `P${String(index + 1).padStart(2, "0")}`,
          start_date: periodStart,
          end_date: addDays(periodStart, days - 1),
        };
      }),
    );
    setMessage(
      "Period boundaries generated; review and edit every date before saving.",
    );
  }

  function edit(index: number, field: keyof DraftPeriod, value: string) {
    setDraft((current) =>
      current.map((period, position) =>
        position === index
          ? {
              ...period,
              [field]: field === "period_no" ? Number(value) : value,
            }
          : period,
      ),
    );
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!draft.length) return;
    setBusy(true);
    setMessage("");
    try {
      await api(
        "/fiscal/years",
        {
          method: "POST",
          body: JSON.stringify({
            label,
            start_date: draft[0].start_date,
            end_date: draft.at(-1)?.end_date,
            periods: draft,
          }),
        },
        token,
        company.id,
      );
      setDraft([]);
      setMessage(`${label} created with ${count} validated periods.`);
      await onChanged();
    } catch (caught) {
      setMessage(
        caught instanceof Error
          ? caught.message
          : "Fiscal calendar could not be created",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">FISCAL CALENDAR</p>
            <h2>{periods.length} periods</h2>
          </div>
          <Badge>Up to 18 supported</Badge>
        </div>
        <div className="table-wrap">
          <table>
            <caption className="ds-visually-hidden">
              Fiscal periods for {company.name}
            </caption>
            <thead>
              <tr>
                <th>Period</th>
                <th>Start</th>
                <th>End</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {periods.map((period) => (
                <tr key={period.id}>
                  <td>
                    {period.period_no} · {period.label}
                  </td>
                  <td>{period.start_date}</td>
                  <td>{period.end_date}</td>
                  <td>
                    <StatusPill
                      status={period.status === "open" ? "open" : "closed"}
                      label={period.status.replaceAll("_", " ")}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {canManage ? (
        <section className="panel fiscal-builder">
          <div>
            <p className="eyebrow">CONFIGURABLE 1–18 PERIODS</p>
            <h2>New fiscal year</h2>
          </div>
          <div className="fiscal-generate">
            <Field label="Year label" htmlFor="fiscal-year-label">
              <Input
                value={label}
                onChange={(event) => setLabel(event.target.value)}
              />
            </Field>
            <Field label="First day" htmlFor="fiscal-start">
              <Input
                type="date"
                value={start}
                onChange={(event) => setStart(event.target.value)}
              />
            </Field>
            <Field label="Periods" htmlFor="fiscal-count">
              <Input
                numeric
                type="number"
                min={1}
                max={18}
                value={count}
                onChange={(event) => setCount(Number(event.target.value))}
              />
            </Field>
            <Field label="Days per period" htmlFor="fiscal-days">
              <Input
                numeric
                type="number"
                min={1}
                max={366}
                value={days}
                onChange={(event) => setDays(Number(event.target.value))}
              />
            </Field>
            <Button
              disabled={!label || !start || count < 1 || count > 18 || days < 1}
              onClick={generate}
            >
              Generate boundaries
            </Button>
          </div>
          {draft.length ? (
            <form onSubmit={save}>
              <div className="table-wrap">
                <table>
                  <caption className="ds-visually-hidden">
                    Draft fiscal period boundaries
                  </caption>
                  <thead>
                    <tr>
                      <th>No.</th>
                      <th>Label</th>
                      <th>Start</th>
                      <th>End</th>
                    </tr>
                  </thead>
                  <tbody>
                    {draft.map((period, index) => (
                      <tr key={period.period_no}>
                        <td>{period.period_no}</td>
                        <td>
                          <Input
                            aria-label={`Label for period ${period.period_no}`}
                            value={period.label}
                            onChange={(event) =>
                              edit(index, "label", event.target.value)
                            }
                          />
                        </td>
                        <td>
                          <Input
                            aria-label={`Start for period ${period.period_no}`}
                            type="date"
                            value={period.start_date}
                            onChange={(event) =>
                              edit(index, "start_date", event.target.value)
                            }
                          />
                        </td>
                        <td>
                          <Input
                            aria-label={`End for period ${period.period_no}`}
                            type="date"
                            value={period.end_date}
                            onChange={(event) =>
                              edit(index, "end_date", event.target.value)
                            }
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Button type="submit" variant="primary" busy={busy}>
                Save fiscal year
              </Button>
            </form>
          ) : null}
          {message ? (
            <Banner tone={message.includes("could not") ? "danger" : "success"}>
              {message}
            </Banner>
          ) : null}
        </section>
      ) : null}
    </>
  );
}
