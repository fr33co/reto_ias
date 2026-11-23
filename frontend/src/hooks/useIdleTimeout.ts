import { useEffect } from "react";

const EVENTS = ["pointerdown", "keydown", "wheel", "touchstart"] as const;

/** Calls onIdle after `ms` without user input. The counter PC is shared by three shifts. */
export function useIdleTimeout(active: boolean, ms: number, onIdle: () => void) {
  useEffect(() => {
    if (!active) return;
    let timer = window.setTimeout(onIdle, ms);
    /** Restart the countdown on any user input. */
    const reset = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(onIdle, ms);
    };
    EVENTS.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    return () => {
      window.clearTimeout(timer);
      EVENTS.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [active, ms, onIdle]);
}
