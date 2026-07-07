import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ExportPDFButton from "../builder/ExportPDFButton";

const mockExportPDF = vi.fn();
const mockDownloadPDF = vi.fn();
const mockAddToast = vi.fn();

vi.mock("../../lib/api/cvs", () => ({
  exportPDF: (...args: unknown[]) => mockExportPDF(...args),
  downloadPDF: (...args: unknown[]) => mockDownloadPDF(...args),
}));

vi.mock("../../lib/store/uiStore", () => ({
  useToastStore: Object.assign(
    (selector: (state: { addToast: typeof mockAddToast }) => unknown) =>
      selector({ addToast: mockAddToast }),
    { getState: () => ({ addToast: mockAddToast }) },
  ),
}));

describe("ExportPDFButton", () => {
  beforeEach(() => {
    mockExportPDF.mockReset();
    mockDownloadPDF.mockReset();
    mockAddToast.mockReset();
  });

  it("awaits onBeforeExport before requesting PDF", async () => {
    const order: string[] = [];
    const onBeforeExport = vi.fn(async () => {
      order.push("save");
    });
    mockExportPDF.mockImplementation(async () => {
      order.push("exportPDF");
      return new Blob(["pdf"], { type: "application/pdf" });
    });
    render(
      <ExportPDFButton
        cvId="cv_1"
        cvTitle="Senior CV"
        onBeforeExport={onBeforeExport}
      />,
    );
    fireEvent.click(screen.getByTitle("Export PDF"));
    await waitFor(() => expect(onBeforeExport).toHaveBeenCalled());
    expect(order).toEqual(["save", "exportPDF"]);
    await waitFor(() => expect(mockDownloadPDF).toHaveBeenCalled());
  });

  it("downloads a title-sanitized PDF and reports success", async () => {
    mockExportPDF.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
    render(<ExportPDFButton cvId="cv_2" cvTitle="Senior CV / 2026" />);
    fireEvent.click(screen.getByTitle("Export PDF"));
    await waitFor(() => expect(mockDownloadPDF).toHaveBeenCalledTimes(1));
    const [, filename] = mockDownloadPDF.mock.calls[0] as [Blob, string];
    // The component uses .replace(/[^a-zA-Z0-9]/g, "_") on the title; slashes become underscores.
    expect(filename).toBe("Senior_CV___2026.pdf");
    expect(mockAddToast).toHaveBeenCalledWith("PDF exported successfully", "success");
    expect(screen.getByText("PDF")).toBeDefined();
  });

  it("reports failure and does not download", async () => {
    mockExportPDF.mockRejectedValue(new Error("network down"));
    render(<ExportPDFButton cvId="cv_3" cvTitle="Will Fail" />);
    fireEvent.click(screen.getByTitle("Export PDF"));
    await waitFor(() => expect(mockAddToast).toHaveBeenCalledWith("Failed to export PDF", "error"));
    expect(mockDownloadPDF).not.toHaveBeenCalled();
    // Button returns to enabled + "PDF" label.
    expect(screen.getByText("PDF")).toBeDefined();
  });
});
