// Section registry — Editor-only.

import ProfileEditor from "./profile/ProfileEditor";
import ExperienceEditor from "./experience/ExperienceEditor";
import EducationEditor from "./education/EducationEditor";
import SkillsEditor from "./skills/SkillsEditor";
import ProjectsEditor from "./projects/ProjectsEditor";
import LanguagesEditor from "./languages/LanguagesEditor";
import CertificationsEditor from "./certifications/CertificationsEditor";
import ResearchEditor from "./research/ResearchEditor";

type EditorProps = { data: any; onChange: (data: any) => void };

interface SectionEditorComponent {
  Editor: (props: EditorProps) => React.JSX.Element;
}

const sectionMap: Record<string, SectionEditorComponent> = {
  profile: { Editor: ProfileEditor },
  experience: { Editor: ExperienceEditor },
  education: { Editor: EducationEditor },
  skills: { Editor: SkillsEditor },
  projects: { Editor: ProjectsEditor },
  languages: { Editor: LanguagesEditor },
  certifications: { Editor: CertificationsEditor },
  research: { Editor: ResearchEditor },
};

export function getSectionComponent(type: string): SectionEditorComponent | null {
  return sectionMap[type] || null;
}

export function renderSectionEditor(type: string, data: any, onChange: (data: any) => void) {
  const comp = sectionMap[type];
  if (!comp) return null;
  return <comp.Editor data={data} onChange={onChange} />;
}

export { sectionMap };
export type { SectionEditorComponent };
