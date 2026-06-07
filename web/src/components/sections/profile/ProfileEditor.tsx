import type { ProfileData } from "../../../lib/sections/types";

interface Props {
  data: ProfileData;
  onChange: (data: ProfileData) => void;
}

export default function ProfileEditor({ data, onChange }: Props) {
  const update = (key: keyof ProfileData, value: string) => {
    onChange({ ...data, [key]: value });
  };

  const inputCls = "mt-1 w-full rounded border px-2 py-1.5 text-sm";

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-xs font-medium text-gray-600">Full Name</label>
        <input
          type="text"
          value={data.name || ""}
          onChange={(e) => update("name", e.target.value)}
          className={inputCls}
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600">Professional Title</label>
        <input
          type="text"
          value={data.title || ""}
          onChange={(e) => update("title", e.target.value)}
          className={inputCls}
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600">Email</label>
        <input
          type="email"
          value={data.email || ""}
          onChange={(e) => update("email", e.target.value)}
          className={inputCls}
        />
        <label className="mt-1 inline-flex items-center gap-1 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={data.email_link ?? true}
            onChange={(e) => onChange({ ...data, email_link: e.target.checked })}
          />
          Make email clickable
        </label>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600">Phone</label>
        <input
          type="text"
          value={data.phone || ""}
          onChange={(e) => update("phone", e.target.value)}
          className={inputCls}
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600">Location</label>
        <input
          type="text"
          value={data.location || ""}
          onChange={(e) => update("location", e.target.value)}
          className={inputCls}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs font-medium text-gray-600">Site Text</label>
          <input
            type="text"
            value={data.site_text || ""}
            onChange={(e) => update("site_text", e.target.value)}
            placeholder="e.g. Personal Site"
            className={inputCls}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600">Site URL</label>
          <input
            type="text"
            value={data.site_url || ""}
            onChange={(e) => update("site_url", e.target.value)}
            placeholder="https://example.com"
            className={inputCls}
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600">Summary</label>
        <textarea
          value={data.summary || ""}
          onChange={(e) => update("summary", e.target.value)}
          rows={3}
          className={inputCls}
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600">Photo URL</label>
        <input
          type="text"
          value={data.photo_url || ""}
          onChange={(e) => update("photo_url", e.target.value)}
          className={inputCls}
        />
      </div>
    </div>
  );
}
