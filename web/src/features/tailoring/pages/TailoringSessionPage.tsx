import { Download } from "lucide-react";
import { Link } from "@tanstack/react-router";

/**
 * Public landing page for the link embedded in the copied agent prompt.
 * It deliberately does not fetch session data: the one-time code is sent
 * only to the scoped exchange endpoint by the installed skill.
 */
export interface TailoringSessionPageProps {
  sessionId: string;
}

export default function TailoringSessionPage({ sessionId }: TailoringSessionPageProps) {

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <section className="w-full max-w-lg rounded-lg border border-app-rule bg-app-surface p-6 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-app-primary">Aergia tailoring session</p>
        <h1 className="mt-2 text-2xl font-bold text-app-ink">Use your coding agent</h1>
        <p className="mt-3 text-sm leading-6 text-app-ink-2">
          Paste the complete prompt from Aergia into Codex, Claude Code, or OpenCode. The Aergia tailoring skill will retrieve the evidence, compose a tailored CV, validate it, and submit it for your review.
        </p>
        <p className="mt-4 rounded-md bg-app-canvas px-3 py-2 text-xs text-app-ink-3">Session: {sessionId}</p>
        <p className="mt-4 text-xs leading-5 text-app-ink-3">
          First time? Download the official bundle and extract its <code>aergia-tailor</code> folder into your agent&apos;s user-level skills directory. The copied prompt also lets your agent ask permission to do this for you.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <a href="/api/v1/tailoring/skill.zip" download className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-sm font-medium text-white hover:bg-app-primary-hover">
            Download skill <Download className="h-4 w-4" />
          </a>
          <Link to="/applications" className="inline-flex text-sm font-medium text-app-primary hover:underline">
            Return to Aergia
          </Link>
        </div>
      </section>
    </main>
  );
}
