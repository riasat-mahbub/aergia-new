import type { ComponentType, ReactNode } from "react";

import type { SectionType } from "@/shared/cv/sectionCatalog";
import ProfileEditor from "./profile/ProfileEditor";
import ExperienceEditor from "./experience/ExperienceEditor";
import EducationEditor from "./education/EducationEditor";
import SkillsEditor from "./skills/SkillsEditor";
import ProjectsEditor from "./projects/ProjectsEditor";
import LanguagesEditor from "./languages/LanguagesEditor";
import CertificationsEditor from "./certifications/CertificationsEditor";
import ExtrasEditor from "./extras/ExtrasEditor";
import ResearchEditor from "./research/ResearchEditor";
import type {
  SectionEditorActions,
  SectionEditorMode,
} from "./types";

export type SectionEditorProps = {
  data: unknown;
  onChange: (data: unknown) => void;
  mode?: SectionEditorMode;
  actions?: SectionEditorActions;
};

export type SectionEditorComponent = ComponentType<SectionEditorProps>;

/**
 * The registry is closed over the supported section types. Runtime input is
 * narrowed before indexing, so an unknown persisted section fails closed
 * instead of becoming an accidental `Record<string, ...>` lookup.
 */
const sectionRegistry = {
  // The dynamic boundary receives persisted `unknown` data. Each editor
  // keeps its concrete entry type internally; these are the only casts at
  // the boundary between the closed registry and those typed components.
  profile: ProfileEditor as unknown as SectionEditorComponent,
  experience: ExperienceEditor as unknown as SectionEditorComponent,
  education: EducationEditor as unknown as SectionEditorComponent,
  skills: SkillsEditor as unknown as SectionEditorComponent,
  projects: ProjectsEditor as unknown as SectionEditorComponent,
  languages: LanguagesEditor as unknown as SectionEditorComponent,
  extras: ExtrasEditor as unknown as SectionEditorComponent,
  certifications: CertificationsEditor as unknown as SectionEditorComponent,
  research: ResearchEditor as unknown as SectionEditorComponent,
} satisfies Record<SectionType, SectionEditorComponent>;

function isSectionType(type: string): type is SectionType {
  return type in sectionRegistry;
}

export function getSectionComponent(type: string): SectionEditorComponent | null {
  return isSectionType(type) ? sectionRegistry[type] : null;
}

export function renderSectionEditor(
  type: string,
  data: unknown,
  onChange: (data: unknown) => void,
  mode: SectionEditorMode = "section",
  actions?: SectionEditorActions,
): ReactNode {
  const Editor = getSectionComponent(type);
  if (!Editor) return null;
  return <Editor data={data} onChange={onChange} mode={mode} actions={actions} />;
}

export { sectionRegistry };
