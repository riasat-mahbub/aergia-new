import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CustomizePanel from "../customization/CustomizePanel";
import SectionZoneView from "../layout/SectionZoneView";
import BuilderPage from "../../pages/BuilderPage";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-id" }),
  useNavigate: () => vi.fn(),
  useBlocker: () => ({ state: "unblocked" }),
  useLocation: () => ({ pathname: "/dashboard/builder/test-cv-id" }),
}));

const mockLoadCV = vi.fn();
const mockSetIsSaving = vi.fn();
const mockSetLastSaved = vi.fn();
const mockCurrentCV = Object.freeze({
  id: "1",
  title: "Test CV",
  template_id: "generic-modern",
  sections: [],
  customizations: {},
});
const mockStoreState = {
  currentCV: mockCurrentCV,
  loadCV: mockLoadCV,
  isLoading: false,
  isSaving: false,
  lastSaved: null,
  setIsSaving: mockSetIsSaving,
  setLastSaved: mockSetLastSaved,
  patchCurrentCV: vi.fn(),
};
vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: Object.assign(vi.fn(() => mockStoreState), { getState: () => mockStoreState }),
}));

vi.mock("../../lib/api/cvs", () => ({
  updateCV: vi.fn(() => Promise.resolve({})),
}));

vi.mock("../../lib/api/templates", () => ({
  fetchTemplate: vi.fn(() => Promise.resolve({})),
}));

vi.mock("../../lib/api/client", () => ({ default: vi.fn() }));

vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({ default: ({ open }: any) => open ? <div>AddSectionModal</div> : null }));
vi.mock("../customization/ZoneStyleEditor", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneCreationModal", () => ({ default: () => <div /> }));
vi.mock("../common/Modal", () => ({ default: ({ open, children }: any) => open ? <div>{children}</div> : null }));
vi.mock("../layout/SectionZoneView", () => ({
  default: vi.fn(({ onSelect, selectedSectionId, instances }: any) => (
    <div data-testid="zone-view">
      {(instances || []).map((inst: any) => (
        <button key={inst.id} data-testid={`zone-section-${inst.id}`} onClick={() => onSelect?.(inst.id)}>
          {inst.title}
        </button>
      ))}
      <div data-testid="zone-view-selected">{selectedSectionId ?? ""}</div>
    </div>
  )),
}));

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: any) => <div>{children}</div>,
  DragOverlay: ({ children }: any) => <div>{children}</div>,
  useDroppable: () => ({ isOver: false, setNodeRef: vi.fn() }),
  closestCenter: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(() => ({})),
  useSensors: vi.fn(() => []),
}));

vi.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: any) => <div>{children}</div>,
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  }),
  arrayMove: vi.fn((arr) => arr),
  verticalListSortingStrategy: vi.fn(),
}));

vi.mock("@dnd-kit/utilities", () => ({ CSS: { Transform: { toString: () => "" } } }));

