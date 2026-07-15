import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Gives a hand-rolled (non-Radix) modal the same baseline keyboard/focus
 * behavior Radix's Dialog provides for free: Escape closes it, focus moves
 * into it on open and is trapped inside while it's open, and focus returns
 * to whatever triggered it on close (AccessibilityAudit.md Phase 8).
 *
 * `isOpen` defaults to true for dialogs that are their own component and
 * only ever mounted while open (e.g. `{selected && <Panel />}`) — for a
 * dialog whose markup instead sits inline behind `{open && (...)}` in an
 * always-mounted parent, pass that same `open` boolean through explicitly.
 */
export function useDialogA11y(onClose: () => void, isOpen = true) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const container = containerRef.current;

    const focusable = container?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    (focusable?.[0] ?? container)?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !container) return;

      const elements = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
      if (elements.length === 0) return;

      const first = elements[0];
      const last = elements[elements.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onClose is read fresh via closure each time isOpen flips true; re-subscribing on every render (not just on open/close) would rebind the listener and re-run focus capture mid-session
  }, [isOpen]);

  return containerRef;
}
