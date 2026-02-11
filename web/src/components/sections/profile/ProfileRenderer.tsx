import type { ProfileData } from "../../../lib/sections/types";

interface Props {
  data: ProfileData;
}

export default function ProfileRenderer({ data }: Props) {
  return (
    <div>
      {data.photo_url && (
        <img src={data.photo_url} alt="" className="mb-3 h-20 w-20 rounded-full object-cover" />
      )}
      <h2 className="text-xl font-bold">{data.name || "Your Name"}</h2>
      <p className="text-sm text-gray-600">{data.title}</p>
      <div className="mt-2 space-y-1 text-xs text-gray-500">
        {data.email && <p>{data.email}</p>}
        {data.phone && <p>{data.phone}</p>}
        {data.location && <p>{data.location}</p>}
      </div>
      {data.summary && <p className="mt-3 text-sm text-gray-700">{data.summary}</p>}
    </div>
  );
}
