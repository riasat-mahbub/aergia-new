import type { ProfileData } from "../../../lib/sections/types";

interface Props {
  data: ProfileData;
  onChange: (data: ProfileData) => void;
}

export default function ProfileEditor({ data, onChange }: Props) {
  const fields: { key: keyof ProfileData; label: string; type?: string }[] = [
    { key: "name", label: "Full Name" },
    { key: "title", label: "Professional Title" },
    { key: "email", label: "Email", type: "email" },
    { key: "phone", label: "Phone" },
    { key: "location", label: "Location" },
    { key: "summary", label: "Summary" },
  ];

  const update = (key: keyof ProfileData, value: string) => {
    onChange({ ...data, [key]: value });
  };

  return (
    <div className="space-y-3">
      {fields.map((f) => (
        <div key={f.key}>
          <label className="block text-xs font-medium text-gray-600">{f.label}</label>
          {f.key === "summary" ? (
            <textarea
              value={data[f.key] || ""}
              onChange={(e) => update(f.key, e.target.value)}
              rows={3}
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
            />
          ) : (
            <input
              type={f.type || "text"}
              value={data[f.key] || ""}
              onChange={(e) => update(f.key, e.target.value)}
              className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
            />
          )}
        </div>
      ))}
    </div>
  );
}
