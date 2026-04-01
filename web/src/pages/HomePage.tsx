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
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-white">
      <header className="flex items-center justify-between px-6 py-4">
        <span className="text-xl font-bold text-emerald-800">Aergia</span>
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <button
              onClick={() => navigate("/dashboard")}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white hover:bg-emerald-700"
            >
              Go to My CVs
            </button>
          ) : (
            <>
              <button
                onClick={() => navigate("/login")}
                className="rounded-md border border-emerald-300 px-4 py-2 text-sm text-emerald-700 hover:bg-emerald-50"
              >
                Sign in
              </button>
              <button
                onClick={() => navigate("/register")}
                className="rounded-md bg-emerald-600 px-4 py-2 text-sm text-white hover:bg-emerald-700"
              >
                Get started
              </button>
            </>
          )}
        </div>
      </header>

      <section className="flex flex-col items-center px-4 py-20 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-gray-900 sm:text-6xl">
          Build beautiful CVs
        </h1>
        <p className="mt-4 max-w-lg text-lg text-gray-500">
          Aergia helps you create, customize, and export professional CVs in minutes — no design skills needed.
        </p>
        {isAuthenticated ? (
          <button
            onClick={() => navigate("/dashboard")}
            className="mt-8 rounded-md bg-emerald-600 px-6 py-3 text-base text-white hover:bg-emerald-700"
          >
            Go to My CVs &rarr;
          </button>
        ) : (
          <button
            onClick={() => navigate("/register")}
            className="mt-8 rounded-md bg-emerald-600 px-6 py-3 text-base text-white hover:bg-emerald-700"
          >
            Start building &rarr;
          </button>
        )}
      </section>

      <section className="mx-auto max-w-5xl px-4 pb-24">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="rounded-lg border border-emerald-100 bg-white p-6 shadow-sm">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-emerald-100 text-emerald-700">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold text-gray-900">{f.title}</h3>
              <p className="mt-1 text-sm text-gray-500">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-emerald-100 px-6 py-6 text-center text-sm text-gray-400">
        &copy; {new Date().getFullYear()} Aergia
      </footer>
    </div>
  );
}
