import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, GitCompareArrows, Route, ScanSearch } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Shell } from "../components/layout/Shell";
import { DURATION, EASE, fadeUp, respectMotion, staggerChildren } from "../lib/motion";

/** The three things the product actually does. One icon each, no emoji. */
const FEATURES = [
  {
    icon: ScanSearch,
    title: "Reads what you wrote",
    body: "Pulls skills out of your PDF or DOCX, including the ones hiding in tables, and understands that sklearn and scikit-learn are the same thing.",
  },
  {
    icon: GitCompareArrows,
    title: "Scores against eight roles",
    body: "Weighted skill coverage, keyword similarity and meaning-based similarity, blended into one number you can compare across roles.",
  },
  {
    icon: Route,
    title: "Tells you what to do next",
    body: "Your missing skills ranked by how much they cost you, and a four-week plan that starts with the ones that matter most.",
  },
];

/**
 * Screen 1. A gradient mesh hero, one clear claim, one action, three cards.
 *
 * Everything here is load-triggered rather than scroll-triggered above the
 * fold - content the user can already see should not wait for a scroll event.
 */
export function Landing({ onStart }) {
  const reduced = useReducedMotion();

  return (
    <main>
      {/* The mesh is a background layer, not a section, so it can bleed past the
          content column without affecting layout. pointer-events-none keeps it
          from ever intercepting a click. */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 -top-24 bg-hero-mesh"
        />

        <Shell className="relative pb-20 pt-20 sm:pb-28 sm:pt-28">
          <motion.div
            variants={staggerChildren(0.06)}
            initial="hidden"
            animate="visible"
            className="max-w-3xl"
          >
            <motion.p
              variants={respectMotion(fadeUp, reduced)}
              className="mb-5 inline-flex items-center gap-2 rounded-pill border border-line bg-surface/70 px-3 py-1.5 text-label uppercase text-muted"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" />
              Resume analysis, without the guesswork
            </motion.p>

            <motion.h1
              variants={respectMotion(fadeUp, reduced)}
              className="text-hero-sm sm:text-hero"
            >
              Find out where your resume
              <br className="hidden sm:block" />{" "}
              <span className="text-gradient">actually stands</span>
            </motion.h1>

            <motion.p
              variants={respectMotion(fadeUp, reduced)}
              className="mt-6 max-w-prose text-[1.0625rem] leading-relaxed text-muted"
            >
              Upload a resume and get a match score against eight engineering roles, the exact
              skills you are missing, and a four-week plan to close the gap.
            </motion.p>

            <motion.div
              variants={respectMotion(fadeUp, reduced)}
              className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center"
            >
              <Button size="lg" onClick={onStart} className="group">
                Analyze my resume
                {/* The arrow moves, not the button. Cheaper visually, and it
                    survives reduced-motion because it is a transform on hover. */}
                <ArrowRight
                  className="h-4 w-4 transition-transform duration-200 ease-brand group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </Button>
              <p className="text-small text-subtle">
                PDF or DOCX &middot; under 5&nbsp;MB &middot; deleted after analysis
              </p>
            </motion.div>
          </motion.div>
        </Shell>
      </section>

      <Shell>
        <div className="hairline" />
      </Shell>

      {/* Below the fold, so these are scroll-triggered. once:true means they
          animate in a single time, not every time they re-enter the viewport. */}
      <Shell className="pt-16">
        <motion.div
          variants={staggerChildren(0.06)}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          className="grid gap-4 md:grid-cols-3"
        >
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <motion.div key={title} variants={respectMotion(fadeUp, reduced)}>
              <Card className="h-full">
                <span className="mb-5 inline-flex h-10 w-10 items-center justify-center rounded-control border border-line bg-elevated">
                  <Icon className="h-[18px] w-[18px] text-accent" strokeWidth={1.75} aria-hidden="true" />
                </span>
                <h2 className="text-title">{title}</h2>
                <p className="mt-2 text-body text-muted">{body}</p>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </Shell>

      <Shell className="pt-16">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: DURATION.slow, ease: EASE }}
        >
          <Card className="flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-section">Ready when you are</h2>
              <p className="mt-2 max-w-prose text-body text-muted">
                Takes about ten seconds. Nothing is stored: your file is deleted as soon as the
                analysis finishes.
              </p>
            </div>
            <Button size="lg" onClick={onStart} className="shrink-0">
              Analyze my resume
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </Card>
        </motion.div>
      </Shell>
    </main>
  );
}
