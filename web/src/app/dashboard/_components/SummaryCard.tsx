import { ArrowRight, type LucideIcon } from "lucide-react";
import { Link } from "@tanstack/react-router";

interface SummaryCardProps {
  to: "/dashboard/cvs" | "/dashboard/library" | "/dashboard/applications";
  label: string;
  count: number;
  description: string;
  Icon: LucideIcon;
}

export default function SummaryCard({ to, label, count, description, Icon }: SummaryCardProps) {
  return (
    <Link
      to={to}
      className="group rounded-xl border border-app-rule bg-app-surface p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-app-primary-soft hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-app-primary-soft text-app-primary">
          <Icon className="h-5 w-5" />
        </div>
        <ArrowRight className="h-4 w-4 text-app-ink-3 transition group-hover:translate-x-0.5 group-hover:text-app-primary" />
      </div>
      <p className="mt-5 text-sm font-medium text-app-ink-2">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight text-app-ink">{count}</p>
      <p className="mt-1 text-sm text-app-ink-3">{description}</p>
    </Link>
  );
}
