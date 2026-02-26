interface ValidationErrorsProps {
  errors: Record<string, string>;
  field?: string;
}

export default function ValidationErrors({ errors, field }: ValidationErrorsProps) {
  if (field) {
    const error = errors[field];
    if (!error) return null;
    return <p className="mt-1 text-xs text-red-500">{error}</p>;
  }

  if (Object.keys(errors).length === 0) return null;

  return (
    <div className="mb-3 rounded border border-red-200 bg-red-50 p-2">
      <ul className="list-inside list-disc text-xs text-red-600">
        {Object.entries(errors).map(([key, msg]) => (
          <li key={key}>{msg}</li>
        ))}
      </ul>
    </div>
  );
}
