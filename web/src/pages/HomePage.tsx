import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../lib/store/authStore";
import { FileText, Palette, Download, GripVertical, Eye, Shield } from "lucide-react";

const features = [
  { icon: FileText, title: "Multiple Templates", description: "Choose from modern, classic, and minimal designs to match your style." },
  { icon: Palette, title: "Custom Styling", description: "Fine-tune colors, fonts, and weights per section for a personalized look." },
  { icon: Download, title: "PDF Export", description: "Export a polished, print-ready PDF with a single click." },
  { icon: GripVertical, title: "Drag & Drop", description: "Reorder sections freely to highlight what matters most." },
  { icon: Eye, title: "Live Preview", description: "See every change reflected instantly as you build your CV." },
  { icon: Shield, title: "Secure & Fast", description: "JWT-secured auth with auto-save, so your work is never lost." },
];

export default function HomePage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return (
    <div className="min-h-screen bg-gradient-to-br from-app-primary-soft to-app-surface">
      <header className="flex items-center justify-between px-6 py-4">
        <span className="text-xl font-bold text-app-primary">Aergia</span>
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <button
              onClick={() => navigate("/dashboard")}
              className="rounded-md bg-app-primary px-4 py-2 text-sm text-white hover:bg-app-primary-hover"
            >
              Go to Dashboard
            </button>
          ) : (
            <>
              <button
                onClick={() => navigate("/login")}
                className="rounded-md border border-app-primary-soft px-4 py-2 text-sm text-app-primary hover:bg-app-primary-soft"
              >
                Sign in
              </button>
              <button
                onClick={() => navigate("/register")}
                className="rounded-md bg-app-primary px-4 py-2 text-sm text-white hover:bg-app-primary-hover"
              >
                Get started
              </button>
            </>
          )}
        </div>
      </header>

      <section className="flex flex-col items-center px-4 py-20 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-app-ink sm:text-6xl">
          Build beautiful CVs
        </h1>
        <p className="mt-4 max-w-lg text-lg text-app-ink-3">
          Aergia helps you create, customize, and export professional CVs in minutes — no design skills needed.
        </p>
        {isAuthenticated ? (
          <button
            onClick={() => navigate("/dashboard")}
            className="mt-8 rounded-md bg-app-primary px-6 py-3 text-base text-white hover:bg-app-primary-hover"
          >
            Go to Dashboard &rarr;
          </button>
        ) : (
          <button
            onClick={() => navigate("/register")}
            className="mt-8 rounded-md bg-app-primary px-6 py-3 text-base text-white hover:bg-app-primary-hover"
          >
            Start building &rarr;
          </button>
        )}
      </section>

      <section className="mx-auto max-w-5xl px-4 pb-24">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="rounded-lg border border-app-primary-soft bg-app-surface p-6 shadow-sm">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-app-primary-soft text-app-primary">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold text-app-ink">{f.title}</h3>
              <p className="mt-1 text-sm text-app-ink-3">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-app-primary-soft px-6 py-6 text-center text-sm text-app-ink-3">
        &copy; {new Date().getFullYear()} Aergia
      </footer>
    </div>
  );
}
