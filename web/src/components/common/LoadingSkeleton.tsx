import { motion } from "motion/react";

interface LoadingSkeletonProps {
  count?: number;
}

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-lg border border-app-rule bg-app-surface p-6">
      <div className="mb-3 h-5 w-3/4 rounded bg-app-surface-strong" />
      <div className="mb-2 h-3 w-1/2 rounded bg-app-surface-strong" />
      <div className="h-3 w-1/3 rounded bg-app-surface-strong" />
    </div>
  );
}

export default function LoadingSkeleton({ count = 6 }: LoadingSkeletonProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{ visible: { transition: { staggerChildren: 0.05 } } }}
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
        >
          <SkeletonCard />
        </motion.div>
      ))}
    </motion.div>
  );
}
