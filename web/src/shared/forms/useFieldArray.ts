import { useState } from "react";

export function useFieldArray<T extends { id: string }>(
  data: T[],
  onChange: (data: T[]) => void,
  createDefault: () => T
) {
  // Always coerce to a real array. Editor callers already default
  // `data = []` at the prop boundary, but transient `undefined` can
  // still leak through (HMR, mid-save updates, partial API responses).
  // Centralising the guard here prevents every editor from
  // re-implementing it.
  const safeData = Array.isArray(data) ? data : [];
  useState(() => (safeData.length > 0 ? safeData : []));

  const add = () => {
    onChange([...safeData, createDefault()]);
  };

  const remove = (index: number) => {
    onChange(safeData.filter((_, i) => i !== index));
  };

  const update = (index: number, field: keyof T, value: unknown) => {
    const updated = safeData.map((entry, i) =>
      i === index ? { ...entry, [field]: value } : entry,
    );
    onChange(updated);
  };

  const move = (from: number, to: number) => {
    if (from === to || from < 0 || from >= safeData.length || to < 0 || to > safeData.length) return;
    const updated = [...safeData];
    const [entry] = updated.splice(from, 1);
    updated.splice(to, 0, entry);
    onChange(updated);
  };

  return { entries: safeData, add, remove, update, move };
}
