import { Plus, Trash2 } from "lucide-react";
import { SOCIAL_ICON_OPTIONS } from "../../../lib/sections/socialIcons";
import type { ProfileData, SocialLink } from "../../../lib/sections/types";


interface Props {
  data: ProfileData;
  onChange: (data: ProfileData) => void;
}
export default function ProfileEditor({ data, onChange }: Props) {

  const update = (key: keyof ProfileData, value: string) => {
    onChange({ ...data, [key]: value });
  };
  const updateSocialLinks = (next: SocialLink[]) => {
    onChange({ ...data, social_links: next });
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
        <label className="block text-xs font-medium text-gray-600">Social Links</label>
        <div className="mt-1 space-y-2">
          {(data.social_links ?? []).map((link, i) => (
            <div key={i} className="grid grid-cols-[1fr_2fr_auto] gap-2">
              <input
                type="text"
                placeholder="Label"
                value={link.label}
                onChange={(e) => {
                  const next = [...data.social_links];
                  next[i] = { ...link, label: e.target.value };
                  updateSocialLinks(next);
                }}
                className={inputCls}
              />
              <input
                type="text"
                placeholder="https://example.com"
                value={link.url}
                onChange={(e) => {
                  const next = [...data.social_links];
                  next[i] = { ...link, url: e.target.value };
                  updateSocialLinks(next);
                }}
                className={inputCls}
              />
              <button
                type="button"
                onClick={() => updateSocialLinks(data.social_links.filter((_, j) => j !== i))}
                className="rounded border px-2 py-1.5 text-gray-500 hover:bg-gray-50"
                aria-label="Remove social link"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
              <select
                value={link.icon}
                onChange={(e) => {
                  const next = [...data.social_links];
                  next[i] = { ...link, icon: e.target.value as SocialLink["icon"] };
                  updateSocialLinks(next);
                }}
                className="col-span-3 mt-1 w-full rounded border px-2 py-1.5 text-sm"
              >
                {SOCIAL_ICON_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              updateSocialLinks([...(data.social_links ?? []), { label: "", url: "", icon: "globe" }])
            }
            className="inline-flex items-center gap-1 rounded border px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
          >
            <Plus className="h-3 w-3" />
            Add link
          </button>
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
