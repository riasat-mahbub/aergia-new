import ProfileEditor from "./profile/ProfileEditor";
import ProfileRenderer from "./profile/ProfileRenderer";
import ExperienceEditor from "./experience/ExperienceEditor";
import ExperienceRenderer from "./experience/ExperienceRenderer";
import EducationEditor from "./education/EducationEditor";
import EducationRenderer from "./education/EducationRenderer";
import SkillsEditor from "./skills/SkillsEditor";
import SkillsRenderer from "./skills/SkillsRenderer";
import ProjectsEditor from "./projects/ProjectsEditor";
import ProjectsRenderer from "./projects/ProjectsRenderer";
import LanguagesEditor from "./languages/LanguagesEditor";
import LanguagesRenderer from "./languages/LanguagesRenderer";
import CertificationsEditor from "./certifications/CertificationsEditor";
import CertificationsRenderer from "./certifications/CertificationsRenderer";
import ResearchEditor from "./research/ResearchEditor";
import ResearchRenderer from "./research/ResearchRenderer";
import type { SectionStyle } from "../../lib/sections/types";
type EditorProps<T> = { data: T | undefined; onChange: (data: T) => void };
type RendererProps<T> = { data: T | undefined; style?: SectionStyle };

interface SectionComponent<T = unknown> {
  Editor: (props: EditorProps<T>) => React.JSX.Element;
  Renderer: (props: RendererProps<T>) => React.JSX.Element;
}

const sectionMap: Record<string, SectionComponent<any>> = {
  profile: { Editor: ProfileEditor, Renderer: ProfileRenderer },
  experience: { Editor: ExperienceEditor, Renderer: ExperienceRenderer },
  education: { Editor: EducationEditor, Renderer: EducationRenderer },
  skills: { Editor: SkillsEditor, Renderer: SkillsRenderer },
  projects: { Editor: ProjectsEditor, Renderer: ProjectsRenderer },
  languages: { Editor: LanguagesEditor, Renderer: LanguagesRenderer },
  certifications: { Editor: CertificationsEditor, Renderer: CertificationsRenderer },
  research: { Editor: ResearchEditor, Renderer: ResearchRenderer },
};

export function getSectionComponent(type: string): SectionComponent | null {
  return sectionMap[type] || null;
}

export function renderSectionEditor(type: string, data: any, onChange: (data: any) => void) {
  const comp = sectionMap[type];
  if (!comp) return null;
  return <comp.Editor data={data} onChange={onChange} />;
}

export function renderSectionPreview(type: string, data: any, style?: SectionStyle) {
  const comp = sectionMap[type];
  if (!comp) return null;
  return <comp.Renderer data={data} style={style} />;
}

export { sectionMap };
export type { SectionComponent };
