import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CustomizePanel from "../customization/CustomizePanel";
import SectionZoneView from "../layout/SectionZoneView";
import BuilderPage from "../../pages/BuilderPage";
import { useSupportStore } from "../../lib/store/supportStore";

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

vi.mock("../../lib/api/cvs", () => ({ updateCV: vi.fn(() => Promise.resolve({})) }));
vi.mock("../../lib/api/templates", () => ({ fetchTemplate: vi.fn(() => Promise.resolve({})) }));
vi.mock("../../lib/api/client", () => ({ default: vi.fn() }));
vi.mock("../../lib/api/render", () => ({
  fetchRendererSupport: vi.fn(() =>
    Promise.resolve({
      break_before: "FULL",
      keep_together: "FULL",
      keep_with_next: "FULL",
      heading_keeps_with_first: "FULL",
      feature_skills_inline: "FULL",
      feature_section_underline: "FULL",
      feature_anchor_styling: "FULL",
    }),
  ),
}));

vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({
  default: ({ open }: any) => (open ? <div>AddSectionModal</div> : null),
}));
vi.mock("../customization/ZoneStyleEditor", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneCreationModal", () => ({ default: () => <div /> }));
vi.mock("../common/Modal", () => ({
  default: ({ open, children }: any) => (open ? <div>{children}</div> : null),
}));
vi.mock("../layout/SectionZoneView", () => ({
  default: vi.fn(({ onSelect, selectedSectionId, instances }: any) => (
    <div data-testid="zone-view">
      {(instances || []).map((inst: any) => (
        <button
          key={inst.id}
          data-testid={`zone-section-${inst.id}`}
          onClick={() => onSelect?.(inst.id)}
        >
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

/**
 * Find a <select> whose visible label sits in the same parent as the
 * select element. The CustomizePanel uses <label>…<select /></label> and
 * some standalone <label><select /></label> combinations; testing-library
 * needs `htmlFor` to resolve them. This helper walks the DOM instead.
 */
function getSelectByLabelText(labelText: string): HTMLSelectElement {
  const labels = Array.from(document.querySelectorAll("label")) as HTMLLabelElement[];
  const target = labels.find((l) => (l.textContent ?? "").trim() === labelText);
  if (!target) throw new Error(`label '${labelText}' not found`);
  // The select may be a sibling or a child of the label.
  let el: Element | null = target.querySelector("select");
  if (!el) {
    // Sibling within the same wrapper:
    const wrapper = target.parentElement;
    if (wrapper) el = wrapper.querySelector("select");
  }
  if (!el) throw new Error(`select not found for label '${labelText}'`);
  return el as HTMLSelectElement;
}

const renderCustomizePanel = (
  props?: Partial<Parameters<typeof CustomizePanel>[0]>,
) =>
  render(
    <CustomizePanel
      templateId="generic-modern"
      onTemplateChange={vi.fn()}
      instances={[]}
      onUpdateStyle={vi.fn()}
      layoutConfig={{ zones: [], placement: {} }}
      onLayoutConfigChange={vi.fn()}
      {...props}
    />,
  );

describe("CustomizePanel", () => {
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
  });

  it("clicking a section in the layout view reveals per-section style controls", () => {
    renderCustomizePanel({
      instances: [
        { id: "s1", type: "profile", title: "John", enabled: true, data: {} },
      ],
    });

    expect(screen.queryByText(/Style: John/)).toBeNull();

    fireEvent.click(screen.getByTestId("zone-section-s1"));

    expect(screen.getByText(/Style: John/)).toBeDefined();
    expect(screen.getByText(/Layout \(page flow\)/)).toBeDefined();
    expect(screen.getByText(/Block style \(subsection\)/)).toBeDefined();
    expect(screen.getByText(/Section policy/)).toBeDefined();
  });

  it("changing section color hex calls onUpdateStyle with subsection.section_color", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Block style \(subsection\)/));

    // The Block style group has two color rows (BG color, Section color).
    // Each row pairs a colour-picker and a hex text input. We change the
    // second row's hex text (Section color).
    const labels = Array.from(document.querySelectorAll("label")) as HTMLLabelElement[];
    const secColorLabel = labels.find((l) => /Section color/.test(l.textContent ?? ""));
    expect(secColorLabel).toBeTruthy();
    const wrapper = secColorLabel!.parentElement;
    const hexInput = wrapper!.querySelector<HTMLInputElement>('input[type="text"]');
    expect(hexInput).toBeTruthy();
    fireEvent.change(hexInput!, { target: { value: "#ff0000" } });

    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({ subsection: { section_color: "#ff0000" } }),
    );
  });

  it("clearing the section color calls onUpdateStyle with subsection stripped of it", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [{
        id: "s1",
        type: "profile",
        title: "John",
        enabled: true,
        data: {},
        style: { subsection: { section_color: "#ff0000", text_align: "left" } } as any,
      }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Block style \(subsection\)/));

    const labels = Array.from(document.querySelectorAll("label")) as HTMLLabelElement[];
    const secColorLabel = labels.find((l) => /Section color/.test(l.textContent ?? ""));
    expect(secColorLabel).toBeTruthy();
    const wrapper = secColorLabel!.parentElement;
    const hexInput = wrapper!.querySelector<HTMLInputElement>('input[type="text"]');
    expect(hexInput).toBeTruthy();
    fireEvent.change(hexInput!, { target: { value: "" } });

    // After clearing section_color, the helper emits the merged subsection
    // with section_color=null. Other fields survive.
    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({
        subsection: expect.objectContaining({ text_align: "left" }),
      }),
    );
  });


  it("passes readOnly={false} so section rows are draggable in the customize tab", () => {
    renderCustomizePanel({
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });
    const calls = vi.mocked(SectionZoneView).mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall?.[0].readOnly).toBe(false);
  });

  it("exposes a Text Align control in Block style that updates subsection.text_align", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Block style \(subsection\)/));

    const alignSelect = getSelectByLabelText("Text align");
    fireEvent.change(alignSelect, { target: { value: "justify" } });

    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({ subsection: { text_align: "justify" } }),
    );
  });

  it("renders a Skills layout select for the skills section that writes policy.skill_variant", () => {
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
    fireEvent.click(screen.getByText(/Section policy/));

    const skillSelect = getSelectByLabelText("Skills layout");
    fireEvent.change(skillSelect, { target: { value: "inline" } });

    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({
        policy: { skill_variant: "inline" },
      }),
    );
  });

  it("writes per-instance policy on two skills sections independently", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [
        {
          id: "s_block",
          type: "skills",
          title: "Backend",
          enabled: true,
          data: [{ id: "g1", category: "Languages", items: ["Python"] }],
        },
        {
          id: "s_inline",
          type: "skills",
          title: "Frontend",
          enabled: true,
          data: [{ id: "g1", category: "Frameworks", items: ["React"] }],
        },
      ],
    });

    fireEvent.click(screen.getByTestId("zone-section-s_block"));
    fireEvent.click(screen.getByText(/Section policy/));
    fireEvent.change(getSelectByLabelText("Skills layout"), {
      target: { value: "inline" },
    });
    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s_block",
      expect.objectContaining({ policy: { skill_variant: "inline" } }),
    );

    fireEvent.click(screen.getByTestId("zone-section-s_inline"));
    fireEvent.click(screen.getByText(/Section policy/));
    fireEvent.change(getSelectByLabelText("Skills layout"), {
      target: { value: "block" },
    });
    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s_inline",
      expect.objectContaining({ policy: { skill_variant: "block" } }),
    );

    const calls = onUpdateStyle.mock.calls;
    expect(calls.some((c) => c[0] === "s_block" && c[1]?.policy?.skill_variant === "inline")).toBe(true);
    expect(calls.some((c) => c[0] === "s_inline" && c[1]?.policy?.skill_variant === "block")).toBe(true);
  });
  it("Field styles panel lists profile fields", () => {
    renderCustomizePanel({
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Field styles/));

    expect(screen.getByText("Name")).toBeDefined();
    expect(screen.getByText("Title")).toBeDefined();
    expect(screen.getByText("Email")).toBeDefined();
    expect(screen.getByText("Phone")).toBeDefined();
    expect(screen.getByText("Location")).toBeDefined();
    expect(screen.getByText("Summary")).toBeDefined();
  });

  it("Field styles panel lists project fields", () => {
    renderCustomizePanel({
      instances: [{ id: "s2", type: "projects", title: "Proj", enabled: true, data: [] }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s2"));
    fireEvent.click(screen.getByText(/Field styles/));

    expect(screen.getByText("Name")).toBeDefined();
    expect(screen.getByText("Link")).toBeDefined();
    expect(screen.getByText("Date")).toBeDefined();
    expect(screen.getByText("Description")).toBeDefined();
  });

  it("renders a Date format dropdown for the experience section that writes layout.date_style", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [
        { id: "s1", type: "experience", title: "Work", enabled: true, data: [] },
      ],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Layout \(page flow\)/));

    const dateStyleSelect = getSelectByLabelText("Date format");
    expect(dateStyleSelect.value).toBe("");
    fireEvent.change(dateStyleSelect, { target: { value: "Mon YYYY" } });

    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({
        layout: expect.objectContaining({
          date_style: { key: "Mon YYYY", rangeSep: " – " },
        }),
      }),
    );
  });

  it("does NOT render a Date format dropdown for the profile section", () => {
    renderCustomizePanel({
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Layout \(page flow\)/));
    expect(() => getSelectByLabelText("Date format")).toThrow();
  });

  it("does NOT render a Date format dropdown for the skills section", () => {
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
    fireEvent.click(screen.getByText(/Layout \(page flow\)/));
    expect(() => getSelectByLabelText("Date format")).toThrow();
  });

  it("renders a Date format dropdown for certifications", () => {
    renderCustomizePanel({
      instances: [
        { id: "s1", type: "certifications", title: "Certs", enabled: true, data: [] },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Layout \(page flow\)/));
    const select = getSelectByLabelText("Date format");
    expect(select).toBeDefined();
  });

  it("renders a Date format dropdown for research", () => {
    renderCustomizePanel({
      instances: [
        { id: "s1", type: "research", title: "Papers", enabled: true, data: [] },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Layout \(page flow\)/));
    const select = getSelectByLabelText("Date format");
    expect(select).toBeDefined();
  });

  it("Date format dropdown shows the current value when layout.date_style is set", () => {
    renderCustomizePanel({
      instances: [
        {
          id: "s1",
          type: "experience",
          title: "Work",
          enabled: true,
          data: [],
          style: { layout: { date_style: { key: "Month YYYY", rangeSep: " – " } } } as any,
        },
      ],
    });
    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Layout \(page flow\)/));
    const dateStyleSelect = getSelectByLabelText("Date format");
    expect(dateStyleSelect.value).toBe("Month YYYY");
  });
});

