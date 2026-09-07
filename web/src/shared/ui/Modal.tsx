import { useEffect, useCallback, useRef, type ReactNode, type RefObject } from "react";
import { motion, AnimatePresence } from "motion/react";

interface Props {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  size?: "default" | "wide";
  titleId?: string;
  descriptionId?: string;
  initialFocusRef?: RefObject<HTMLElement | null>;
}

const PANEL_WIDTH = {
  default: "max-w-lg",
  wide: "max-w-3xl",
} as const;

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type=hidden])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[contenteditable=\"true\"]",
  "[tabindex]:not([tabindex=\"-1\"])",
].join(", ");

function getFocusableElements(panel: HTMLElement): HTMLElement[] {
  return Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (element) => element.getAttribute("aria-hidden") !== "true",
  );
}

export default function Modal({
  open,
  onClose,
  children,
  size = "default",
  titleId,
  descriptionId,
  initialFocusRef,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const panel = panelRef.current;
      if (!panel) return;

      if (e.key === "Escape") {
        e.preventDefault();
        onCloseRef.current();
        return;
      }

      if (e.key !== "Tab") return;

      const focusable = getFocusableElements(panel);
      if (focusable.length === 0) {
        e.preventDefault();
        panel.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const activeElement = document.activeElement;

      if (!panel.contains(activeElement)) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      } else if (e.shiftKey && activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    },
    [],
  );

  useEffect(() => {
    if (!open) return;

    previousFocusRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const previousOverflow = document.body.style.overflow;
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    const focusFrame = window.requestAnimationFrame(() => {
      const requestedFocus = initialFocusRef?.current;
      if (requestedFocus && requestedFocus.getAttribute("aria-disabled") !== "true") {
        requestedFocus.focus();
        return;
      }

      const firstFocusable = panelRef.current && getFocusableElements(panelRef.current)[0];
      (firstFocusable ?? panelRef.current)?.focus();
    });

    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;

      const previousFocus = previousFocusRef.current;
      previousFocusRef.current = null;
      if (previousFocus && document.contains(previousFocus)) previousFocus.focus();
    };
  }, [open, handleKeyDown, initialFocusRef]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/50"
            onClick={onClose}
          />
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            tabIndex={-1}
            className={`relative z-10 w-[calc(100%-2rem)] ${PANEL_WIDTH[size]} max-h-[calc(100vh-2rem)] overflow-hidden rounded-lg bg-white p-6 shadow-xl focus:outline-none`}
          >
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
