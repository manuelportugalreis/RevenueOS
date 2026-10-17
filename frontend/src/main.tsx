import React, {
  Component,
  useEffect,
  useState,
  useRef,
  type ReactNode,
} from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import focused from "../../data/dashboard/focused-evaluation.json";

const SHOWCASE = import.meta.env.MODE === "showcase";

type Session = { csrf: string; reviewer: boolean; mode: string };
type Score = {
  lead_id: string;
  points: number;
  components: Record<string, number>;
  warnings: string[];
  evidence: { source: string; employee_band: string };
};
type Dashboard = {
  metrics: {
    observed_at: string;
    dataset_id: string;
    dataset_version: number;
    interval: { start_inclusive: string; end_exclusive: string };
    leads: {
      inbound_leads: number;
      qualification_rate: number | null;
      qualified_30d: number;
      qualification_denominator: number;
      no_recorded_response: number;
    };
    opportunities: {
      win_rate: number | null;
      won: number;
      closed_denominator: number;
    };
    open_pipeline_by_currency: {
      currency: string;
      amount: string;
      opportunity_count: number;
    }[];
    import_quality: {
      accepted_count: number;
      quarantined_count: number;
      duplicate_count: number;
    };
  };
  priorities: Score[];
  recommendations: {
    id: string;
    state: string;
    failure_code: string | null;
    created_at: string;
  }[];
  actions: { id: string; state: string; current_version: number }[];
  costs: {
    cost_basis: string;
    state: string;
    attempts: number;
    estimated_cost_usd: string | null;
  }[];
  evaluation: {
    recorded_at: string;
    source_sha256: string;
    retrieval_comparison: Record<
      string,
      { recall_at_5: number; p95_latency_ms: number }
    >;
    recommendation_comparison: Record<
      string,
      {
        false_abstentions: number;
        false_abstention_rate: number;
        p95_latency_ms: number;
      }
    >;
  } | null;
};
type Claim = { text: string; evidence_id: string };
type Recommendation = {
  recommendation: {
    action: string;
    abstention_reason: string | null;
    rationale_claims: Claim[];
    draft: {
      subject: string;
      opening: string;
      claims: Claim[];
      closing: string;
    } | null;
  };
};
type Action = {
  action_id: string;
  version: number;
  state: string;
  payload_hash: string;
  expires_at: string;
  payload: {
    recipient: string;
    subject: string;
    body: string;
    evidence_ids: string[];
  };
};
type Citation = {
  title: string;
  version: number;
  heading: string;
  start_offset: number;
  end_offset: number;
  text: string;
};

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
async function api<T>(
  path: string,
  session?: Session,
  body?: unknown,
  requestKey?: string,
): Promise<T> {
  if (SHOWCASE)
    return (await (await import("./publicReplay")).replay(path, body)) as T;
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(session ? { "X-CSRF-Token": session.csrf } : {}),
      ...(requestKey ? { "Idempotency-Key": requestKey } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    credentials: "same-origin",
  });
  const value = await response.json();
  if (!response.ok)
    throw new ApiError(
      response.status,
      `${String(value.error?.code ?? "Request failed").replaceAll("_", " ")} · Reference ${value.error?.request_id ?? response.status}`,
    );
  return value as T;
}
const percent = (v: number | null) =>
  v === null
    ? "Unavailable"
    : new Intl.NumberFormat("en", {
        style: "percent",
        maximumFractionDigits: 1,
      }).format(v);
const date = (v: string) =>
  new Date(v).toLocaleString("en", {
    timeZone: "UTC",
    dateStyle: "medium",
    timeStyle: "short",
  }) + " UTC";
const money = (v: string, currency: string) =>
  new Intl.NumberFormat("en", { style: "currency", currency }).format(
    Number(v),
  );
const label = (v: string) => v.replaceAll("_", " ");

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main>
        <h1>RevenueOS could not display this view</h1>
        <p>Reload to recover. No approval was submitted by this error.</p>
        <button onClick={() => location.reload()}>Reload</button>
      </main>
    ) : (
      this.props.children
    );
  }
}

