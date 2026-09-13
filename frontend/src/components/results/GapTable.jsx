import { motion, useReducedMotion } from "framer-motion";
import { Check } from "lucide-react";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { cn } from "../../lib/utils";
import { fadeUp, respectMotion, staggerChildren } from "../../lib/motion";

/** Tier ids from the API to the words a person uses. */
const TIER_LABEL = {
  must_have: "Must have",
  good_to_have: "Good to have",
  nice_to_have: "Nice to have",
};

const TIER_ORDER = ["must_have", "good_to_have", "nice_to_have"];

/**
 * What the role needs, split into what you have and what you do not.
 *
 * Two columns rather than one list, because "you already have 8 of these" is
 * as much a part of the answer as "you are missing 10".
 *
 * @param {object} props
 * @param {object} props.gaps the gaps object from the API
 * @param {string} props.roleName
 */
export function GapTable({ gaps, roleName }) {
  const reduced = useReducedMotion();

  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="text-title">Requirements for {roleName}</h2>
        <span className="text-small tabular-nums text-subtle">
          {gaps.earned_weight} of {gaps.total_weight} weighted points
        </span>
      </div>

      {/* Per-tier progress. This is the clearest explanation of the score on the
          whole page: it shows exactly which bucket is costing the points. */}
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        {TIER_ORDER.map((tier) => {
          const summary = gaps.tier_summary[tier];
          if (!summary) return null;
          const pct = summary.total ? (summary.have / summary.total) * 100 : 0;
          return (
            <div key={tier} className="rounded-control border border-line bg-elevated p-3">
              <p className="flex items-baseline justify-between text-small">
                <span className="text-muted">{TIER_LABEL[tier]}</span>
                <span className="tabular-nums text-primary">
                  {summary.have}/{summary.total}
                </span>
              </p>
              <span className="mt-2 block h-1 overflow-hidden rounded-pill bg-line">
                <motion.span
                  initial={reduced ? false : { width: 0 }}
                  whileInView={{ width: `${pct}%` }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                  className={cn(
                    "block h-full rounded-pill",
                    tier === "must_have" ? "bg-accent" : "bg-line-strong",
                  )}
                />
              </span>
            </div>
          );
        })}
      </div>

      <motion.div
        variants={staggerChildren(0.06)}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px" }}
        className="mt-8 grid gap-8 md:grid-cols-2"
      >
        {/* Missing first. It is the column the user came for, and on mobile the
            grid collapses to one column so column order becomes reading order. */}
        <motion.section variants={respectMotion(fadeUp, reduced)}>
          <ColumnHeading
            title="Missing"
            count={gaps.missing.length}
            hint="Ranked by how much each one costs you"
          />
          {gaps.missing.length === 0 ? (
            <EmptyNote>You cover every skill listed for this role.</EmptyNote>
          ) : (
            <ul className="divide-y divide-line">
              {gaps.missing.map((gap) => (
                <li
                  key={gap.skill_id}
                  className="flex items-center justify-between gap-3 py-2.5 first:pt-0"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-body text-primary">{gap.name}</span>
                    <span className="text-small text-subtle">{gap.category}</span>
                  </span>
                  <Badge tone={gap.severity} className="shrink-0">
                    {gap.severity}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </motion.section>

        <motion.section variants={respectMotion(fadeUp, reduced)}>
          <ColumnHeading
            title="You already have"
            count={gaps.matched.length}
            hint="Counted toward your score"
          />
          {gaps.matched.length === 0 ? (
            <EmptyNote>None of this role&apos;s skills were detected.</EmptyNote>
          ) : (
            <ul className="divide-y divide-line">
              {gaps.matched.map((skill) => (
                <li
                  key={skill.skill_id}
                  className="flex items-center justify-between gap-3 py-2.5 first:pt-0"
                >
                  <span className="flex min-w-0 items-center gap-2.5">
                    <Check
                      className="h-4 w-4 shrink-0 text-band-strong"
                      strokeWidth={2.5}
                      aria-hidden="true"
                    />
                    <span className="min-w-0">
                      <span className="block truncate text-body text-primary">{skill.name}</span>
                      <span className="text-small text-subtle">
                        {TIER_LABEL[skill.tier]}
                      </span>
                    </span>
                  </span>
                  <span className="shrink-0 text-small tabular-nums text-subtle">
                    +{skill.weight}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </motion.section>
      </motion.div>
    </Card>
  );
}

function ColumnHeading({ title, count, hint }) {
  return (
    <div className="mb-4">
      <h3 className="flex items-baseline gap-2 text-label uppercase text-subtle">
        {title}
        <span className="tabular-nums text-subtle/70">{count}</span>
      </h3>
      <p className="mt-1 text-small text-subtle">{hint}</p>
    </div>
  );
}

function EmptyNote({ children }) {
  return (
    <p className="rounded-control border border-line bg-elevated px-3.5 py-3 text-small text-muted">
      {children}
    </p>
  );
}
