import type { TailoringSessionStatusResponse } from "../types";

export function sessionStatusLabel(status: TailoringSessionStatusResponse["status"]): string {
  switch (status) {
    case "created": return "Ready to start";
    case "exchanged": return "Agent connected";
    case "submitted": return "Validating patch";
    case "applied": return "Tailoring applied";
    case "failed": return "Tailoring failed";
    case "expired": return "Expired";
    case "cancelled": return "Cancelled";
    case "stale": return "Source CV changed — restart required";
    default: return status;
  }
}

export function isTerminalTailoringStatus(
  status: TailoringSessionStatusResponse["status"] | undefined,
): boolean {
  return status === "applied" || status === "failed" || status === "expired" || status === "cancelled" || status === "stale";
}

export function terminalTailoringToast(
  status: TailoringSessionStatusResponse["status"],
): { message: string; type: "success" | "error" | "info" } | null {
  switch (status) {
    case "applied": return { message: "Your tailored CV is ready. Relevance has been updated.", type: "success" };
    case "failed": return { message: "Tailoring failed. No CV changes were saved.", type: "error" };
    case "expired": return { message: "The tailoring session expired. Start a new session to try again.", type: "info" };
    case "cancelled": return { message: "Tailoring session cancelled.", type: "info" };
    case "stale": return { message: "The source CV changed during tailoring. Start a new session to try again.", type: "error" };
    default: return null;
  }
}
