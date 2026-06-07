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
            <a href={`mailto:${data.email}`} className={linkCls}>
              {data.email}
            </a>
          ) : (
            <span>{data.email}</span>
          ))}
        {data.phone && <span>{data.phone}</span>}
        {data.location && <span>{data.location}</span>}
        {data.site_url && (
          <a
            href={data.site_url}
            className={linkCls}
            target="_blank"
            rel="noopener noreferrer"
          >
            {data.site_text || data.site_url}
          </a>
        )}
      </div>
      {data.summary && <p className="mt-3 text-sm text-gray-700">{data.summary}</p>}
    </div>
  );
}
