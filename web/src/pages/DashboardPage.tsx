import { useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import {
  ArrowRight,
  BriefcaseBusiness,
  FileText,
  Library,
  Plus,
  type LucideIcon,
} from "lucide-react";
import type { Application, ApplicationStatus } from "../lib/api/applications";
import { useApplicationStore } from "../lib/store/applicationStore";
import { useCVStore } from "../lib/store/cvStore";
import { useLibraryStore } from "../lib/store/libraryStore";

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  draft: "Draft",
  applied: "Applied",
  responded: "Responded",
  interview: "Interview",
  offer: "Offer",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const STATUS_CLASSES: Record<ApplicationStatus, string> = {
  draft: "bg-app-surface-muted text-app-ink-2",
  applied: "bg-app-primary-soft text-app-primary",
  responded: "bg-app-secondary-soft text-app-secondary",
  interview: "bg-app-secondary-soft text-app-secondary",
  offer: "bg-app-warning-soft text-app-warning",
  hired: "bg-app-primary-soft text-app-primary",
  rejected: "bg-app-danger-soft text-app-danger",
  withdrawn: "bg-app-surface-muted text-app-ink-3",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

function templateLabel(templateId: string): string {
  return templateId.replace("generic-", "").replace("-", " ");
}

interface SummaryCardProps {
  to: string;
  label: string;
  count: number;
  description: string;
  Icon: LucideIcon;
}

function SummaryCard({ to, label, count, description, Icon }: SummaryCardProps) {
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

function ApplicationRow({ application }: { application: Application }) {
  return (
    <Link
      to={`/dashboard/applications/${application.id}`}
      className="flex items-center justify-between gap-4 rounded-lg px-3 py-3 transition hover:bg-app-surface-muted"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-app-ink">{application.company}</p>
        <p className="mt-0.5 truncate text-xs text-app-ink-3">{application.role}</p>
      </div>
      <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_CLASSES[application.status]}`}>
        {STATUS_LABELS[application.status]}
      </span>
    </Link>
  );
}

export default function DashboardPage() {
  const cvList = useCVStore((state) => state.cvList);
  const cvLoading = useCVStore((state) => state.isLoading);
  const fetchCVs = useCVStore((state) => state.fetchCVs);
  const libraryEntries = useLibraryStore((state) => state.entries);
  const libraryLoaded = useLibraryStore((state) => state.loaded);
  const libraryFetch = useLibraryStore((state) => state.fetchAll);
  const applications = useApplicationStore((state) => state.applications);
  const applicationsLoading = useApplicationStore((state) => state.isLoading);
  const applicationsLoaded = useApplicationStore((state) => state.loaded);
  const fetchApplications = useApplicationStore((state) => state.fetchAll);

  useEffect(() => {
    fetchCVs();
    if (!libraryLoaded) libraryFetch();
    if (!applicationsLoaded) fetchApplications();
  }, [applicationsLoaded, fetchApplications, fetchCVs, libraryFetch, libraryLoaded]);

  const authoredCvs = cvList.filter((cv) => !cv.application);
  const generatedCvCount = cvList.length - authoredCvs.length;
  const recentCvs = authoredCvs.slice(0, 3);
  const recentApplications = applications.slice(0, 4);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <motion.header initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <p className="text-sm font-medium text-app-primary">Your workspace</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-app-ink">Dashboard</h1>
        <p className="mt-2 max-w-2xl text-sm text-app-ink-2">
          Keep your reusable CVs, source material, and job applications in one place.
        </p>
      </motion.header>

      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard
          to="/dashboard/cvs"
          label="CVs"
          count={authoredCvs.length}
          description={generatedCvCount ? `${generatedCvCount} tailored CV${generatedCvCount === 1 ? "" : "s"} in Applications` : "Reusable CVs and versions"}
          Icon={FileText}
        />
        <SummaryCard
          to="/dashboard/library"
          label="Library"
          count={libraryLoaded ? libraryEntries.length : 0}
          description="Reusable experience, skills, and more"
          Icon={Library}
        />
        <SummaryCard
          to="/dashboard/applications"
          label="Applications"
          count={applications.length}
          description="Jobs you are tracking"
          Icon={BriefcaseBusiness}
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <section className="rounded-xl border border-app-rule bg-app-surface p-5 shadow-sm" aria-labelledby="recent-cvs-heading">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 id="recent-cvs-heading" className="text-lg font-semibold text-app-ink">Recent CVs</h2>
              <p className="mt-1 text-sm text-app-ink-3">Your reusable CV drafts and versions.</p>
            </div>
            <Link to="/dashboard/cvs" className="text-sm font-medium text-app-primary hover:text-app-primary-hover">
              View all
            </Link>
          </div>

          <div className="mt-5">
            {cvLoading ? (
              <p className="text-sm text-app-ink-3">Loading CVs…</p>
            ) : recentCvs.length > 0 ? (
              <div className="divide-y divide-app-rule-soft">
                {recentCvs.map((cv) => (
                  <Link
                    key={cv.id}
                    to={`/dashboard/builder/${cv.id}`}
                    className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-app-ink">{cv.title}</p>
                      <p className="mt-0.5 text-xs capitalize text-app-ink-3">
                        {templateLabel(cv.template_id)} · Updated {formatDate(cv.updated_at)}
                      </p>
                    </div>
                    <ArrowRight className="h-4 w-4 shrink-0 text-app-ink-3" />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-app-rule-strong px-4 py-6 text-center">
                <p className="text-sm font-medium text-app-ink">No reusable CVs yet</p>
                <p className="mt-1 text-sm text-app-ink-3">Start with a CV you can adapt for every application.</p>
                <Link to="/dashboard/cvs" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-app-primary hover:text-app-primary-hover">
                  <Plus className="h-4 w-4" />
                  Create a CV
                </Link>
              </div>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-app-rule bg-app-surface p-5 shadow-sm" aria-labelledby="recent-applications-heading">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 id="recent-applications-heading" className="text-lg font-semibold text-app-ink">Applications</h2>
              <p className="mt-1 text-sm text-app-ink-3">Your latest tracked opportunities.</p>
            </div>
            <Link to="/dashboard/applications" className="text-sm font-medium text-app-primary hover:text-app-primary-hover">
              View all
            </Link>
          </div>

          <div className="mt-5">
            {applicationsLoading && !applicationsLoaded ? (
              <p className="text-sm text-app-ink-3">Loading applications…</p>
            ) : recentApplications.length > 0 ? (
              <div className="divide-y divide-app-rule-soft">
                {recentApplications.map((application) => <ApplicationRow key={application.id} application={application} />)}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-app-rule-strong px-4 py-6 text-center">
                <p className="text-sm font-medium text-app-ink">No applications yet</p>
                <p className="mt-1 text-sm text-app-ink-3">Track a job to keep its notes and tailored CV together.</p>
                <Link to="/dashboard/applications" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-app-primary hover:text-app-primary-hover">
                  Track an application <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
