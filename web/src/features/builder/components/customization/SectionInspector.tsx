/**
 * SectionInspector — the adapter between the section-style JSON and the
 * controls that edit it.
 *
 * The individual groups own presentation and section-specific visibility.
 * This component owns the shared patching rules so every control preserves
 * the same inheritance semantics: an empty value means "use the default".
 */

import { useMemo } from "react";
import type {
  LayoutHints,
  SectionInstance,
  SectionInstanceStyle,
  SectionPolicy,
  SubsectionStyle,
  TextStyle,
  TypographyRole,
} from "@/shared/cv/schema";
import { ink, ruleDefault } from "@/styles/tokens";
import { fieldsForInstance } from "../../domain/customization/fieldsForInstance";
import { effectiveStyle } from "../../domain/customization/cascade";
import AppearanceGroup from "./groups/AppearanceGroup";
import BodyTextGroup from "./groups/BodyTextGroup";
import { AlignmentGroup, DatesGroup, PageBreakGroup } from "./groups/LayoutGroups";
import FieldOverridesGroup from "./groups/FieldOverridesGroup";
import HeadingGroup from "./groups/HeadingGroup";
import SpacingGroup from "./groups/SpacingGroup";
import { updateAxis, updateTextStyle, updateTypographyAxis } from "./groups/stylePatches";

interface Props {
  instance: SectionInstance;
  inheritedBodyFont: string | null;
  inheritedHeadingFont: string | null;
  inheritedAccent: string | null;
  onChange: (next: SectionInstanceStyle) => void;
}

export default function SectionInspector({
  instance,
  inheritedBodyFont,
  inheritedHeadingFont,
  inheritedAccent,
  onChange,
}: Props) {
  const style = useMemo(() => effectiveStyle(instance.type, instance.style), [instance.type, instance.style]);
  const fields = useMemo(() => fieldsForInstance(instance), [instance]);
  const rawStyle = instance.style ?? {};

  const updateSubsection = (partial: Partial<SubsectionStyle>) => {
    onChange(updateAxis(rawStyle, "subsection", partial));
  };

  const updateLayout = (partial: Partial<LayoutHints>) => {
    onChange(updateAxis(rawStyle, "layout", partial));
  };

  const updatePolicy = (partial: Partial<SectionPolicy>) => {
    onChange(updateAxis(rawStyle, "policy", partial));
  };

  const updateTypography = (role: "heading" | "body", partial: Partial<TypographyRole>) => {
    onChange(updateTypographyAxis(rawStyle, role, partial));
  };

  const updateText = (key: string, value: TextStyle | undefined) => {
    onChange(updateTextStyle(rawStyle, key, value));
  };

  const groupProps = {
    instance,
    style,
    rawStyle,
    inheritedBodyFont,
    inheritedHeadingFont,
    inheritedAccent,
    onChange,
    updateSubsection,
    updateLayout,
    updatePolicy,
    updateTypography,
    updateText,
  };

  return (
    <div className="space-y-3">
      <HeadingGroup {...groupProps} />
      <AppearanceGroup {...groupProps} />
      <BodyTextGroup {...groupProps} />
      <SpacingGroup {...groupProps} />
      <PageBreakGroup {...groupProps} />
      <DatesGroup {...groupProps} />
      <AlignmentGroup {...groupProps} />
      <FieldOverridesGroup {...groupProps} fields={fields} />
      <button
        type="button"
        onClick={() => onChange({})}
        className="w-full rounded border px-3 py-1.5 text-xs"
        style={{ borderColor: ruleDefault, color: ink.ink3 }}
      >
        Reset this section
      </button>
    </div>
  );
}
