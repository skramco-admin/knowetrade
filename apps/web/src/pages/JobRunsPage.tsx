import { useEffect, useState } from "react";
import { getJobRuns, type JobRun } from "../api";
import { friendlyJobName, jobDescription } from "../jobs";
import { formatDateTime, formatRelativeTime } from "../format";
import { StatusPill } from "../components/OperatorUi";

function runStatusLevel(status: string): "ok" | "warn" | "bad" {
  if (status === "success") {
    return "ok";
  }
  if (status === "failed" || status === "completed_with_errors") {
    return "bad";
  }
  return "warn";
}

export function JobRunsPage() {
  const [runs, setRuns] = useState<JobRun[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getJobRuns()
      .then(setRuns)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load job runs"));
  }, []);

  return (
    <section className="card">
      <h2>Automation log</h2>
      <p className="muted">Each row is one scheduled Render cron run.</p>
      {error ? <p role="alert" className="error">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>Status</th>
            <th>What ran</th>
            <th>Technical name</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const level = runStatusLevel(run.status);
            const when = run.started_at ?? run.created_at;
            return (
              <tr key={run.id}>
                <td>
                  <StatusPill status={level} label={run.status} />
                </td>
                <td>
                  <strong>{friendlyJobName(run.job_name)}</strong>
                  <div className="muted small">{jobDescription(run.job_name)}</div>
                </td>
                <td className="muted small">{run.job_name}</td>
                <td>
                  {formatRelativeTime(when)}
                  <div className="muted small">{formatDateTime(when)}</div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