describe("CustomizePanel — Document group", () => {
  it("renders the Document disclosure with accent, fonts, and spacing controls", () => {
    renderCustomizePanel();
    const group = screen.getByTestId("document-group");
    expect(group).toBeDefined();
    fireEvent.click(screen.getByText("Document"));
    expect(screen.getByTestId("document-accent-input")).toBeDefined();
    expect(screen.getByTestId("document-body-font")).toBeDefined();
    expect(screen.getByTestId("document-spacing-compact")).toBeDefined();
    expect(screen.getByTestId("document-spacing-comfortable")).toBeDefined();
    expect(screen.getByTestId("document-spacing-minimal")).toBeDefined();
  });

  it("changing the accent color hex calls onCustomizationsChange with the new value", () => {
    const onCustomizationsChange = vi.fn();
    renderCustomizePanel({ onCustomizationsChange });
    fireEvent.click(screen.getByText("Document"));
    fireEvent.change(screen.getByTestId("document-accent-input"), {
      target: { value: "#abcdef" },
    });
    expect(onCustomizationsChange).toHaveBeenCalledWith(
      expect.objectContaining({ accent_color: "#abcdef" }),
    );
  });

  it("selecting a different body font calls onCustomizationsChange with the new value", () => {
    const onCustomizationsChange = vi.fn();
    renderCustomizePanel({ onCustomizationsChange });
    fireEvent.click(screen.getByText("Document"));
    fireEvent.change(screen.getByTestId("document-body-font"), {
      target: { value: "Inter, system-ui, sans-serif" },
    });
    expect(onCustomizationsChange).toHaveBeenCalledWith(
      expect.objectContaining({ body_font: "Inter, system-ui, sans-serif" }),
    );
  });
});

