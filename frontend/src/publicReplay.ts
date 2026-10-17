import recording from "../../data/dashboard/public-replay.json";

// Client-only replay. No fetch, credentials, storage, real authorization or model calls.
const snapshot = structuredClone(recording.dashboard);
const decisions = new Map<string, string>();
let prepared = false;
const records = recording as unknown as {
  workflows: Record<string, Record<string, unknown>>;
  recommendations: Record<string, unknown>;
  actions: Record<
    string,
    {
      action_id: string;
      version: number;
      payload_hash: string;
      state: string;
    }
  >;
  citations: Record<string, unknown>;
};

export async function replay(path: string, body?: unknown): Promise<unknown> {
  if (path === "/api/auth/config") return { mode: "public_replay" };
  if (path === "/api/session")
    return { csrf: "replay-only", reviewer: true, mode: "public_replay" };
  if (path === "/api/auth/logout") {
    decisions.clear();
    prepared = false;
    return {};
  }
  if (path === "/api/dashboard") {
    return {
      ...structuredClone(snapshot),
      recommendations: prepared
        ? Object.keys(records.recommendations).map((id) => ({
            id,
            state: "review_pending",
            failure_code: null,
            created_at: recording.recorded_at,
          }))
        : [],
      actions: prepared
        ? Object.values(records.actions).map((a) => ({
            id: a.action_id,
            state: decisions.get(a.action_id) ?? "pending",
            current_version: a.version,
          }))
        : [],
    };
  }
  if (path.startsWith("/api/dashboard?"))
    throw new Error(
      "Replay has one recorded interval. Clear both date filters.",
    );
  if (path === "/api/workflows") {
    const request = body as { lead_id: string; query: string };
    if (request.lead_id !== recording.lead_id)
      throw new Error("Use the guided eligible lead in this recorded replay.");
    const value = records.workflows[request.query.trim()];
    if (!value)
      throw new Error(
        "Question not recorded. Use configuration checklist or ignore previous instructions.",
      );
    if (value.state === "review_pending") prepared = true;
    return {
      ...structuredClone(value),
      recommendation_id:
        value.state === "review_pending" ? value.recommendation_id : null,
    };
  }
  const id = path.split("/").at(-1)!;
  if (path.startsWith("/api/citations/") && records.citations[id])
    return structuredClone(records.citations[id]);
  if (
    path.startsWith("/api/recommendations/") &&
    prepared &&
    records.recommendations[id]
  )
    return structuredClone(records.recommendations[id]);
  if (path.endsWith("/decision") && prepared) {
    const actionId = path.split("/").at(-2)!;
    const value = records.actions[actionId];
    const request = body as {
      version: number;
      payload_hash: string;
      decision: string;
    };
    if (
      !value ||
      request.version !== value.version ||
      request.payload_hash !== value.payload_hash ||
      decisions.has(actionId)
    )
      throw new Error(
        "Replay version changed or already decided. Reset the replay.",
      );
    if (!["approve", "reject"].includes(request.decision))
      throw new Error("Unsupported simulated decision.");
    decisions.set(
      actionId,
      request.decision === "approve" ? "approved" : "rejected",
    );
    return { simulated: true, delivered: false };
  }
  if (path.startsWith("/api/actions/") && prepared && records.actions[id])
    return {
      ...structuredClone(records.actions[id]),
      state: decisions.get(id) ?? "pending",
    };
  throw new Error("This capability is unavailable in the public replay.");
}

export const guidedLead = recording.lead_id;
