/**
 * REMOVED in Phase 2 — see
 * tracker/tasks/TASK-01KZJ0PHASE2QA-phase-3-template-creator-and-global-customizations.md
 *
 * v2 template creation lives in `POST /templates/user` (uploads a manifest.json).
 * This wizard wrote the legacy {colors, fonts, spacing, flags} default_customizations
 * shape, which Phase 2 now rejects at the Customizations boundary. It is stubbed
 * here until Phase 3 rebuilds it against the v2 TemplateManifest + Customizations.
 *
 * Props are accepted (and ignored) for API compatibility with `TemplateCreatorPage`,
 * which still passes the old `initialManifest / onManifestChange / onComplete /
 * onSave` callbacks. To restore: git checkout HEAD -- web/src/components/template-creator/TemplateWizard.tsx
 */

export default function TemplateWizard(_props?: Record<string, unknown>) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <h3 className="text-sm font-medium text-amber-900">Template creator is being rebuilt</h3>
      <p className="mt-1 text-xs text-amber-700">
        The legacy template wizard was incompatible with the v2 manifest pipeline and is
        removed in Phase 2. See the Phase 3 task for the rewrite.
      </p>
    </div>
  );
}
