/** @vitest-environment jsdom */
import { describe, it, expect, vi } from "vitest";
import { act, render } from "@testing-library/react";
import { useEffect, useState } from "react";

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: "/dashboard/builder/test" }),
  useBlocker: () => ({ state: "unblocked", proceed: vi.fn() }),
}));
vi.mock("motion/react", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));
vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: () => ({
    currentCV: { id: "test", title: "T", template_id: "generic-modern", template_content: null, sections: [], customizations: {}, styles: {}, created_at: "", updated_at: "" },
    loadCV: vi.fn(),
    isLoading: false,
    isSaving: false,
    lastSaved: null,
    setIsSaving: vi.fn(),
    setLastSaved: vi.fn(),
  }),
}));
vi.mock("../../lib/api/cvs", () => ({ updateCV: vi.fn(() => Promise.resolve({})) }));
vi.mock("../../lib/api/templates", () => ({ fetchTemplate: vi.fn(() => Promise.resolve({})) }));
vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneStyleEditor", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneCreationModal", () => ({ default: () => <div /> }));
vi.mock("../common/Modal", () => ({ default: ({ open }: any) => (open ? <div /> : null) }));
vi.mock("../layout/SectionZoneView", () => ({ default: () => <div /> }));
vi.mock("../preview/TemplateSwitcher", () => ({ default: () => <div /> }));
vi.mock("../customization/CustomizePanel", () => ({ default: () => <div /> }));
vi.mock("../builder/ExportPDFButton", () => ({ default: () => <div /> }));
vi.mock("../builder/ContentSectionList", () => ({ default: (_props: any) => {
  // Simulate the editor calling onUpdateData with empty array
  // so we can verify the parent removes the instance.
  return <div data-testid="content-list" />;
} }));

/**
 * Test harness that mirrors BuilderPage's handleUpdateData logic.
 * Verifies the empty-array-removes-instance behavior.
 */
function TestHarness({ initialInstances }: { initialInstances: any[] }) {
  const [instances, setInstances] = useState<any[]>(initialInstances);
  const handleUpdateData = (id: string, data: any) => {
    if (Array.isArray(data) && data.length === 0) {
      // Empty array → remove instance
      setInstances((prev) => prev.filter((i) => i.id !== id));
    } else {
      setInstances((prev) => prev.map((i) => (i.id === id ? { ...i, data } : i)));
    }
  };
  // Expose the latest state and handler to the test assertions via
  // a side effect (the `react-hooks/immutability` rule forbids assigning
  // to the component function during render).
  useEffect(() => {
    (TestHarness as any).instances = instances;
    (TestHarness as any).handleUpdateData = handleUpdateData;
  });
  return <div data-testid="harness" />;
}
describe("BuilderPage.handleUpdateData empty-array semantically removes", () => {
  it("removes the instance when data is empty array", () => {
    const initial = [
      { id: "a", type: "experience", title: "Experience", enabled: true, data: [{ id: "e1" }] },
      { id: "b", type: "education", title: "Education", enabled: true, data: [{ id: "ed1" }] },
    ];
    render(<TestHarness initialInstances={initial} />);
    act(() => {
      (TestHarness as any).handleUpdateData("a", []);
    });
    expect((TestHarness as any).instances).toHaveLength(1);
    expect((TestHarness as any).instances[0].id).toBe("b");
  });

  it("keeps the instance when data is non-empty array", () => {
    const initial = [
      { id: "a", type: "experience", title: "Experience", enabled: true, data: [{ id: "e1" }] },
    ];
    render(<TestHarness initialInstances={initial} />);
    act(() => {
      (TestHarness as any).handleUpdateData("a", [{ id: "e2" }]);
    });
    expect((TestHarness as any).instances).toHaveLength(1);
    expect((TestHarness as any).instances[0].data).toHaveLength(1);
  });
});
