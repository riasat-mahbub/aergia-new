import { useEffect } from "react";
import { Link } from "@tanstack/react-router";
import { motion } from "motion/react";
import {
  ArrowRight,
  BriefcaseBusiness,
  FileText,
  Library,
  Plus,
} from "lucide-react";
import SummaryCard from "./_components/SummaryCard";
import ApplicationRow from "./_components/ApplicationRow";
import { formatDate, templateLabel } from "./_lib/dashboardPresentation";
import { useApplicationStore } from "@/app/dashboard/_stores/applicationStore";
import { useCVListStore } from "@/app/dashboard/_stores/cvListStore";
import { useLibraryStore } from "@/store/libraryStore";

export default function DashboardPage() {
  const cvList = useCVListStore((state) => state.cvList);
  const cvLoading = useCVListStore((state) => state.isLoading);
  const fetchCVs = useCVListStore((state) => state.fetchCVs);
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
                    to="/builder/$id"
                    params={{ id: cv.id }}
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
