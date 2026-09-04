import { Link } from "react-router-dom";
import { motion } from "motion/react";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-app-canvas px-4">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h1 className="text-6xl font-bold text-app-ink-muted">404</h1>
        <p className="mt-2 text-lg text-app-ink-2">Page not found</p>
        <Link
          to="/dashboard"
          className="mt-6 inline-block rounded-md bg-app-primary px-4 py-2 text-sm text-white hover:bg-app-primary-hover"
        >
          Go to Dashboard
        </Link>
      </motion.div>
    </div>
  );
}
