import TokenPicker from "../controls/TokenPicker";
import { Group } from "./Controls";
import { spacingTokenToSpacingToken } from "./stylePatches";
import type { SectionStyleGroupProps } from "./types";

export default function SpacingGroup({ instance, style, updateSubsection }: SectionStyleGroupProps) {
  return (
    <Group title="Spacing">
      <TokenPicker
        label="Above"
        value={spacingTokenToSpacingToken(style.subsection?.spacing_before)}
        onChange={(tok) => updateSubsection({ spacing_before: tok })}
        testId={`spacing-above-${instance.id}`}
      />
      <TokenPicker
        label="Below"
        value={spacingTokenToSpacingToken(style.subsection?.spacing_after)}
        onChange={(tok) => updateSubsection({ spacing_after: tok })}
        testId={`spacing-below-${instance.id}`}
      />
      {instance.type !== "profile" && (
        <TokenPicker
          label="Between entries"
          value={spacingTokenToSpacingToken(style.subsection?.entry_gap)}
          onChange={(tok) => updateSubsection({ entry_gap: tok })}
          testId={`spacing-entries-${instance.id}`}
        />
      )}
      <TokenPicker
        label="Between fields"
        value={spacingTokenToSpacingToken(style.subsection?.field_gap)}
        onChange={(tok) => updateSubsection({ field_gap: tok })}
        testId={`spacing-fields-${instance.id}`}
      />
    </Group>
  );
}
