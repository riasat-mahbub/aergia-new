import type { TailoringSessionStatusResponse } from "../types";

export function sessionStatusLabel(status: TailoringSessionStatusResponse["status"]): string {
  switch (status) {
    case "created": return "Ready to start";
    case "exchanged": return "Agent connected";
    case "draft_ready": return "Draft ready for your review";
    case "accepted": return "Draft accepted";
    case "rejected": return "Draft rejected";
    case "failed": return "Tailoring failed";
    case "expired": return "Expired";
    case "cancelled": return "Cancelled";
    case "stale": return "Context changed — restart required";
    default: return status;
  }
}

export function isTerminalTailoringStatus(
  status: TailoringSessionStatusResponse["status"] | undefined,
): boolean {
  return status === "draft_ready" || status === "accepted" || status === "rejected" || status === "failed" || status === "expired" || status === "cancelled" || status === "stale";
}

export function terminalTailoringToast(
  status: TailoringSessionStatusResponse["status"],
): { message: string; type: "success" | "error" | "info" } | null {
  switch (status) {
    case "draft_ready": return { message: "A tailored CV draft is ready for your review.", type: "info" };
    case "accepted": return { message: "The tailored CV is now linked to this application.", type: "success" };
    case "rejected": return { message: "The tailored draft was rejected and removed.", type: "info" };
    case "failed": return { message: "Tailoring failed. No CV changes were saved.", type: "error" };
    case "expired": return { message: "The tailoring session expired. Start a new session to try again.", type: "info" };
    case "cancelled": return { message: "Tailoring session cancelled.", type: "info" };
    case "stale": return { message: "The tailoring context changed. Start a new session to try again.", type: "error" };
    default: return null;
  }
}
