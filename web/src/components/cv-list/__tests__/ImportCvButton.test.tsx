import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import {
  createMemoryRouter,
  RouterProvider,
} from "react-router-dom";

import ImportCvButton from "../ImportCvButton";
import { forgetAllKeys, loadKeys, saveKeys } from "../../../lib/llm/keys";

const mockImportPDF = vi.fn();
const mockCreateCV = vi.fn();
const mockAddToast = vi.fn();
const mockNavigate = vi.fn();

vi.mock("../../../lib/api/imports", () => ({
  importPDF: (...args: unknown[]) => mockImportPDF(...args),
}));

vi.mock("../../../lib/store/cvStore", () => ({
  useCVStore: Object.assign(
    (selector: (state: { createCV: typeof mockCreateCV }) => unknown) =>
      selector({ createCV: mockCreateCV }),
    { getState: () => ({ createCV: mockCreateCV }) }
  ),
}));

vi.mock("../../../lib/store/uiStore", () => ({
  useToastStore: Object.assign(
    (selector: (state: { addToast: typeof mockAddToast }) => unknown) =>
      selector({ addToast: mockAddToast }),
    { getState: () => ({ addToast: mockAddToast }) }
  ),
}));

vi.mock("../../../lib/api/templates", () => ({
  fetchSystemTemplates: vi.fn().mockResolvedValue([
    {
      id: "generic-modern",
      name: "Modern",
      description: null,
      preview_image_url: null,
      manifest: null,
    },
    {
      id: "generic-classic",
      name: "Classic",
      description: null,
      preview_image_url: null,
      manifest: null,
    },
    {
      id: "generic-minimal",
      name: "Minimal",
      description: null,
      preview_image_url: null,
      manifest: null,
    },
  ]),
}));

vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderButton() {
  const router = createMemoryRouter(
    [
      { path: "/dashboard", element: <ImportCvButton /> },
      { path: "/dashboard/builder/:id", element: <div>builder</div> },
    ],
    { initialEntries: ["/dashboard"] }
  );
  return render(<RouterProvider router={router} />);
}

// Click the modal's "Import" submit button (the in-modal one). The
// header "Import CV" button has the same word, so we match exact-text.
function clickModalImport() {
  fireEvent.click(screen.getByRole("button", { name: "Import" }));
}

describe("ImportCvButton", () => {
  beforeEach(() => {
    forgetAllKeys();
    mockImportPDF.mockReset();
    mockCreateCV.mockReset();
    mockAddToast.mockReset();
    mockNavigate.mockReset();
  });

  it("renders the default 'Import CV' label when no key is set", () => {
    renderButton();
    expect(screen.getByText("Import CV")).toBeTruthy();
  });

  it("switches the label to 'Import CV · OpenAI' when an OpenAI key is saved", () => {
    saveKeys({ openai: "sk-test-key-marker" });
    renderButton();
    expect(screen.getByText("Import CV · OpenAI")).toBeTruthy();
  });

  it("breaks ties by canonical order when multiple keys are saved", () => {
    saveKeys({ groq: "gsk_x", openai: "sk_x", anthropic: "sk-ant_x" });
    renderButton();
    expect(screen.getByText("Import CV · OpenAI")).toBeTruthy();
  });

  it("keeps API-key configuration out of the import action cluster", () => {
    renderButton();
    expect(screen.queryByTitle("Configure LLM API keys")).not.toBeInTheDocument();
  });

  it("clicking the Import CV button opens the modal", () => {
    renderButton();
    fireEvent.click(screen.getByText("Import CV"));
    expect(screen.getByText(/Cancel/)).toBeTruthy();
    expect(screen.getByLabelText("Title")).toBeTruthy();
    expect(screen.getByLabelText("Template")).toBeTruthy();
  });

  it("clears in-memory LLM keys when the import modal is canceled", () => {
    saveKeys({ openai: "sk-cancel-key" });
    renderButton();

    fireEvent.click(screen.getByText("Import CV · OpenAI"));
    expect(loadKeys()).toEqual({ openai: "sk-cancel-key" });

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(loadKeys()).toEqual({});
  });

  it("on success: invokes importPDF, createCV with sections, navigates to the new builder route", async () => {
    const sections = [
      {
        id: "imp_one",
        type: "profile",
        title: "One",
        enabled: true,
        data: { name: "One" },
      },
    ];
    mockImportPDF.mockResolvedValue({
      sections,
      confidence: { fields: [], overall_level: "high" },
      meta: { source: "regex", warnings: [] },
    });
    mockCreateCV.mockResolvedValue({
      id: "cv_new",
      title: "Senior CV",
      template_id: "generic-modern",
    });

    renderButton();

    fireEvent.click(screen.getByText("Import CV"));
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Senior CV" },
    });

    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(["%PDF-1.4\n%smoke"], "input.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });

    clickModalImport();

    await waitFor(() => expect(mockImportPDF).toHaveBeenCalledWith(file));
    await waitFor(() =>
      expect(mockCreateCV).toHaveBeenCalledWith(
        "Senior CV",
        "generic-minimal",
        sections
      )
    );
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/dashboard/builder/cv_new")
    );
  });

  it("on importPDF failure: fires the error toast, no navigation, no createCV", async () => {
    mockImportPDF.mockRejectedValue(new Error("bad PDF"));

    renderButton();

    fireEvent.click(screen.getByText("Import CV"));
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Senior CV" },
    });

    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    fireEvent.change(fileInput, {
      target: {
        files: [new File(["x"], "input.pdf", { type: "application/pdf" })],
      },
    });
    clickModalImport();

    await waitFor(() =>
      expect(mockAddToast).toHaveBeenCalledWith("Failed to import CV", "error")
    );
    expect(mockCreateCV).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
