import { Link, useParams } from "react-router-dom";

/**
 * Public landing page for the link embedded in the copied agent prompt.
 * It deliberately does not fetch session data: the one-time code is sent
 * only to the scoped exchange endpoint by the installed skill.
 */
export default function AgentTailoringPage() {
  const { sessionId = "" } = useParams();

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <section className="w-full max-w-lg rounded-lg border border-app-rule bg-app-surface p-6 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-app-primary">Aergia tailoring session</p>
        <h1 className="mt-2 text-2xl font-bold text-app-ink">Use your installed coding agent</h1>
        <p className="mt-3 text-sm leading-6 text-app-ink-2">
          Paste the complete prompt from Aergia into Codex, Claude Code, or OpenCode. The Aergia tailoring skill will use the one-time session code to retrieve the task evidence and submit a validated patch.
        </p>
        <p className="mt-4 rounded-md bg-app-canvas px-3 py-2 text-xs text-app-ink-3">Session: {sessionId}</p>
        <p className="mt-4 text-xs leading-5 text-app-ink-3">
          If the skill is missing or outdated, your agent should ask before installing or updating it from the official Aergia source.
        </p>
        <Link to="/dashboard/applications" className="mt-6 inline-flex text-sm font-medium text-app-primary hover:underline">
          Return to Aergia
        </Link>
      </section>
    </main>
  );
}
