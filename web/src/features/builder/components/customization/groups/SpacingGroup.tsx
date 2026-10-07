import TokenPicker from "../controls/TokenPicker";
import { ink } from "@/styles/tokens";
import { Group } from "./Controls";
import type { SectionStyleGroupProps } from "./types";

export default function SpacingGroup({ instance, style, inheritedEntryGap, inheritedFieldGap, updateSubsection }: SectionStyleGroupProps) {
  const entryGap = style.subsection?.entry_gap ?? null;
  const fieldGap = style.subsection?.field_gap ?? null;

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
        <div className="space-y-1">
          <TokenPicker
            label="Between entries"
            value={entryGap}
            onChange={(tok) => updateSubsection({ entry_gap: tok })}
            testId={`spacing-entries-${instance.id}`}
          />
          {entryGap === null && (
            <InheritedGap source={inheritedEntryGap.source} pixels={inheritedEntryGap.pixels} testId={`inherited-entry-gap-${instance.id}`} />
          )}
        </div>
      )}
      <div className="space-y-1">
        <TokenPicker
          label="Between fields"
          value={fieldGap}
          onChange={(tok) => updateSubsection({ field_gap: tok })}
          testId={`spacing-fields-${instance.id}`}
        />
        {fieldGap === null && (
          <InheritedGap source={inheritedFieldGap.source} pixels={inheritedFieldGap.pixels} testId={`inherited-field-gap-${instance.id}`} />
        )}
      </div>
    </Group>
  );
}

function InheritedGap({ source, pixels, testId }: { source: string; pixels: number; testId: string }) {
  return (
    <p data-testid={testId} className="text-[11px] leading-4" style={{ color: ink.ink3 }}>
      {source} ({pixels} px)
    </p>
  );
}