vi.mock("motion/react", () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

const renderCustomizePanel = (
  props?: Partial<Parameters<typeof CustomizePanel>[0]>,
) =>
  render(
    <CustomizePanel
      customizations={{}}
      onChange={vi.fn()}
      templateId="generic-modern"
      onTemplateChange={vi.fn()}
      instances={[]}
      onUpdateStyle={vi.fn()}
      layoutConfig={{ zones: [], placement: {} }}
      onLayoutConfigChange={vi.fn()}
      globalStyleSchema={undefined}
      {...props}
    />
  );

describe("CustomizePanel", () => {
  it("renders Global section with color pickers by default", () => {
    renderCustomizePanel();

    expect(screen.getByText("Global")).toBeDefined();
    expect(screen.getByText("Accent")).toBeDefined();
  });

  it("calls onChange when color is changed", () => {
    const onChange = vi.fn();
    renderCustomizePanel({ customizations: { colors: { accent: "#2563eb" } }, onChange });

    const inputs = screen.getAllByRole("textbox") as HTMLInputElement[];
    const accentInput = inputs.find((i) => i.value === "#2563eb");
    if (accentInput) {
      fireEvent.change(accentInput, { target: { value: "#ff0000" } });
      expect(onChange).toHaveBeenCalled();
    }
  });

  it("renders the layout view (mocked SectionZoneView)", () => {
    renderCustomizePanel({
      instances: [
        { id: "s1", type: "profile", title: "John", enabled: true, data: {} },
        { id: "s2", type: "experience", title: "Work", enabled: true, data: [] },
      ],
    });

    expect(screen.getByTestId("zone-view")).toBeDefined();
    expect(screen.getByText("John")).toBeDefined();
    expect(screen.getByText("Work")).toBeDefined();
    expect(screen.queryByText(/Section Overrides/i)).toBeNull();
  });

  it("clicking a section in the layout view reveals per-section style controls", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [
        { id: "s1", type: "profile", title: "John", enabled: true, data: {} },
      ],
    });

    expect(screen.queryByText(/Style: John/)).toBeNull();

    fireEvent.click(screen.getByTestId("zone-section-s1"));

    expect(screen.getByText(/Style: John/)).toBeDefined();
  });

  it("changing the color in the per-section style panel calls onUpdateStyle with the new style", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [
        { id: "s1", type: "profile", title: "John", enabled: true, data: {} },
      ],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));

    const hexInput = screen.getByPlaceholderText("Default") as HTMLInputElement;
    fireEvent.change(hexInput, { target: { value: "#ff0000" } });

    expect(onUpdateStyle).toHaveBeenCalledWith("s1", expect.objectContaining({ color: "#ff0000" }));
  });

  it("clearing all style values calls onUpdateStyle with an empty object", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [
        {
          id: "s1",
          type: "profile",
          title: "John",
          enabled: true,
          data: {},
          style: { color: "#ff0000" } as any,
        },
      ],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));

    const hexInput = screen.getByPlaceholderText("Default") as HTMLInputElement;
    fireEvent.change(hexInput, { target: { value: "" } });

    expect(onUpdateStyle).toHaveBeenCalledWith("s1", {});
  });

  it("passes readOnly={false} so section rows are draggable in the customize tab", () => {
    renderCustomizePanel({
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });
    const calls = vi.mocked(SectionZoneView).mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall?.[0].readOnly).toBe(false);
  });

  it("exposes a Text Align control that updates the section style", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));

    const selects = screen.getAllByRole("combobox") as HTMLSelectElement[];
    const alignSelect = selects.find((s) =>
      Array.from(s.options).some((o) => o.value === "justify"),
    );
    expect(alignSelect).toBeDefined();
    const optionLabels = Array.from(alignSelect!.options).map((o) => o.textContent);
    expect(optionLabels).toEqual(expect.arrayContaining(["Default", "Left", "Right", "Center", "Justify"]));
  });
  it("renders a Layout select for the skills section that switches between block and inline", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [
        {
          id: "s1",
          type: "skills",
          title: "Skills",
          enabled: true,
          data: [{ id: "g1", category: "Languages", items: ["Python", "Go"] }],
        },
      ],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));

    const layoutSelect = screen.getByRole("combobox", { name: /layout/i }) as HTMLSelectElement;
    fireEvent.change(layoutSelect, { target: { value: "inline" } });
    expect(onUpdateStyle).toHaveBeenCalledWith("s1", expect.objectContaining({ layout: "inline" }));
  });


  it("Per-field typography panel lists profile fields", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));

    expect(screen.getByText("Per-field typography")).toBeDefined();
    expect(screen.getByText("Name")).toBeDefined();
    expect(screen.getByText("Title")).toBeDefined();
    expect(screen.getByText("Email")).toBeDefined();
    expect(screen.getByText("Phone")).toBeDefined();
    expect(screen.getByText("Location")).toBeDefined();
    expect(screen.getByText("Site")).toBeDefined();
    expect(screen.getByText("Social Links")).toBeDefined();
    expect(screen.getByText("Summary")).toBeDefined();
  });

  it("Per-field typography panel lists project fields", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [{ id: "s2", type: "projects", title: "Proj", enabled: true, data: [] }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s2"));

    expect(screen.getByText("Name")).toBeDefined();
    expect(screen.getByText("Link")).toBeDefined();
    expect(screen.getByText("Date")).toBeDefined();
    expect(screen.getByText("Description")).toBeDefined();
    expect(screen.getByText("Tech")).toBeDefined();
  });

  it("renders a Date Style dropdown for the experience section that updates the section style", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [
        {
          id: "s1",
          type: "experience",
          title: "Work",
          enabled: true,
          data: [],
        },
      ],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));

    const dateStyleSelect = screen.getByLabelText("Date Style") as HTMLSelectElement;
    expect(dateStyleSelect).toBeDefined();
    expect(dateStyleSelect.value).toBe("");
    fireEvent.change(dateStyleSelect, { target: { value: "Mon YYYY" } });
    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({
        date_style: { key: "Mon YYYY", rangeSep: " \u2013 " },
      }),
    );
  });

  it("does NOT render a Date Style dropdown for the profile section", () => {
    renderCustomizePanel({
      instances: [
        { id: "s1", type: "profile", title: "John", enabled: true, data: {} },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    expect(screen.queryByLabelText("Date Style")).toBeNull();
  });

  it("does NOT render a Date Style dropdown for the skills section", () => {
    renderCustomizePanel({
      instances: [
        {
          id: "s1",
          type: "skills",
          title: "Skills",
          enabled: true,
          data: [{ id: "g1", category: "Languages", items: ["Python"] }],
        },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    expect(screen.queryByLabelText("Date Style")).toBeNull();
  });

  it("does NOT render a Date Style dropdown for the languages section", () => {
    renderCustomizePanel({
      instances: [
        {
          id: "s1",
          type: "languages",
          title: "Languages",
          enabled: true,
          data: [{ id: "l1", language: "English", proficiency: "Native" }],
        },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    expect(screen.queryByLabelText("Date Style")).toBeNull();
  });

  it("renders a Date Style dropdown for certifications", () => {
    renderCustomizePanel({
      instances: [
        {
          id: "s1",
          type: "certifications",
          title: "Certs",
          enabled: true,
          data: [],
        },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    expect(screen.getByLabelText("Date Style")).toBeDefined();
  });

  it("renders a Date Style dropdown for research", () => {
    renderCustomizePanel({
      instances: [
        {
          id: "s1",
          type: "research",
          title: "Papers",
          enabled: true,
          data: [],
        },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    expect(screen.getByLabelText("Date Style")).toBeDefined();
  });

  it("Date Style dropdown shows the current value when style.date_style is set", () => {
    renderCustomizePanel({
      instances: [
        {
          id: "s1",
          type: "experience",
          title: "Work",
          enabled: true,
          data: [],
          style: { date_style: { key: "Month YYYY", rangeSep: " \u2013 " } } as any,
        },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    const dateStyleSelect = screen.getByLabelText("Date Style") as HTMLSelectElement;
    expect(dateStyleSelect.value).toBe("Month YYYY");
  });
});

describe("globalStyleSchema prop", () => {
  it("renders the new toggle from the schema, replacing the hardcoded DEFAULT_SCHEMA", () => {
    renderCustomizePanel({
      globalStyleSchema: [
        { key: "default_link_style", type: "boolean", label: "Default Link Style", default: "false" },
        { key: "underline_section_titles", type: "boolean", label: "Underline Section Titles", default: "false" },
      ],
    });

    expect(screen.getByText("Default Link Style")).toBeDefined();
    expect(screen.getByText("Underline Section Titles")).toBeDefined();
  });

  it("falls back to hardcoded schema when no globalStyleSchema is supplied", () => {
    renderCustomizePanel({ globalStyleSchema: undefined });

    expect(screen.getByText("Underline Section Titles")).toBeDefined();
    expect(screen.queryByText("Default Link Style")).toBeNull();
  });
});

describe("T48: customization panel switches via tab bar in BuilderPage", () => {
  it("is hidden in Content tab by default", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.queryByText("Accent")).toBeNull());
  });

  it("appears after clicking Customize tab", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.getByText("Customize")).toBeDefined());
    fireEvent.click(screen.getByText("Customize"));
    await waitFor(() => expect(screen.getByText("Accent")).toBeDefined());
  });

  it("hides when switching back to Content tab", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.getByText("Customize")).toBeDefined());
    fireEvent.click(screen.getByText("Customize"));
    await waitFor(() => expect(screen.getByText("Accent")).toBeDefined());
    fireEvent.click(screen.getByText("Content"));
    await waitFor(() => expect(screen.queryByText("Accent")).toBeNull());
  });
});
