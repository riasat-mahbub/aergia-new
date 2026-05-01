import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import ZoneLayoutBar from "./ZoneLayoutBar";
import type { LayoutConfig } from "../../lib/sections/types";

interface ZonesSectionProps {
  layoutConfig: LayoutConfig | null;
  onChange: (config: LayoutConfig) => void;
  templateLayoutConfig?: LayoutConfig | null;
  title?: string;
  assets?: Record<string, string>;
}

export default function ZonesSection({
  layoutConfig,
  onChange,
  templateLayoutConfig,
  title = "Zones & Layout",
  assets,
}: ZonesSectionProps) {
  const [open, setOpen] = useState(true);

  return (
    <div className="mb-4 rounded-lg border border-gray-200">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between rounded-t-lg px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 hover:bg-gray-50"
      >
        {title}
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="h-3 w-3" />
        </motion.div>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="border-t p-3">
              {layoutConfig?.zones?.length ? (
                <ZoneLayoutBar layoutConfig={layoutConfig} onChange={onChange} assets={assets} />
              ) : (
                <div className="py-2 text-center">
                  <p className="mb-2 text-xs text-gray-400">No zones configured</p>
                </div>
              )}
              {templateLayoutConfig &&
                layoutConfig !== templateLayoutConfig && (
                  <button
                    onClick={() => onChange(templateLayoutConfig)}
                    className="mt-2 text-xs text-gray-400 hover:text-blue-600"
                  >
                    Reset to template defaults
                  </button>
                )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}