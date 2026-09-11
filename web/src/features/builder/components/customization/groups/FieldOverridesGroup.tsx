import type { FieldRow } from "../../../domain/customization/fieldsForInstance";
import TypographyRow from "../controls/TypographyRow";
import { Group } from "./Controls";
import type { SectionStyleGroupProps } from "./types";

export default function FieldOverridesGroup({ instance, fields, style, updateText }: SectionStyleGroupProps & { fields: FieldRow[] }) {
  if (fields.length === 0) return null;
  return (
    <Group title="Advanced field overrides">
      {fields.map((field) => (
        <TypographyRow
          key={field.key}
          label={field.label}
          sample={field.sample}
          current={style.text?.[field.key] ?? {}}
          isRichText={field.isRichText}
          onChange={(next) => updateText(field.key, next)}
          testId={`typography-${instance.id}-${field.key}`}
        />
      ))}
    </Group>
  );
}
