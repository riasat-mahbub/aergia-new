/** @vitest-environment jsdom */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act, fireEvent } from "@testing-library/react";
import { useState } from "react";
import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";
import { getFirstZoneId } from "../../lib/sections/types";
import { fetchTemplate } from "../../lib/api/templates";

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


/** A test harness that mirrors BuilderPage.handleTemplateChange. We re-implement
 *  the relevant portion here so we can probe its observable effect on
 *  `localCustomizations.layout` without rendering the full builder.
 */
function TestTemplateChangeHarness({
  initialInstances,
  initialCustomizations,
}: {
  initialInstances: SectionInstance[];
  initialCustomizations: Record<string, unknown>;
}) {
  const [instances, setInstances] = useState<SectionInstance[]>(initialInstances);
  const [customizations, setCustomizations] = useState<any>(initialCustomizations);

  const handleTemplateChange = async (newTemplateId: string) => {
    // Defensive: drop every per-instance style so the new template's styles take effect.
    const cleanInstances = instances.map((i) => ({ ...i, style: undefined }));
    setInstances(cleanInstances);

    let customizationsWithLayout: Record<string, unknown>;
    try {
      const template = await fetchTemplate(newTemplateId);
      const zones = template.manifest?.zones;
      const placement = template.manifest?.placement;
      if (Array.isArray(zones) && zones.length > 0 && placement) {
        // Install the new template's zones verbatim and reassign every section
        // to the first zone so the editor is never left with zero zones.
        const newLayout: LayoutConfig = { zones, placement: {} };
        const firstZoneId = getFirstZoneId(newLayout);
        for (const instance of cleanInstances) {
          if (firstZoneId) newLayout.placement[instance.id] = firstZoneId;
        }
        customizationsWithLayout = { ...customizations, layout: newLayout };
      } else {
        customizationsWithLayout = {};
      }
    } catch {
      // Template fetch failed — fall back to the wipe-and-reload behavior.
      customizationsWithLayout = {};
    }
    setCustomizations(customizationsWithLayout);
  };

  return (
    <div>
      <button onClick={() => handleTemplateChange("generic-classic")}>Switch template</button>
      <pre data-testid="state">{JSON.stringify({ customizations, instances })}</pre>
    </div>
  );
}

describe("BuilderPage.handleTemplateChange zone install", () => {
  beforeEach(() => {
    vi.mocked(fetchTemplate).mockReset();
  });

  it("installs the new template's zones and reassigns every section to the first zone", async () => {
    vi.mocked(fetchTemplate).mockResolvedValueOnce({
      manifest: {
        zones: [
          { id: "left", styles: { width: "40%" } },
          { id: "right", styles: { width: "60%" } },
        ],
        placement: {},
      },
    } as any);
    const { getByText, getByTestId } = render(
      <TestTemplateChangeHarness
        initialInstances={[
          { id: "sec_1", type: "profile", title: "Profile", enabled: true, data: {}, style: { color: "#fff" } },
          { id: "sec_2", type: "experience", title: "Experience", enabled: true, data: {} },
        ]}
        initialCustomizations={{ colors: { accent: "#123456" } }}
      />,
    );
    await act(async () => {
      fireEvent.click(getByText("Switch template"));
    });
    const state = JSON.parse(getByTestId("state").textContent!);
    const layout = state.customizations.layout;
    expect(layout.zones).toHaveLength(2);
    expect(state.customizations.colors.accent).toBe("#123456"); // other customization keys preserved
    for (const instance of state.instances) {
      expect(layout.placement[instance.id]).toBe("left");
      expect(instance.style).toBeUndefined();
    }
    expect(JSON.stringify(layout)).not.toMatch(/rowHeights/);
    expect(JSON.stringify(layout.zones)).not.toMatch(/"row"/);
  });

  it("falls back to no layout when the fetched template has no zones", async () => {
    vi.mocked(fetchTemplate).mockResolvedValueOnce({} as any);
    const { getByText, getByTestId } = render(
      <TestTemplateChangeHarness
        initialInstances={[{ id: "sec_1", type: "profile", title: "Profile", enabled: true, data: {} }]}
        initialCustomizations={{ colors: { accent: "#123456" } }}
      />,
    );
    await act(async () => {
      fireEvent.click(getByText("Switch template"));
    });
    const state = JSON.parse(getByTestId("state").textContent!);
    expect(state.customizations.layout).toBeUndefined();
    expect(state.instances).toHaveLength(1);
  });

  it("falls back to no layout when the template fetch throws", async () => {
    vi.mocked(fetchTemplate).mockRejectedValueOnce(new Error("network"));
    const { getByText, getByTestId } = render(
      <TestTemplateChangeHarness
        initialInstances={[{ id: "sec_1", type: "profile", title: "Profile", enabled: true, data: {} }]}
        initialCustomizations={{}}
      />,
    );
    await act(async () => {
      fireEvent.click(getByText("Switch template"));
    });
    const state = JSON.parse(getByTestId("state").textContent!);
    expect(state.customizations.layout).toBeUndefined();
  });
});
