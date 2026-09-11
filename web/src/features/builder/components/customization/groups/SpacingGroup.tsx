import TokenPicker from "../controls/TokenPicker";
import { Group } from "./Controls";
import type { SectionStyleGroupProps } from "./types";

export default function SpacingGroup({ instance, style, updateSubsection }: SectionStyleGroupProps) {
  return (
    <Group title="Spacing">
      <TokenPicker
        label="Above"
        value={style.subsection?.spacing_before ?? null}
        onChange={(tok) => updateSubsection({ spacing_before: tok })}
        testId={`spacing-above-${instance.id}`}
      />
      <TokenPicker
        label="Below"
        value={style.subsection?.spacing_after ?? null}
        onChange={(tok) => updateSubsection({ spacing_after: tok })}
        testId={`spacing-below-${instance.id}`}
      />
      {instance.type !== "profile" && (
        <TokenPicker
          label="Between entries"
          value={style.subsection?.entry_gap ?? null}
          onChange={(tok) => updateSubsection({ entry_gap: tok })}
          testId={`spacing-entries-${instance.id}`}
        />
      )}
      <TokenPicker
        label="Between fields"
        value={style.subsection?.field_gap ?? null}
        onChange={(tok) => updateSubsection({ field_gap: tok })}
        testId={`spacing-fields-${instance.id}`}
      />
    </Group>
  );
}
