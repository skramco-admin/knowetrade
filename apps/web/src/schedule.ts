type Weekday = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export type CronCountdown = {
  label: string;
  nextRunLocal: string;
  countdown: string;
};

function formatCountdown(ms: number): string {
  if (ms <= 0) {
    return "00:00:00";
  }
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function nextUtcWeeklyRun(now: Date, hourUtc: number, minuteUtc: number, runDaysUtc: Weekday[]): Date {
  const currentMs = now.getTime();
  for (let offset = 0; offset <= 14; offset += 1) {
    const candidate = new Date(currentMs + offset * 24 * 60 * 60 * 1000);
    const day = candidate.getUTCDay() as Weekday;
    if (!runDaysUtc.includes(day)) {
      continue;
    }
    candidate.setUTCHours(hourUtc, minuteUtc, 0, 0);
    if (candidate.getTime() > currentMs) {
      return candidate;
    }
  }
  // Fallback should never happen with a valid weekly schedule.
  return new Date(currentMs + 24 * 60 * 60 * 1000);
}

function buildCountdown(label: string, hourUtc: number, minuteUtc: number): CronCountdown {
  const now = new Date();
  const nextRun = nextUtcWeeklyRun(now, hourUtc, minuteUtc, [1, 2, 3, 4, 5]);
  return {
    label,
    nextRunLocal: nextRun.toLocaleString(),
    countdown: formatCountdown(nextRun.getTime() - now.getTime()),
  };
}

export function getTradingCronCountdowns(): CronCountdown[] {
  return [
    buildCountdown("Next premarket health check", 13, 30),
    buildCountdown("Next strategy check (postclose workflow)", 20, 30),
    buildCountdown("Next trade execution check (order-submit)", 20, 40),
    buildCountdown("Next reconciliation check", 21, 0),
    buildCountdown("Next daily summary", 21, 15),
  ];
}
