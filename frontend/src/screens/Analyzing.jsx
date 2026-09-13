import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Shell } from "../components/layout/Shell";
import { cn } from "../lib/utils";
import { DURATION, EASE } from "../lib/motion";

/**
 * The stages, with how long each typically takes.
 *
 * These are an honest estimate of the pipeline, not a progress report from the
 * server - /api/analyze is a single request with no streaming, so there is
 * nothing to report. The last stage holds until the response actually lands, so
 * the UI never claims to be finished before it is.
 */
const STAGES = [
  { label: "Extracting text", ms: 900 },
  { label: "Splitting sections", ms: 700 },
  { label: "Detecting skills", ms: 1100 },
  { label: "Matching roles", ms: 1400 },
  { label: "Building your roadmap", ms: Infinity },
];

/**
 * Screen 3. Skeletons shaped like the results, plus stepped progress text.
 *
 * Skeletons mirror the real results layout so the page does not jump when the
 * data arrives - the point of a skeleton is to reserve the space, not to spin.
 */
export function Analyzing({ fileName, roleName }) {
  const [stage, setStage] = useState(0);
  const reduced = useReducedMotion();

  useEffect(() => {
    if (stage >= STAGES.length - 1) return undefined; // hold on the last stage
    const timer = setTimeout(() => setStage((current) => current + 1), STAGES[stage].ms);
    return () => clearTimeout(timer);
  }, [stage]);

  return (
    <main>
      <Shell className="py-12 sm:py-16">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-section">Analyzing your resume</h1>
          <p className="mt-2 text-body text-muted">
            <span className="text-primary">{fileName}</span> against{" "}
            <span className="text-primary">{roleName}</span>
          </p>

          {/* Stage list -------------------------------------------------- */}
          <Card className="mt-8">
            <ol className="space-y-3.5">
              {STAGES.map((item, index) => {
                const done = index < stage;
                const active = index === stage;
                return (
                  <li key={item.label} className="flex items-center gap-3">
                    <span
                      className={cn(
                        "flex h-5 w-5 shrink-0 items-center justify-center rounded-pill border transition-colors duration-200 ease-brand",
                        done && "border-accent/40 bg-accent-soft",
                        active && "border-accent/40 bg-accent-soft",
                        !done && !active && "border-line bg-elevated",
                      )}
                    >
                      {done && (
                        <Check className="h-3 w-3 text-accent-hover" strokeWidth={3} aria-hidden="true" />
                      )}
                      {active && (
                        <Loader2
                          className={cn("h-3 w-3 text-accent-hover", !reduced && "animate-spin")}
                          aria-hidden="true"
                        />
                      )}
                    </span>
                    <span
                      className={cn(
                        "text-body transition-colors duration-200 ease-brand",
                        done && "text-muted",
                        active && "text-primary",
                        !done && !active && "text-subtle",
                      )}
                    >
                      {item.label}
                      {active && <span aria-hidden="true">&hellip;</span>}
                    </span>
                  </li>
                );
              })}
            </ol>
            {/* One live region for the whole list: screen readers hear each
                stage announced once, instead of the entire list re-read. */}
            <p className="sr-only" aria-live="polite">
              {STAGES[stage].label}
            </p>
          </Card>

          {/* Skeletons --------------------------------------------------- */}
          <motion.div
            initial={reduced ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: DURATION.slow, ease: EASE, delay: 0.1 }}
            className="mt-6 space-y-4"
            aria-hidden="true"
          >
            <Card className="flex items-center gap-8">
              <Skeleton className="h-28 w-28 shrink-0 rounded-full" />
              <div className="flex-1 space-y-3">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-3 w-full max-w-sm" />
              </div>
            </Card>

            <Card className="space-y-4">
              <Skeleton className="h-3 w-32" />
              <div className="flex flex-wrap gap-2">
                {[72, 96, 64, 110, 80, 88].map((width, index) => (
                  <Skeleton key={index} className="h-7 rounded-pill" style={{ width }} />
                ))}
              </div>
            </Card>

            <Card className="space-y-3">
              <Skeleton className="h-3 w-28" />
              {[88, 72, 61, 44].map((width, index) => (
                <Skeleton key={index} className="h-6" style={{ width: `${width}%` }} />
              ))}
            </Card>
          </motion.div>
        </div>
      </Shell>
    </main>
  );
}

/**
 * A skeleton block with a shimmer sweep.
 *
 * The sweep is a gradient translated across the block, not an opacity pulse -
 * it reads as "loading" rather than "broken". Under prefers-reduced-motion the
 * global CSS rule freezes it, leaving a static grey block.
 */
function Skeleton({ className, style }) {
  return (
    <div
      style={style}
      className={cn("relative overflow-hidden rounded-control bg-elevated", className)}
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/[0.04] to-transparent" />
    </div>
  );
}
