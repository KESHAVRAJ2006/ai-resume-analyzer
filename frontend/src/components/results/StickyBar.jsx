import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, Download, Loader2, RotateCcw } from "lucide-react";
import { Button } from "../ui/Button";
import { Shell } from "../layout/Shell";
import { cn } from "../../lib/utils";
import { DURATION, EASE } from "../../lib/motion";

const BAND_DOT = {
  early: "bg-band-early",
  developing: "bg-band-developing",
  strong: "bg-band-strong",
};

/**
 * The bar that follows you down the results page.
 *
 * It only appears once the hero score has scrolled out of view - showing it
 * while the real score ring is still on screen would just be a second copy of
 * the same number.
 *
 * @param {object} props
 * @param {boolean} props.visible
 * @param {number} props.score
 * @param {string} props.band
 * @param {string} props.roleName
 * @param {"idle"|"working"|"done"} props.downloadState
 * @param {() => void} props.onDownload
 * @param {() => void} props.onRestart
 */
export function StickyBar({
  visible,
  score,
  band,
  roleName,
  downloadState,
  onDownload,
  onRestart,
}) {
  const reduced = useReducedMotion();
  const working = downloadState === "working";

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduced ? { opacity: 0 } : { opacity: 0, y: 16 }}
          transition={{ duration: DURATION.base, ease: EASE }}
          className="fixed inset-x-0 bottom-0 z-50 border-t border-line bg-base/85 backdrop-blur-md"
        >
          <Shell className="flex h-16 items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <span
                aria-hidden="true"
                className={cn("h-2 w-2 shrink-0 rounded-full", BAND_DOT[band])}
              />
              <p className="min-w-0 truncate text-small text-muted">
                <span className="font-medium tabular-nums text-primary">
                  {Math.round(score)}%
                </span>{" "}
                <span className="hidden sm:inline">match for </span>
                <span className="text-primary">{roleName}</span>
              </p>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={onRestart}
                aria-label="Analyze another resume"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">Analyze another</span>
              </Button>

              <Button size="sm" onClick={onDownload} disabled={working}>
                <DownloadIcon state={downloadState} reduced={reduced} />
                <span className="hidden sm:inline">
                  {working ? "Building PDF" : downloadState === "done" ? "Saved" : "Download PDF report"}
                </span>
                <span className="sm:hidden">PDF</span>
              </Button>
            </div>
          </Shell>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** The button's icon, which doubles as its progress indicator. */
function DownloadIcon({ state, reduced }) {
  if (state === "working") {
    return (
      <Loader2
        className={cn("h-3.5 w-3.5", !reduced && "animate-spin")}
        aria-hidden="true"
      />
    );
  }
  if (state === "done") {
    return <Check className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden="true" />;
  }
  return <Download className="h-3.5 w-3.5" aria-hidden="true" />;
}
