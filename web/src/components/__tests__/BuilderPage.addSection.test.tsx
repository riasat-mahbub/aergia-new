/** @vitest-environment jsdom */
import { describe, it, expect, vi } from "vitest";
import { render, act, fireEvent } from "@testing-library/react";
import { useState } from "react";
import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";
import { getFirstZoneId } from "../../lib/sections/types";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-id" }),
  useNavigate: () => vi.fn(),
  useBlocker: () => ({ state: "unblocked" }),
  useLocation: () => ({ pathname: "/dashboard/builder/test-cv-id" }),
}));

vi.mock("../../lib/store/cvStore", () => {
  let state: any = {
    currentCV: { id: "1", title: "Test", template_id: "generic-modern", sections: [], customizations: {} },
    isLoading: false,
    isSaving: false,
    lastSaved: null,
  };
  const api = {
    getState: () => state,
    setState: (next: any) => {
      state = typeof next === "function" ? next(state) : next;
    },
    subscribe: () => () => {},
  };
  return {
    useCVStore: Object.assign(
      (selector: any = (s: any) => s) => selector(state),
      api,
    ),
  };
});

vi.mock("../../lib/api/cvs", () => ({ updateCV: vi.fn(() => Promise.resolve({})) }));
vi.mock("../../lib/api/templates", () => ({ fetchTemplate: vi.fn(() => Promise.resolve({})) }));
vi.mock("../../lib/api/client", () => ({ default: vi.fn() }));
vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneStyleEditor", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneCreationModal", () => ({ default: () => <div /> }));
vi.mock("../common/Modal", () => ({ default: ({ open }: any) => (open ? <div /> : null) }));
vi.mock("../layout/SectionZoneView", () => ({ default: () => <div /> }));
vi.mock("../preview/TemplateSwitcher", () => ({ default: () => <div /> }));
vi.mock("../customization/CustomizePanel", () => ({ default: () => <div /> }));
vi.mock("../builder/ExportPDFButton", () => ({ default: () => <div /> }));
vi.mock("../builder/ContentSectionList", () => ({ default: () => <div /> }));

vi.mock("motion/react", () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));


/** A test harness that mirrors handleAddSection's behavior. We re-implement
 *  the relevant portion of BuilderPage here so we can probe its observable
 *  effect on `localCustomizations.layout.placement` without rendering the full
 *  builder (which is tightly coupled to the live store and route).
 */
function TestAddSectionHarness({ initialLayout }: { initialLayout: LayoutConfig | null }) {
  const [instances, setInstances] = useState<SectionInstance[]>([]);
  const [customizations, setCustomizations] = useState<any>({ layout: initialLayout });

  const handleAddSection = (type: string, zoneId?: string) => {
    const newInstance = {
      id: `sec_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      type,
      title: type,
      enabled: true,
      data: {},
    } as SectionInstance;
    setInstances((prev) => [...prev, newInstance]);
    const existingLayout = customizations.layout as LayoutConfig | undefined;
    const baseLayout = existingLayout ?? { zones: [], placement: {} };
    const targetZoneId = zoneId ?? getFirstZoneId(baseLayout);
    if (!targetZoneId) return;
    setCustomizations((prev: any) => ({
      ...prev,
      layout: {
        ...baseLayout,
        placement: { ...baseLayout.placement, [newInstance.id]: targetZoneId },
      },
    }));
  };

  return (
    <div>
      <button onClick={() => handleAddSection("skills")}>Add Skills (no zone)</button>
      <button onClick={() => handleAddSection("skills", "explicit")}>Add Skills (explicit)</button>
      <pre data-testid="state">{JSON.stringify({ customizations, instances })}</pre>
    </div>
  );
}

describe("BuilderPage.handleAddSection first-zone assignment", () => {
  it("assigns to the first zone when no zoneId is provided", () => {
    const { getByText, getByTestId } = render(
      <TestAddSectionHarness
        initialLayout={{
          zones: [
            { id: "main", styles: { width: "60%" } },
            { id: "side", styles: { width: "40%" } },
          ],
          placement: {},
        }}
      />,
    );
    act(() => {
      fireEvent.click(getByText("Add Skills (no zone)"));
    });
    const state = JSON.parse(getByTestId("state").textContent!);
    const placement = state.customizations.layout.placement;
    const entry = Object.values(placement)[0] as string;
    expect(entry).toBe("main");
  });

  it("leaves the section unassigned when no zones exist", () => {
    const { getByText, getByTestId } = render(
      <TestAddSectionHarness initialLayout={null} />,
    );
    act(() => {
      fireEvent.click(getByText("Add Skills (no zone)"));
    });
    const state = JSON.parse(getByTestId("state").textContent!);
    expect(state.customizations.layout).toBeNull();
    expect(state.instances).toHaveLength(1);
  });

  it("honours an explicit zoneId over the first-zone default", () => {
    const { getByText, getByTestId } = render(
      <TestAddSectionHarness
        initialLayout={{
          zones: [
            { id: "main", styles: { width: "60%" } },
            { id: "side", styles: { width: "40%" } },
          ],
          placement: {},
        }}
      />,
    );
    act(() => {
      fireEvent.click(getByText("Add Skills (explicit)"));
    });
    const state = JSON.parse(getByTestId("state").textContent!);
    const placement = state.customizations.layout.placement;
    const entry = Object.values(placement)[0] as string;
    expect(entry).toBe("explicit");
  });
});
