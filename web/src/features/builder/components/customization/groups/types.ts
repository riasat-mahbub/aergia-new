import type {
  LayoutHints,
  SectionInstance,
  SectionInstanceStyle,
  SectionPolicy,
  SubsectionStyle,
  TextStyle,
  TypographyRole,
} from "@/shared/cv/schema";

export interface SectionStyleGroupProps {
  instance: SectionInstance;
  style: SectionInstanceStyle;
  rawStyle: SectionInstanceStyle;
  inheritedBodyFont: string | null;
  inheritedHeadingFont: string | null;
  inheritedAccent: string | null;
  onChange: (next: SectionInstanceStyle) => void;
  updateSubsection: (partial: Partial<SubsectionStyle>) => void;
  updateLayout: (partial: Partial<LayoutHints>) => void;
  updatePolicy: (partial: Partial<SectionPolicy>) => void;
  updateTypography: (role: "heading" | "body", partial: Partial<TypographyRole>) => void;
  updateText: (key: string, value: TextStyle | undefined) => void;
}
