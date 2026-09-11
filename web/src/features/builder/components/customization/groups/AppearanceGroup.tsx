import ColorChip from "../controls/ColorChip";
import { Group, Row } from "./Controls";
import type { SectionStyleGroupProps } from "./types";

export default function AppearanceGroup({ rawStyle, style, updateSubsection }: SectionStyleGroupProps) {
  return (
    <Group title="Appearance">
      <Row label="Section background">
        <ColorChip
          value={style.subsection?.background_color ?? null}
          onChange={(next) => updateSubsection({ background_color: next })}
          label="Section background"
          showRevert={!!rawStyle.subsection?.background_color}
          onRevert={() => updateSubsection({ background_color: null })}
        />
      </Row>
    </Group>
  );
}
