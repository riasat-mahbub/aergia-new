import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import LLMKeyDialog from "../LLMKeyDialog";
import {
  STORAGE_KEY,
  saveKeys,
  loadKeys,
  forgetAllKeys,
} from "../../../lib/llm/keys";

const mockAddToast = vi.fn();

vi.mock("../../../lib/store/uiStore", () => ({
  useToastStore: Object.assign(
    (selector: (state: { addToast: typeof mockAddToast }) => unknown) =>
      selector({ addToast: mockAddToast }),
    { getState: () => ({ addToast: mockAddToast }) }
  ),
}));

describe("LLMKeyDialog", () => {
  beforeEach(() => {
    forgetAllKeys();
    mockAddToast.mockReset();
  });

  it("renders four inputs with type=password and provider-specific autoComplete", () => {
    render(<LLMKeyDialog open onClose={() => undefined} />);

    const inputByProvider = (name: string) =>
      document.querySelector(`input[name="${name}"]`) as HTMLInputElement;

    const openai = inputByProvider("key-openai");
    const anthropic = inputByProvider("key-anthropic");
    const gemini = inputByProvider("key-gemini");
    const groq = inputByProvider("key-groq");

    expect(openai).toBeTruthy();
    expect(openai.type).toBe("password");
    expect(openai.getAttribute("autocomplete")).toBe("current-password");

    expect(anthropic.type).toBe("password");
    expect(anthropic.getAttribute("autocomplete")).toBe("current-password");

    expect(gemini.type).toBe("password");
    expect(gemini.getAttribute("autocomplete")).toBe("off");

    expect(groq.type).toBe("password");
    expect(groq.getAttribute("autocomplete")).toBe("off");
  });

  it("renders the persistent security warning text in the DOM", () => {
    render(<LLMKeyDialog open onClose={() => undefined} />);
    expect(
      screen.getByText(/stored only in this browser tab/, { exact: false })
    ).toBeTruthy();
  });

  it("Save updates sessionStorage and fires the success toast with the stored providers", () => {
    render(<LLMKeyDialog open onClose={() => undefined} />);

    const openai = document.querySelector(
      'input[name="key-openai"]'
    ) as HTMLInputElement;
    fireEvent.change(openai, { target: { value: "sk-round-trip" } });

    fireEvent.click(screen.getByRole("button", { name: /Save/ }));

    expect(loadKeys()).toEqual({ openai: "sk-round-trip" });
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBe(
      JSON.stringify({ openai: "sk-round-trip" })
    );
    expect(mockAddToast).toHaveBeenCalledWith(
      "Saved API keys for: OpenAI",
      "success"
    );
  });

  it("Forget all wipes sessionStorage in one call and fires the info toast", () => {
    saveKeys({ openai: "sk-still-here", gemini: "AIza-still-here" });
    render(<LLMKeyDialog open onClose={() => undefined} />);

    fireEvent.click(screen.getByRole("button", { name: /Forget all/ }));

    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(mockAddToast).toHaveBeenCalledWith(
      "API keys cleared from this browser tab.",
      "info"
    );
  });

  it("Per-row Forget clears only that provider", () => {
    saveKeys({ openai: "sk-keep", gemini: "AIza-forget" });
    render(<LLMKeyDialog open onClose={() => undefined} />);

    const forgetGemini = screen.getByTitle("Forget Gemini key");
    fireEvent.click(forgetGemini);

    expect(loadKeys()).toEqual({ openai: "sk-keep" });
    expect(
      (window.sessionStorage.getItem(STORAGE_KEY) ?? "{}").includes(
        "sk-keep"
      )
    ).toBe(true);
    expect(
      (window.sessionStorage.getItem(STORAGE_KEY) ?? "{}").includes(
        "AIza-forget"
      )
    ).toBe(false);
  });

  it("Cancel leaves sessionStorage untouched", () => {
    saveKeys({ openai: "sk-keep-on-cancel" });
    render(<LLMKeyDialog open onClose={() => undefined} />);

    // Open the dialog, modify an input, then cancel.
    const openai = document.querySelector(
      'input[name="key-openai"]'
    ) as HTMLInputElement;
    // The dialog seeds values from loadKeys() — let's overwrite.
    fireEvent.change(openai, { target: { value: "sk-modified-but-not-saved" } });

    fireEvent.click(screen.getByRole("button", { name: /Cancel/ }));

    expect(loadKeys()).toEqual({ openai: "sk-keep-on-cancel" });
  });

  it("detects a typed-in-wrong-slot mismatch inline but Save still works", async () => {
    render(<LLMKeyDialog open onClose={() => undefined} />);

    const openai = document.querySelector(
      'input[name="key-openai"]'
    ) as HTMLInputElement;
    fireEvent.change(openai, { target: { value: "AIzaSyBong" } });

    // Save is non-blocking; the warning is informational only.
    await waitFor(() =>
      expect(
        screen.getByText(/Looks like a Gemini key/, { exact: false })
      ).toBeTruthy()
    );

    fireEvent.click(screen.getByRole("button", { name: /Save/ }));
    expect(loadKeys()).toEqual({ openai: "AIzaSyBong" });
  });

  it("does NOT show the mismatch warning when key prefix matches the slot", () => {
    render(<LLMKeyDialog open onClose={() => undefined} />);
    const openai = document.querySelector(
      'input[name="key-openai"]'
    ) as HTMLInputElement;
    fireEvent.change(openai, { target: { value: "sk-correct-prefix" } });
    expect(
      screen.queryByText(/Looks like a/, { exact: false })
    ).toBeNull();
  });

  it("seeds each input from saved values when re-opened", () => {
    saveKeys({ openai: "sk-rehydrated" });
    const { unmount } = render(
      <LLMKeyDialog open onClose={() => undefined} />
    );
    const openai = document.querySelector(
      'input[name="key-openai"]'
    ) as HTMLInputElement;
    expect(openai.value).toBe("sk-rehydrated");
    unmount();
  });
});
