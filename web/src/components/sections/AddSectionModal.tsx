import { User, Briefcase, GraduationCap, Wrench, FolderKanban, Globe, Award, BookOpen, Plus } from "lucide-react";
import { SECTION_LABELS, SECTION_TYPES } from "../../lib/sections/types";
import Modal from "../common/Modal";

interface Props {
  open: boolean;
  onClose: () => void;
  onSelect: (type: string) => void;
}

const SECTION_ICONS: Record<string, React.ReactNode> = {
  profile: <User className="h-6 w-6" />,
  experience: <Briefcase className="h-6 w-6" />,
  education: <GraduationCap className="h-6 w-6" />,
  skills: <Wrench className="h-6 w-6" />,
  projects: <FolderKanban className="h-6 w-6" />,
  languages: <Globe className="h-6 w-6" />,
  certifications: <Award className="h-6 w-6" />,
  research: <BookOpen className="h-6 w-6" />,
  extras: <Plus className="h-6 w-6" />,
};

export default function AddSectionModal({ open, onClose, onSelect }: Props) {
  return (
    <Modal open={open} onClose={onClose}>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Add Section</h2>
      <div className="grid grid-cols-3 gap-3">
        {(SECTION_TYPES as unknown as string[]).map((type) => (
          <button
            key={type}
            onClick={() => { onSelect(type); onClose(); }}
            className="flex flex-col items-center gap-2 rounded-lg border border-gray-200 p-4 text-sm text-gray-700 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
          >
            {SECTION_ICONS[type]}
            <span>{SECTION_LABELS[type] || type}</span>
          </button>
        ))}
      </div>
    </Modal>
  );
}
