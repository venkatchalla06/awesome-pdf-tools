"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "./api";

export type JobStatus = "pending" | "processing" | "completed" | "failed" | "expired";

export interface JobState {
  status: JobStatus;
  progress: number;
  downloadUrl: string | null;
  error: string | null;
  options: Record<string, unknown>;
}

export function useJob(jobId: string | null): JobState {
  const [state, setState] = useState<JobState>({
    status: "pending",
    progress: 0,
    downloadUrl: null,
    error: null,
    options: {},
  });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!jobId) return;
    try {
      const job = await api.get(`/jobs/${jobId}`);
      setState((prev) => ({ ...prev, status: job.status, progress: job.progress, options: job.options ?? {} }));

      if (job.status === "completed") {
        const { download_url } = await api.get(`/jobs/${jobId}/download-url`);
        setState((prev) => ({ ...prev, downloadUrl: download_url }));
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
      if (job.status === "failed") {
        setState((prev) => ({ ...prev, error: job.error_message }));
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    } catch (e) {
      console.error("Job poll error:", e);
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 1500);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [jobId, fetchStatus]);

  return state;
}
