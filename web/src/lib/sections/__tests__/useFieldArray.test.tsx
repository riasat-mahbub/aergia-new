import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useFieldArray } from "../useFieldArray";

const entries = [
  { id: "a", title: "A" },
  { id: "b", title: "B" },
  { id: "c", title: "C" },
];

describe("useFieldArray move", () => {
  it("moves an entry using indices from the current array", () => {
    const onChange = vi.fn();
    const { result } = renderHook(() =>
      useFieldArray(entries, onChange, () => ({ id: "new", title: "New" })),
    );

    result.current.move(0, 2);

    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange).toHaveBeenCalledWith([entries[1], entries[2], entries[0]]);
  });

  it.each([
    [0, 0],
    [-1, 1],
    [entries.length, 0],
    [0, -1],
    [0, entries.length + 1],
  ])("does not emit a change for invalid move (%i, %i)", (from, to) => {
    const onChange = vi.fn();
    const { result } = renderHook(() =>
      useFieldArray(entries, onChange, () => ({ id: "new", title: "New" })),
    );

    result.current.move(from, to);

    expect(onChange).not.toHaveBeenCalled();
  });
});
