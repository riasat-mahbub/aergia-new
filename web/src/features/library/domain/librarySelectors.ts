import type { LibraryEntry, LibraryEntryKind } from "@/features/library/types";

export function selectByKind(entries: LibraryEntry[]): Record<LibraryEntryKind, LibraryEntry[]> {
  const buckets: Record<LibraryEntryKind, LibraryEntry[]> = {
    experience: [],
    education: [],
    skill: [],
    project: [],
    certification: [],
    language: [],
    research: [],
  };
  for (const entry of entries) {
    // Runtime data can contain a future or legacy kind that is not in the
    // current contract. Ignore it rather than indexing an absent bucket.
    const bucket = buckets[entry.kind as LibraryEntryKind];
    if (bucket) bucket.push(entry);
  }
  return buckets;
}

export function countByKind(entries: LibraryEntry[]): Record<LibraryEntryKind, number> {
  const buckets = selectByKind(entries);
  const counts = {} as Record<LibraryEntryKind, number>;
  (Object.keys(buckets) as LibraryEntryKind[]).forEach((kind) => {
    counts[kind] = buckets[kind].length;
  });
  return counts;
}
