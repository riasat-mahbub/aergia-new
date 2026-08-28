import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Modal from "../Modal";

describe("Modal", () => {
  it("uses a mobile-safe default panel and an explicit wide panel", () => {
    render(
      <>
        <Modal open onClose={vi.fn()}>
          <div data-testid="default-content" />
        </Modal>
        <Modal open onClose={vi.fn()} size="wide">
          <div data-testid="wide-content" />
        </Modal>
      </>,
    );

    const defaultPanel = screen.getByTestId("default-content").parentElement;
    const widePanel = screen.getByTestId("wide-content").parentElement;

    expect(defaultPanel).toHaveClass("w-[calc(100%-2rem)]", "max-w-lg", "max-h-[calc(100vh-2rem)]", "overflow-hidden");
    expect(widePanel).toHaveClass("w-[calc(100%-2rem)]", "max-w-3xl", "max-h-[calc(100vh-2rem)]", "overflow-hidden");
  });
});
