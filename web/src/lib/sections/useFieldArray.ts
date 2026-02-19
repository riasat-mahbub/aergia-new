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

  return { entries: data, add, remove, update };
}
