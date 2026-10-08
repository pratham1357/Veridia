import { useEffect, useState } from "react";
import { differenceUrl } from "../services/api";

/** Stretched |original - processed| image. The server reports the unstretched peak difference in a header. */
export default function DifferenceImage({ originalId, processedId }: { originalId: string; processedId: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [peak, setPeak] = useState<number | null>(null);

  useEffect(() => {
    let url: string | null = null;
    let cancelled = false;
    fetch(differenceUrl(originalId, processedId))
      .then(async (res) => {
        if (!res.ok || cancelled) return;
        setPeak(Number(res.headers.get("X-Max-Difference")));
        url = URL.createObjectURL(await res.blob());
        setSrc(url);
      })
      .catch(() => setSrc(null));
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [originalId, processedId]);

  if (!src) return null;
  return (
    <div className="min-w-0 flex-1">
      <div className="mb-2 text-xs uppercase tracking-wider text-slate-500">Difference (stretched)</div>
      <img src={src} alt="Difference image" style={{ imageRendering: "pixelated" }} className="max-h-72 w-full rounded border border-slate-800 bg-black object-contain" />
      <p className="mt-2 text-xs text-slate-500">
        Brightness is scaled so the largest per-pixel change ({peak === 0 ? "none" : `±${peak}`}) is white. Use it to see <em>where</em> changes are, not how large.
      </p>
    </div>
  );
}
