import { Link } from "react-router-dom";
import { motion } from "motion/react";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h1 className="text-6xl font-bold text-gray-300">404</h1>
        <p className="mt-2 text-lg text-gray-600">Page not found</p>
        <Link
          to="/dashboard"
          className="mt-6 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
        >
          Go to Dashboard
        </Link>
      </motion.div>
    </div>
  );
}
