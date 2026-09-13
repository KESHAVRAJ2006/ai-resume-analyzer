import { useCallback, useEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AlertCircle, Check, Download, Info, Loader2 } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Shell } from "../components/layout/Shell";
import { ScoreRing, BAND_LABEL } from "../components/results/ScoreRing";
import { SkillChips } from "../components/results/SkillChips";
import { RoleRankCard } from "../components/results/RoleRankCard";
import { GapTable } from "../components/results/GapTable";
import { RoadmapTimeline } from "../components/results/RoadmapTimeline";
import { StickyBar } from "../components/results/StickyBar";
import { downloadReport } from "../lib/api";
import { cn } from "../lib/utils";
import { DURATION, EASE, fadeUp, respectMotion, staggerChildren } from "../lib/motion";

// How long the button stays on "Saved" before returning to its normal label.
const DONE_RESET_MS = 2500;

/**
 * Screen 4.
 *
 * Hierarchy is deliberate and strict: one hero number, then the evidence
 * behind it, then what to do about it. Everything that does not serve that
 * order was cut.
 */
export function Results({ data, onRestart }) {
  const reduced = useReducedMotion();
  const heroRef = useRef(null);
  const [heroVisible, setHeroVisible] = useState(true);
  const [downloadState, setDownloadState] = useState("idle"); // idle | working | done
  const [downloadError, setDownloadError] = useState(null);
  const resetTimer = useRef(null);

  const {
    target_role: target,
    skills_found: skills,
    skills_by_category: byCategory,
    role_ranking: ranking,
    gaps,
    roadmap,
    meta,
  } = data;

  // The sticky bar appears only once the hero score has left the viewport.
  // IntersectionObserver rather than a scroll listener: no work on every frame,
  // and it stays correct if the layout reflows.
  useEffect(() => {
    const element = heroRef.current;
    if (!element) return undefined;

    const observer = new IntersectionObserver(
      ([entry]) => setHeroVisible(entry.isIntersecting),
      { rootMargin: "-64px 0px 0px 0px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Clear the pending "Saved" reset if the screen unmounts first, so the
  // timeout cannot fire setState on an unmounted component.
  useEffect(() => () => clearTimeout(resetTimer.current), []);

  const handleDownload = useCallback(async () => {
    setDownloadError(null);
    setDownloadState("working");
    try {
      await downloadReport(data);
      setDownloadState("done");
      resetTimer.current = setTimeout(() => setDownloadState("idle"), DONE_RESET_MS);
    } catch (caught) {
      if (caught.name === "AbortError") return;
      setDownloadState("idle");
      setDownloadError(caught.message);
    }
  }, [data]);

  return (
    <main className="pb-24">
      <Shell className="py-12 sm:py-16">
        <motion.div
          variants={staggerChildren(0.06)}
          initial="hidden"
          animate="visible"
          className="space-y-4"
        >
          {/* ---- Hero: the one number ------------------------------------ */}
          <motion.div ref={heroRef} variants={respectMotion(fadeUp, reduced)}>
            <Card className="overflow-hidden p-0">
              <div className="flex flex-col items-center gap-8 p-6 text-center sm:flex-row sm:items-center sm:p-8 sm:text-left">
                <ScoreRing score={target.score} band={target.band} />

                <div className="min-w-0">
                  <p className="text-label uppercase text-subtle">{target.role_name}</p>
                  <h1 className="mt-2 text-section">{BAND_LABEL[target.band]}</h1>
                  <p className="mt-2.5 max-w-prose text-body text-muted">{gaps.summary}</p>

                  {/* A second entry point for the same action. The sticky bar
                      only exists once this card has scrolled away, so without
                      this there is no way to export from the top of the page. */}
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleDownload}
                    disabled={downloadState === "working"}
                    className="mt-5"
                  >
                    {downloadState === "working" ? (
                      <Loader2
                        className={cn("h-3.5 w-3.5", !reduced && "animate-spin")}
                        aria-hidden="true"
                      />
                    ) : downloadState === "done" ? (
                      <Check className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden="true" />
                    ) : (
                      <Download className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    {downloadState === "working"
                      ? "Building PDF"
                      : downloadState === "done"
                        ? "Saved"
                        : "Download PDF report"}
                  </Button>

                  {downloadError && (
                    <p
                      role="alert"
                      className="mt-3 flex items-start gap-2 text-small text-band-early"
                    >
                      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                      {downloadError}
                    </p>
                  )}
                </div>
              </div>

              {/* The three tiers, on a separate surface step. Present because a
                  single opaque number invites "where did that come from?" -
                  and the honest answer is three measurements, not one. */}
              <div className="grid grid-cols-1 gap-px border-t border-line bg-line sm:grid-cols-3">
                <TierStat
                  label="Skill coverage"
                  value={target.skill_coverage}
                  weight="45%"
                  hint="Weighted by how much each skill matters to the role"
                />
                <TierStat
                  label="Meaning similarity"
                  value={target.semantic_score}
                  weight="35%"
                  hint="How closely your experience reads like this role"
                />
                <TierStat
                  label="Keyword similarity"
                  value={target.tfidf_score}
                  weight="20%"
                  hint="Shared vocabulary between your resume and the role"
                />
              </div>
            </Card>
          </motion.div>

          {/* ---- Evidence ------------------------------------------------ */}
          <motion.div variants={respectMotion(fadeUp, reduced)}>
            <SkillChips byCategory={byCategory} total={skills.length} />
          </motion.div>

          <motion.div variants={respectMotion(fadeUp, reduced)}>
            <RoleRankCard ranking={ranking} targetRoleId={target.role_id} />
          </motion.div>

          <motion.div variants={respectMotion(fadeUp, reduced)}>
            <GapTable gaps={gaps} roleName={target.role_name} />
          </motion.div>

          {/* ---- What to do about it ------------------------------------- */}
          <motion.div variants={respectMotion(fadeUp, reduced)}>
            <RoadmapTimeline roadmap={roadmap} />
          </motion.div>

          {/* ---- The limits of the number -------------------------------- */}
          <motion.div variants={respectMotion(fadeUp, reduced)}>
            <Card className="bg-transparent">
              <p className="flex gap-3 text-small text-subtle">
                <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="max-w-prose">
                  {meta.disclaimer}
                  {!meta.semantic_enabled &&
                    " The meaning-similarity tier was unavailable for this analysis, so the score was calculated from the remaining two."}
                </span>
              </p>
            </Card>
          </motion.div>
        </motion.div>
      </Shell>

      <StickyBar
        visible={!heroVisible}
        score={target.score}
        band={target.band}
        roleName={target.role_name}
        downloadState={downloadState}
        onDownload={handleDownload}
        onRestart={onRestart}
      />
    </main>
  );
}

/**
 * One of the three score components.
 *
 * The bar is deliberately thin and neutral - these are supporting evidence for
 * the hero number, and giving them colour would compete with it.
 */
function TierStat({ label, value, weight, hint }) {
  const reduced = useReducedMotion();
  const unavailable = value === null || value === undefined;
  const pct = unavailable ? 0 : Math.round(value * 100);

  return (
    <div className="bg-surface p-5">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-small text-muted">{label}</p>
        <p className="text-small tabular-nums text-subtle">{weight}</p>
      </div>

      <p
        className={cn(
          "mt-1.5 text-[1.375rem] font-semibold tabular-nums tracking-tight",
          unavailable ? "text-subtle" : "text-primary",
        )}
      >
        {unavailable ? "n/a" : `${pct}%`}
      </p>

      <span className="mt-2.5 block h-1 overflow-hidden rounded-pill bg-elevated">
        <motion.span
          initial={reduced ? false : { width: 0 }}
          whileInView={{ width: `${pct}%` }}
          viewport={{ once: true }}
          transition={{ duration: DURATION.slow, ease: EASE, delay: 0.2 }}
          className="block h-full rounded-pill bg-line-strong"
        />
      </span>

      <p className="mt-2.5 text-small leading-snug text-subtle">{hint}</p>
    </div>
  );
}

// Default export as well as the named one: App loads this screen with
// React.lazy(), which resolves the module's default.
export default Results;
