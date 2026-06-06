import { useState } from "react";

export function useFieldArray<T extends { id: string }>(
  data: T[],
  onChange: (data: T[]) => void,
  createDefault: () => T
) {
  useState(() => data.length > 0 ? data : []);

  const add = () => {
    onChange([...data, createDefault()]);
  };

  const remove = (index: number) => {
    onChange(data.filter((_, i) => i !== index));
  };

  const update = (index: number, field: keyof T, value: unknown) => {
    const updated = data.map((entry, i) =>
      i === index ? { ...entry, [field]: value } : entry
    );
    onChange(updated);
  };

  const move = (from: number, to: number) => {
    if (from === to || from < 0 || from >= data.length || to < 0 || to > data.length) return;
    const updated = [...data];
    const [entry] = updated.splice(from, 1);
    updated.splice(to, 0, entry);
    onChange(updated);
  };

  return { entries: data, add, remove, update, move };
}