function App() {
  const [session, setSession] = useState<Session | null>(null),
    [boot, setBoot] = useState(true),
    [mode, setMode] = useState("local");
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [data, setData] = useState<Dashboard | null>(null);
  const [tab, setTab] = useState("Overview"),
    [selected, setSelected] = useState<Score | null>(null),
    [draft, setDraft] = useState<Recommendation | null>(null),
    [action, setAction] = useState<Action | null>(null),
    [citation, setCitation] = useState<Citation | null>(null);
  const [query, setQuery] = useState("configuration checklist"),
    [notice, setNotice] = useState(""),
    [start, setStart] = useState(""),
    [end, setEnd] = useState("");
  const workflowRequest = useRef<{ signature: string; key: string } | null>(
    null,
  );
  const fail = (e: unknown) => {
    setError(
      e instanceof Error ? e.message : "Service unavailable. Try again.",
    );
    if (e instanceof ApiError && e.status === 401) {
      setSession(null);
      setData(null);
      setAction(null);
      setDraft(null);
      setCitation(null);
      setSelected(null);
      workflowRequest.current = null;
    }
  };
  useEffect(() => {
    let active = true;
    Promise.all([
      api<{ mode: string }>("/api/auth/config"),
      api<Session>("/api/session").catch((e) => {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }),
    ])
      .then(([config, s]) => {
        if (active) {
          setMode(config.mode);
          setSession(s);
        }
      })
      .catch((e) => {
        if (active) fail(e);
      })
      .finally(() => {
        if (active) setBoot(false);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!session) return;
    let active = true;
    setBusy(true);
    api<Dashboard>("/api/dashboard")
      .then((v) => {
        if (active) setData(v);
      })
      .catch((e) => {
        if (active) fail(e);
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [session]);
  async function perform(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function refresh() {
    const params =
      start && end
        ? "?" +
          new URLSearchParams({
            start: start + "T00:00:00Z",
            end: end + "T00:00:00Z",
          })
        : "";
    setData(await api<Dashboard>("/api/dashboard" + params));
  }
  async function showCitation(id: string) {
    setCitation(
      await api<Citation>("/api/citations/" + id.replace("doc:", "")),
    );
  }
  if (boot)
    return (
      <main aria-busy="true">
        <h1>RevenueOS</h1>
        <p role="status">Checking your session…</p>
      </main>
    );
  if (!session)
    return (
      <main className="login">
        <div className="brand">
          R<span>RevenueOS</span>
        </div>
        <p className="eyebrow">REVENUE INTELLIGENCE</p>
        <h1>
          Clear priorities.
          <br />
          Evidence behind every action.
        </h1>
        <p>
          Sign in to your approved workspace. This demonstration contains
          synthetic data only.
        </p>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {mode === "google" ? (
          <a className="button" href="/auth/google">
            Continue with Google Workspace
          </a>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const form = new FormData(e.currentTarget);
              void perform(async () => {
                await api("/api/auth/login", undefined, {
                  username: form.get("username"),
                  password: form.get("password"),
                });
                setSession(await api<Session>("/api/session"));
              });
            }}
          >
            <label>
              Username
              <input
                name="username"
                autoComplete="username"
                required
                maxLength={100}
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
                maxLength={256}
              />
            </label>
            <button disabled={busy}>Sign in</button>
            <p className="muted">
              Local synthetic workspace · credentials supplied by your operator
            </p>
          </form>
        )}
      </main>
    );
  const m = data?.metrics;
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          R<span>RevenueOS</span>
        </div>
        <p className="muted">Commercial workspace</p>
        <nav aria-label="Main navigation">
          {[
            "Overview",
            "Lead priorities",
            "Recommendations",
            "Approvals",
            "Evaluation",
          ].map((name) => (
            <button
              key={name}
              aria-current={tab === name ? "page" : undefined}
              onClick={() => {
                setTab(name);
                setError("");
                setNotice("");
              }}
            >
              {name}
            </button>
          ))}
        </nav>
        <div className="aside-bottom">
          <span className="badge">SYNTHETIC DATA</span>
          <p>No external delivery</p>
          <button
            disabled={busy}
            onClick={() =>
              void perform(async () => {
                if (SHOWCASE) {
                  location.reload();
                  return;
                }
                await api("/api/auth/logout", session, {});
                setSession(null);
                setData(null);
                setAction(null);
                setDraft(null);
                setCitation(null);
                setSelected(null);
                workflowRequest.current = null;
              })
            }
          >
            {SHOWCASE ? "Restart walkthrough" : "Sign out"}
          </button>
        </div>
      </aside>
      <main id="main">
        {SHOWCASE && (
          <section
            className="replay-banner"
            aria-label="Public replay disclosure"
          >
            <p className="eyebrow">
              PUBLIC INTERACTIVE REPLAY · SYNTHETIC DATA
            </p>
            <h2>Explore RevenueOS without installing anything</h2>
            <p>
              Recorded API results, not live generation. Decisions below are
              simulated in this browser only. No login, backend request, model
              call or message delivery.
            </p>
            <div className="buttons">
              <button
                disabled={!data || busy}
                onClick={() =>
                  void perform(async () => {
                    const { guidedLead } = await import("./publicReplay");
                    setSelected(
                      data?.priorities.find((p) => p.lead_id === guidedLead) ??
                        null,
                    );
                    setQuery("configuration checklist");
                    setTab("Lead priorities");
                    setDraft(null);
                    setAction(null);
                    setCitation(null);
                  })
                }
              >
                Start guided walkthrough
              </button>
              <button onClick={() => location.reload()}>Reset replay</button>
              <a href="https://github.com/manuelportugalreis/RevenueOS">
                Source and full-stack setup
              </a>
            </div>
          </section>
        )}
        <header>
          <div>
            <p className="eyebrow">REVENUE OPERATIONS / {tab.toUpperCase()}</p>
            <h1>{tab === "Overview" ? "Revenue command center" : tab}</h1>
            <p className="muted">
              A shared view of pipeline, priorities, and accountable decisions.
            </p>
          </div>
          <button disabled={busy} onClick={() => void perform(refresh)}>
            Refresh data
          </button>
        </header>
        <div className="context">
          <span className="badge">Synthetic demonstration</span>
          <span>
            {m ? "Snapshot " + date(m.observed_at) : "No snapshot loaded"}
          </span>
          <span>Human review required</span>
        </div>
        {error && (
          <div className="error" role="alert">
            {error}
            <button onClick={() => void perform(refresh)}>Try again</button>
          </div>
        )}
        {notice && (
          <p className="notice" role="status">
            {notice}
          </p>
        )}
        {busy && <p role="status">Loading or validating your request…</p>}
        {!data && !busy && (
          <section>
            <h2>No data available</h2>
            <p>
              Ask your operator to publish a validated synthetic CRM snapshot,
              then refresh.
            </p>
          </section>
        )}
        {data && m && (
          <>
            {tab === "Overview" && (
              <>
                <form
                  className="filters"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void perform(refresh);
                  }}
                >
                  <label>
                    Cohort from (UTC)
                    <input
                      type="date"
                      value={start}
                      required
                      onChange={(e) => setStart(e.target.value)}
                    />
                  </label>
                  <label>
                    Until, exclusive (UTC)
                    <input
                      type="date"
                      value={end}
                      required
                      onChange={(e) => setEnd(e.target.value)}
                    />
                  </label>
                  <button disabled={busy}>Apply interval</button>
                  <span className="muted">
                    Current: {m.interval.start_inclusive.slice(0, 10)} →{" "}
                    {m.interval.end_exclusive.slice(0, 10)}
                  </span>
                </form>
                <div className="kpis">
                  <Kpi
                    name="Inbound leads"
                    value={String(m.leads.inbound_leads)}
                    detail="Selected acquisition cohort"
                  />
                  <Kpi
                    name="30-day qualification"
                    value={percent(m.leads.qualification_rate)}
                    detail={`${m.leads.qualified_30d} qualified / ${m.leads.qualification_denominator} mature, known outcomes`}
                  />
                  <Kpi
                    name="Closed opportunity win rate"
                    value={percent(m.opportunities.win_rate)}
                    detail={`${m.opportunities.won} won / ${m.opportunities.closed_denominator} closed in interval`}
                  />
                  <Kpi
                    name="Unknown response status"
                    value={String(m.leads.no_recorded_response)}
                    detail="No recorded response; not proof of no contact"
                  />
                </div>
                <div className="grid">
                  <section>
                    <p className="eyebrow">PIPELINE PERFORMANCE</p>
                    <h2>Open pipeline by currency</h2>
                    <p className="muted">
                      At snapshot time; independent of the cohort interval.
                      Currencies are not combined.
                    </p>
                    <table>
                      <caption className="sr-only">
                        Open opportunities at snapshot
                      </caption>
                      <thead>
                        <tr>
                          <th>Currency</th>
                          <th>Pipeline value</th>
                          <th>Opportunities</th>
                        </tr>
                      </thead>
                      <tbody>
                        {m.open_pipeline_by_currency.map((p) => (
                          <tr key={p.currency}>
                            <td>{p.currency}</td>
                            <td className="number">
                              {money(p.amount, p.currency)}
                            </td>
                            <td>{p.opportunity_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!m.open_pipeline_by_currency.length && (
                      <p>No open opportunities in this snapshot.</p>
                    )}
                  </section>
                  <section>
                    <p className="eyebrow">DECISION QUEUE</p>
                    <h2>Where attention is needed</h2>
                    <p>
                      <strong>{data.priorities.length}</strong> top eligible
                      leads shown
                    </p>
                    <p>
                      <strong>
                        {
                          data.actions.filter((a) => a.state === "pending")
                            .length
                        }
                      </strong>{" "}
                      pending approvals in latest 20 visible actions
                    </p>
                    <button onClick={() => setTab("Lead priorities")}>
                      Review lead priorities
                    </button>
                    <p className="muted">
                      Revenue impact and ROI: not measured. No predictive model
                      has been trained.
                    </p>
                  </section>
                </div>
                <section>
                  <h2>Data provenance and quality</h2>
                  <p>
                    Snapshot v{m.dataset_version} · {m.dataset_id}
                  </p>
                  <p>
                    {m.import_quality.accepted_count} accepted records ·{" "}
                    {m.import_quality.quarantined_count} quarantined ·{" "}
                    {m.import_quality.duplicate_count} duplicates
                  </p>
                  <p className="muted">
                    Historical synthetic snapshot. No continuous CRM coverage or
                    live trend is asserted.
                  </p>
                </section>
              </>
            )}
            {tab === "Lead priorities" && (
              <section>
                <h2>Explainable attention queue</h2>
                <p className="muted">
                  Top 20 eligible leads. Points reflect rules, not conversion
                  probabilities.
                </p>
                <table>
                  <caption className="sr-only">Lead priority ranking</caption>
                  <thead>
                    <tr>
                      <th>Lead reference</th>
                      <th>Source</th>
                      <th>Company size</th>
                      <th>Points</th>
                      <th>Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.priorities.map((p, i) => (
                      <tr key={p.lead_id}>
                        <td>
                          {i + 1}. {p.lead_id.slice(0, 8)}
                        </td>
                        <td>{label(p.evidence.source)}</td>
                        <td>{p.evidence.employee_band ?? "Unknown"}</td>
                        <td>
                          <strong>{p.points}</strong>
                        </td>
                        <td>
                          <button
                            onClick={() => {
                              setSelected(p);
                              setDraft(null);
                              setAction(null);
                            }}
                          >
                            Explain lead {i + 1}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!data.priorities.length && <p>No eligible leads.</p>}
                {selected && (
                  <div className="detail">
                    <h3>Why this lead: {selected.lead_id.slice(0, 8)}</h3>
                    <dl>
                      {Object.entries(selected.components).map(([key, val]) => (
                        <React.Fragment key={key}>
                          <dt>{label(key)}</dt>
                          <dd>{val} points</dd>
                        </React.Fragment>
                      ))}
                    </dl>
                    <p className="muted">
                      {selected.warnings.map(label).join("; ")}
                    </p>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        void perform(async () => {
                          const signature = JSON.stringify([
                            selected.lead_id,
                            query,
                          ]);
                          if (workflowRequest.current?.signature !== signature)
                            workflowRequest.current = {
                              signature,
                              key: crypto.randomUUID(),
                            };
                          const result = await api<{
                            state: string;
                            recommendation_id: string | null;
                          }>(
                            "/api/workflows",
                            session,
                            {
                              lead_id: selected.lead_id,
                              query,
                            },
                            workflowRequest.current.key,
                          );
                          workflowRequest.current = null;
                          if (result.recommendation_id)
                            setDraft(
                              await api<Recommendation>(
                                "/api/recommendations/" +
                                  result.recommendation_id,
                              ),
                            );
                          setNotice(
                            "Workflow " +
                              label(result.state) +
                              ". External delivery remains disabled.",
                          );
                          await refresh();
                        });
                      }}
                    >
                      <label>
                        Approved knowledge question
                        <input
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          required
                          maxLength={500}
                        />
                      </label>
                      <button disabled={busy}>
                        {SHOWCASE
                          ? "Replay cited recommendation"
                          : "Prepare cited recommendation"}
                      </button>
                    </form>
                  </div>
                )}
              </section>
            )}
            {tab === "Recommendations" && (
              <section>
                <h2>Your recent recommendations</h2>
                <p className="muted">
                  Latest 20 runs. Opening rechecks expiry, scope, suppression,
                  and sources.
                </p>
                {data.recommendations.length === 0 && (
                  <p>No recommendations yet. Select a lead to prepare one.</p>
                )}
                {data.recommendations.map((r) => (
                  <div className="row" key={r.id}>
                    <span>
                      {date(r.created_at)} · {label(r.state)}
                      {r.failure_code ? " · " + label(r.failure_code) : ""}
                    </span>
                    <button
                      disabled={busy}
                      onClick={() =>
                        void perform(async () =>
                          setDraft(
                            await api<Recommendation>(
                              "/api/recommendations/" + r.id,
                            ),
                          ),
                        )
                      }
                    >
                      Open {r.id.slice(0, 8)}
                    </button>
                  </div>
                ))}
              </section>
            )}
            {draft &&
              (tab === "Recommendations" || tab === "Lead priorities") && (
                <section>
                  <h2>Recommendation: {label(draft.recommendation.action)}</h2>
                  {draft.recommendation.abstention_reason && (
                    <p className="notice">
                      Abstained: {label(draft.recommendation.abstention_reason)}
                      . No outreach prepared.
                    </p>
                  )}
                  {draft.recommendation.rationale_claims.map((c, i) => (
                    <p key={i}>
                      {c.text}{" "}
                      <button
                        onClick={() =>
                          void perform(() => showCitation(c.evidence_id))
                        }
                      >
                        View supporting citation {i + 1}
                      </button>
                    </p>
                  ))}
                  {draft.recommendation.draft && (
                    <>
                      <h3>{draft.recommendation.draft.subject}</h3>
                      <p>{draft.recommendation.draft.opening}</p>
                      {draft.recommendation.draft.claims.map((c, i) => (
                        <p key={i}>{c.text}</p>
                      ))}
                      <p>{draft.recommendation.draft.closing}</p>
                      <p className="muted">
                        Draft only. An assigned reviewer must inspect the
                        approval queue.
                      </p>
                    </>
                  )}
                </section>
              )}
            {tab === "Approvals" && (
              <section>
                <h2>Human approval queue</h2>
                <p className="muted">
                  {SHOWCASE
                    ? "Simulated decisions are temporary and local to this browser. No real approval is recorded."
                    : "Approval records a decision for one exact version. It does not send a message."}
                </p>
                {!session.reviewer && (
                  <p>
                    Your account is not assigned as a reviewer. Ask your steward
                    for access.
                  </p>
                )}
                {session.reviewer && !data.actions.length && (
                  <p>No actions awaiting or recording review.</p>
                )}
                {data.actions.map((a) => (
                  <div className="row" key={a.id}>
                    <span>
                      {a.id.slice(0, 8)} · Version {a.current_version} ·{" "}
                      {label(a.state)}
                    </span>
                    <button
                      disabled={busy}
                      onClick={() =>
                        void perform(async () => {
                          setAction(null);
                          setAction(await api<Action>("/api/actions/" + a.id));
                        })
                      }
                    >
                      Inspect {a.id.slice(0, 8)}
                    </button>
                  </div>
                ))}
                {action && (
                  <div className="detail">
                    <h3>Inspect exact outreach version {action.version}</h3>
                    <p>
                      <strong>Recipient:</strong> {action.payload.recipient}
                    </p>
                    <p>
                      <strong>Subject:</strong> {action.payload.subject}
                    </p>
                    <pre className="message">{action.payload.body}</pre>
                    {action.payload.evidence_ids.map((id, i) => (
                      <button
                        key={id}
                        onClick={() => void perform(() => showCitation(id))}
                      >
                        Review source {i + 1}
                      </button>
                    ))}
                    <p className="hash">
                      Payload SHA-256: {action.payload_hash}
                    </p>
                    <p>
                      {SHOWCASE ? "Recorded expiry" : "Expires"}{" "}
                      {date(action.expires_at)}
                    </p>
                    {action.state === "pending" ? (
                      <div className="buttons">
                        {(["approve", "reject"] as const).map((decision) => (
                          <button
                            key={decision}
                            disabled={busy}
                            onClick={() =>
                              void perform(async () => {
                                await api(
                                  "/api/actions/" +
                                    action.action_id +
                                    "/decision",
                                  session,
                                  {
                                    version: action.version,
                                    payload_hash: action.payload_hash,
                                    decision,
                                  },
                                );
                                setAction(null);
                                setNotice(
                                  SHOWCASE
                                    ? "Simulated decision recorded in this browser only. No message was sent."
                                    : decision === "approve"
                                      ? "Version approved. No message was sent."
                                      : "Version rejected. No message was sent.",
                                );
                                await refresh();
                              })
                            }
                          >
                            {SHOWCASE
                              ? decision === "approve"
                                ? "Simulate approval"
                                : "Simulate rejection"
                              : decision === "approve"
                                ? "Approve this version"
                                : "Reject this version"}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <p>
                        This version is {action.state}; a new decision is
                        unavailable.
                      </p>
                    )}
                  </div>
                )}
              </section>
            )}
            {tab === "Evaluation" && (
              <>
                <section>
                  <p className="eyebrow">
                    FOCUSED POLICY V2 · SYNTHETIC DIAGNOSTIC
                  </p>
                  <h2>Independent quality review pending</h2>
                  <p>
                    <strong>
                      {focused.successes}/{focused.tasks}
                    </strong>{" "}
                    authored tasks passed. {focused.false_abstentions} false
                    abstentions; {focused.inappropriate_completions}{" "}
                    inappropriate completion remains.
                  </p>
                  <p className="muted">
                    {focused.scope} Direct and bounded templates had equal task
                    quality; tools added software overhead.
                  </p>
                  <p className="hash">
                    Source SHA-256: {focused.source_sha256}
                  </p>
                </section>
                <div className="warning">
                  <p className="eyebrow">HISTORICAL V1 RESULT · PRESERVED</p>
                  <h2>Recommendation quality gate: failed</h2>
                  <p>
                    Four false abstentions among 15 answerable frozen synthetic
                    test cases (26.7%; target ≤10%). This prior evaluation has
                    not been re-run or promoted by the dashboard.
                  </p>
                </div>
                <section>
                  <h2>Frozen offline evaluation evidence</h2>
                  <p className="muted">
                    Synthetic, agent-authored cases; not independently labeled.
                    No live-model accuracy or business lift.
                  </p>
                  {data.evaluation ? (
                    <>
                      <p>Recorded {data.evaluation.recorded_at}</p>
                      <table>
                        <caption>
                          Retrieval comparison · answerable cases · Recall@5
                        </caption>
                        <thead>
                          <tr>
                            <th>Method</th>
                            <th>Recall</th>
                            <th>Local p95 latency</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(
                            data.evaluation.retrieval_comparison,
                          ).map(([key, val]) => (
                            <tr key={key}>
                              <td>{label(key)}</td>
                              <td>{percent(val.recall_at_5)}</td>
                              <td>{val.p95_latency_ms.toFixed(1)} ms</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <p className="hash">
                        Source report SHA-256: {data.evaluation.source_sha256}
                      </p>
                    </>
                  ) : (
                    <p>
                      Evaluation artifact unavailable. No new quality claim can
                      be made.
                    </p>
                  )}
                </section>
                <section>
                  <h2>Attempt accounting</h2>
                  <p className="muted">
                    Organization-wide ledger, all periods. Fictional fixture
                    prices are simulated; unknown usage is not free. Hosting and
                    actual invoices are not measured.
                  </p>
                  {data.costs.map((c, i) => (
                    <p key={i}>
                      {label(c.cost_basis)} · {label(c.state)} · {c.attempts}{" "}
                      attempts · estimated USD{" "}
                      {c.estimated_cost_usd ?? "unknown"}
                    </p>
                  ))}
                  {!data.costs.length && (
                    <p>
                      No provider attempts recorded. Templates do not call a
                      model.
                    </p>
                  )}
                </section>
              </>
            )}
          </>
        )}
        {citation && (
          <section className="citation" aria-label="Source evidence">
            <h2>
              {citation.title} · v{citation.version}
            </h2>
            <p>
              {citation.heading} · characters {citation.start_offset}–
              {citation.end_offset}
            </p>
            <blockquote>{citation.text}</blockquote>
            <button onClick={() => setCitation(null)}>Close source</button>
          </section>
        )}
        <footer>
          RevenueOS · Offline intelligence · Synthetic data only · No external
          messaging
        </footer>
      </main>
    </div>
  );
}
function Kpi({
  name,
  value,
  detail,
}: {
  name: string;
  value: string;
  detail: string;
}) {
  return (
    <section className="kpi">
      <h2>{name}</h2>
      <strong>{value}</strong>
      <p className="muted">{detail}</p>
    </section>
  );
}
createRoot(document.getElementById("root")!).render(
  <Boundary>
    <App />
  </Boundary>,
);
