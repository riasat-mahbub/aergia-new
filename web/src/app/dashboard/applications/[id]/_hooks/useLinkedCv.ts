import { useEffect, useState } from "react";
import { fetchCV } from "@/services/cvs";
import type { CVDetail } from "@/contracts/cvs";

/** Loads the CV linked to the current application and prevents stale responses on route changes. */
export function useLinkedCv(cvId: string | null | undefined): CVDetail | null {
  const [linkedCV, setLinkedCV] = useState<CVDetail | null>(null);

  useEffect(() => {
    if (!cvId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear stale linked CV when application changes
      setLinkedCV(null);
      return;
    }
    let cancelled = false;
    fetchCV(cvId).then((cv) => {
      if (!cancelled) setLinkedCV(cv);
    }).catch(() => {
      if (!cancelled) setLinkedCV(null);
    });
    return () => {
      cancelled = true;
    };
  }, [cvId]);

  return linkedCV;
}
