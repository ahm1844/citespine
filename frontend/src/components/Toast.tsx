import React, { useEffect, useRef } from "react";

type ToastMsg = { id: number; text: string; kind?: "ok" | "err" | "info" };

/** Helper you already use in App */
export function makeToaster(setter: React.Dispatch<React.SetStateAction<ToastMsg[]>>) {
  return (text: string, kind: ToastMsg["kind"] = "info") =>
    setter((list) => [...list, { id: Date.now(), text, kind }]);
}

const AUTO_MS = 3500;

export default function Toast({
  items,
  onClose,
}: {
  items: ToastMsg[];
  onClose: (id: number) => void;
}) {
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());
  const scheduledRef = useRef<Set<number>>(new Set());

  // Schedule timers once per toast id
  useEffect(() => {
    items.forEach((t) => {
      if (!scheduledRef.current.has(t.id)) {
        scheduledRef.current.add(t.id);
        const tt = setTimeout(() => {
          timersRef.current.delete(t.id);
          onClose(t.id);
        }, AUTO_MS);
        timersRef.current.set(t.id, tt);
      }
    });
  }, [items, onClose]);

  // Clean up all timers on unmount
  useEffect(() => {
    return () => {
      timersRef.current.forEach((tt) => clearTimeout(tt));
      timersRef.current.clear();
      scheduledRef.current.clear();
    };
  }, []);

  return (
    <div className="toast-wrap">
      {items.map((t) => (
        <div
          key={t.id}
          className={`toast ${t.kind || "info"}`}
          onClick={() => {
            const tt = timersRef.current.get(t.id);
            if (tt) clearTimeout(tt);
            timersRef.current.delete(t.id);
            scheduledRef.current.delete(t.id);
            onClose(t.id);
          }}
          role="status"
          aria-live="polite"
        >
          {t.text}
        </div>
      ))}
    </div>
  );
}
