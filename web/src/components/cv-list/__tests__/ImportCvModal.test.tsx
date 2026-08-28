import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import ImportCvModal, { titleFromFilename } from "../ImportCvModal";

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

describe("titleFromFilename", () => {
  it("strips a trailing .pdf (case-insensitive)", () => {
    expect(titleFromFilename("Senior CV.pdf")).toBe("Senior CV");
    expect(titleFromFilename("Senior CV.PDF")).toBe("Senior CV");
  });

  it("returns 'Imported CV' for empty or whitespace-only input", () => {
    expect(titleFromFilename("")).toBe("Imported CV");
    expect(titleFromFilename("   ")).toBe("Imported CV");
    expect(
      titleFromFilename(undefined as unknown as string)
    ).toBe("Imported CV");
    expect(titleFromFilename(null as unknown as string)).toBe("Imported CV");
  });

  it("leaves non-pdf filenames unchanged", () => {
    expect(titleFromFilename("resume.docx")).toBe("resume.docx");
  });
});

describe("ImportCvModal", () => {
  it("renders the title input, template select, and a Choose PDF button", () => {
    render(
      <ImportCvModal
        open
        onClose={() => undefined}
        onSubmit={() => undefined}
      />
    );

    expect(screen.getByLabelText("Title")).toBeTruthy();
    expect(screen.getByLabelText("Template")).toBeTruthy();
    expect(screen.getByText(/Choose PDF…/)).toBeTruthy();
    expect(screen.getByText(/Cancel/)).toBeTruthy();
  });

  it("Import is disabled until both title and file are present", () => {
    render(
      <ImportCvModal
        open
        onClose={() => undefined}
        onSubmit={() => undefined}
      />
    );

    const importBtn = screen.getByRole("button", { name: "Import" });
    expect((importBtn as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Senior CV" },
    });
    expect((importBtn as HTMLButtonElement).disabled).toBe(true);

    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(["%PDF-1.4\n%smoke"], "Senior.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });
    expect((importBtn as HTMLButtonElement).disabled).toBe(false);
  });

  it("autofills the title from the filename when the input is empty", () => {
    render(
      <ImportCvModal
        open
        onClose={() => undefined}
        onSubmit={() => undefined}
      />
    );

    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(
      ["%PDF-1.4\n%smoke"],
      "Imported Senior CV.pdf",
      { type: "application/pdf" }
    );
    fireEvent.change(fileInput, { target: { files: [file] } });

    const titleInput = screen.getByLabelText("Title") as HTMLInputElement;
    expect(titleInput.value).toBe("Imported Senior CV");
  });

  it("keeps an existing title when the user has typed one", () => {
    render(
      <ImportCvModal
        open
        onClose={() => undefined}
        onSubmit={() => undefined}
      />
    );

    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "My Custom Title" },
    });

    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(["%PDF-1.4\n%smoke"], "Resume.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(fileInput, { target: { files: [file] } });

    const titleInput = screen.getByLabelText("Title") as HTMLInputElement;
    expect(titleInput.value).toBe("My Custom Title");
  });

  it("invokes onSubmit with title, templateId and file", () => {
    const onSubmit = vi.fn();
    render(
      <ImportCvModal open onClose={() => undefined} onSubmit={onSubmit} />
    );

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

    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const arg = onSubmit.mock.calls[0][0];
    expect(arg.title).toBe("Senior CV");
    expect(arg.templateId).toBe("generic-minimal");
    expect(arg.file).toBe(file);
  });

  it("Cancel invokes onClose without calling onSubmit", () => {
    const onSubmit = vi.fn();
    const onClose = vi.fn();
    render(<ImportCvModal open onClose={onClose} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByRole("button", { name: /Cancel/ }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("Change pill swaps the chosen file", () => {
    render(
      <ImportCvModal
        open
        onClose={() => undefined}
        onSubmit={() => undefined}
      />
    );

    const fileInput = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    fireEvent.change(fileInput, {
      target: {
        files: [new File(["x"], "first.pdf", { type: "application/pdf" })],
      },
    });

    expect(screen.getByText("first.pdf")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Change/ })).toBeTruthy();

    fireEvent.change(fileInput, {
      target: {
        files: [new File(["y"], "second.pdf", { type: "application/pdf" })],
      },
    });
    expect(screen.getByText("second.pdf")).toBeTruthy();
  });
});