describe("T48: customization panel switches via tab bar in BuilderPage", () => {
  it("is hidden in Content tab by default", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.queryByText(/Style:/)).toBeNull());
  });

  it("appears after clicking Customize tab", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.getByText("Customize")).toBeDefined());
    fireEvent.click(screen.getByText("Customize"));
    await waitFor(() => expect(screen.getByText("Layout")).toBeDefined());
  });

  it("hides when switching back to Content tab", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.getByText("Customize")).toBeDefined());
    fireEvent.click(screen.getByText("Customize"));
    await waitFor(() => expect(screen.getByText("Layout")).toBeDefined());
    fireEvent.click(screen.getByText("Content"));
    await waitFor(() => expect(screen.queryByText(/Layout \(page flow\)/)).toBeNull());
  });
});

afterEach(() => {
  useSupportStore.getState().reset();
});

  it("Field style toggles are paired with their own labels and write style.text", () => {
    const onUpdateStyle = vi.fn();
    renderCustomizePanel({
      onUpdateStyle,
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Field styles/));

    // Each checkbox is wrapped by its own label, so the label text sits
    // next to its checkbox (the Italic label is not orphaned beside the
    // Bold checkbox). Scope to the "Name" field row — every field row has
    // its own toggles.
    const nameRow = screen.getByText("Name").closest("div.rounded") as HTMLElement;
    const boldCheckbox = nameRow.querySelector('input[type="checkbox"]') as HTMLInputElement;
    const italicCheckbox = nameRow.querySelectorAll('input[type="checkbox"]')[1] as HTMLInputElement;
    expect(boldCheckbox.type).toBe("checkbox");
    expect(italicCheckbox.type).toBe("checkbox");

    fireEvent.click(boldCheckbox);
    fireEvent.click(italicCheckbox);

    expect(onUpdateStyle).toHaveBeenCalled();
    const style = onUpdateStyle.mock.calls[0][1] as { text?: Record<string, { bold?: boolean; italic?: boolean }> };
    expect(style.text).toBeDefined();
  });

  it("Field style color is a compact swatch+hex unit in one row", () => {
    renderCustomizePanel({
      instances: [{ id: "s1", type: "profile", title: "John", enabled: true, data: {} }],
    });

    fireEvent.click(screen.getByTestId("zone-section-s1"));
    fireEvent.click(screen.getByText(/Field styles/));

    const nameRow = screen.getByText("Name").closest("div.rounded") as HTMLElement;
    const hexInput = nameRow.querySelector('input[type="text"]') as HTMLInputElement;
    const colorInput = nameRow.querySelector('input[type="color"]') as HTMLInputElement;
    // Swatch and hex sit in the same label row (flex), not a full-width row.
    const label = hexInput.closest("label");
    expect(label).not.toBeNull();
    expect(label!.contains(colorInput)).toBe(true);
  });
