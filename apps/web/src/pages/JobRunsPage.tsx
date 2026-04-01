import { useEffect, useState } from "react";
import { getJobRuns, type JobRun } from "../api";

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
      <h2>Job Runs</h2>
      {error ? <p role="alert">API error: {error}</p> : null}
      <table className="table">
        <thead>
          <tr>
            <th>Job Name</th>
            <th>Status</th>
            <th>Started</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>{run.job_name}</td>
              <td>{run.status}</td>
              <td>{run.started_at ?? run.created_at ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
