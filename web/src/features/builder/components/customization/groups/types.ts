import type {
  GlobalStyles,
  LayoutHints,
  SectionInstance,
  SectionInstanceStyle,
  SectionPolicy,
  SubsectionStyle,
  TextStyle,
  TypographyRole,
} from "@/shared/cv/schema";
import type { InheritedGapHint } from "../../../domain/customization/cascade";

export interface SectionStyleGroupProps {
  instance: SectionInstance;
  style: SectionInstanceStyle;
  rawStyle: SectionInstanceStyle;
  inheritedBodyFont: string | null;
  inheritedBodySize: GlobalStyles["body_font_size"] | null;
  inheritedBodyLineHeight: GlobalStyles["body_line_height"] | null;
  inheritedHeadingFont: string | null;
  inheritedAccent: string | null;
  inheritedEntryGap: InheritedGapHint;
  inheritedFieldGap: InheritedGapHint;
  onChange: (next: SectionInstanceStyle) => void;
  updateSubsection: (partial: Partial<SubsectionStyle>) => void;
  updateLayout: (partial: Partial<LayoutHints>) => void;
  updatePolicy: (partial: Partial<SectionPolicy>) => void;
  updateTypography: (role: "heading" | "body", partial: Partial<TypographyRole>) => void;
  updateText: (key: string, value: TextStyle | undefined) => void;
}
