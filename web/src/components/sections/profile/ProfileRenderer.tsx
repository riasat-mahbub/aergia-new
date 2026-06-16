import { SocialIcon } from "../../../lib/sections/socialIcons";

import type { ProfileData } from "../../../lib/sections/types";

interface Props {
  data: ProfileData;
}

export default function ProfileRenderer({ data }: Props) {
  const linkCls = "text-xs text-blue-600 hover:underline";

  return (
    <div>
      {data.photo_url && (
        <img src={data.photo_url} alt="" className="mb-3 h-20 w-20 rounded-full object-cover" />
      )}
      <h2 className="text-xl font-bold">{data.name || "Your Name"}</h2>
      <p className="text-sm text-gray-600">{data.title}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500">
        {data.email &&
          (data.email_link !== false ? (
            <span className={linkCls}>{data.email}</span>
          ) : (
            <span>{data.email}</span>
          ))}
        {data.phone && <span>{data.phone}</span>}
        {data.location && <span>{data.location}</span>}
        {data.site_url && (
          <span className={linkCls}>
            {data.site_text || data.site_url}
          </span>
        )}
      </div>
      {(data.social_links ?? []).length > 0 && (
        <div className="mt-2 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-xs text-gray-700">
          {(data.social_links ?? []).map((link, i) => (
            link.url ? (
              <a
                key={i}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 hover:underline"
              >
                <SocialIcon name={link.icon} className="h-3.5 w-3.5" />
                <span>{link.label || link.url}</span>
              </a>
            ) : (
              <span key={i} className="inline-flex items-center gap-1 text-gray-400">
                <SocialIcon name={link.icon} className="h-3.5 w-3.5" />
                <span>{link.label || "(empty URL)"}</span>
              </span>
            )
          ))}
        </div>
      )}
    </div>
  );
}
