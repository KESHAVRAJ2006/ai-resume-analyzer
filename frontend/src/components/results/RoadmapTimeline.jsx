import { motion, useReducedMotion } from "framer-motion";
import { Clock } from "lucide-react";
import { Card } from "../ui/Card";
import { fadeUp, respectMotion, staggerChildren } from "../../lib/motion";

/**
 * The four-week plan as a vertical timeline.
 *
 * A timeline rather than four cards because the weeks are ordered by impact,
 * not by preference - week 1 closes the gaps that cost the most points, and the
 * connecting line is what communicates that sequence.
 *
 * @param {object} props
 * @param {Array} props.roadmap the roadmap array from the API
 */
export function RoadmapTimeline({ roadmap }) {
  const reduced = useReducedMotion();
  const totalHours = roadmap.reduce((sum, week) => sum + week.estimated_hours, 0);

  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="text-title">Your four-week plan</h2>
        <span className="flex items-center gap-1.5 text-small tabular-nums text-subtle">
          <Clock className="h-3.5 w-3.5" aria-hidden="true" />
          {totalHours} hours total
        </span>
      </div>

      <motion.ol
        variants={staggerChildren(0.06)}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px" }}
        className="relative mt-7"
      >
        {/* The connecting line. Inset from the top and bottom so it starts and
            ends at the first and last node rather than floating past them. */}
        <span
          aria-hidden="true"
          className="absolute bottom-6 left-[13px] top-3 w-px bg-line"
        />

        {roadmap.map((week, index) => (
          <motion.li
            key={week.week}
            variants={respectMotion(fadeUp, reduced)}
            className="relative pb-9 pl-11 last:pb-0"
          >
            {/* Node. Week 1 is accent-filled because it is the one that moves
                the score; the rest are outlined. */}
            <span
              aria-hidden="true"
              className={
                index === 0
                  ? "absolute left-0 top-1.5 flex h-[27px] w-[27px] items-center justify-center rounded-full border border-accent/40 bg-accent text-[0.6875rem] font-semibold tabular-nums text-white"
                  : "absolute left-0 top-1.5 flex h-[27px] w-[27px] items-center justify-center rounded-full border border-line bg-elevated text-[0.6875rem] font-semibold tabular-nums text-muted"
              }
            >
              {week.week}
            </span>

            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h3 className="text-body font-medium text-primary">{week.title}</h3>
              <span className="text-small tabular-nums text-subtle">
                {week.estimated_hours}h
              </span>
            </div>

            <p className="mt-1.5 max-w-prose text-small text-muted">{week.objective}</p>

            {week.focus_skills.length > 0 && (
              <ul className="mt-3 flex flex-wrap gap-1.5">
                {week.focus_skills.map((skill) => (
                  <li
                    key={skill}
                    className="rounded-pill border border-accent/25 bg-accent-soft px-2.5 py-1 text-small text-accent-hover"
                  >
                    {skill}
                  </li>
                ))}
              </ul>
            )}

            <ul className="mt-3.5 space-y-2">
              {week.activities.map((activity) => (
                <li key={activity} className="flex gap-2.5 text-small text-muted">
                  <span
                    aria-hidden="true"
                    className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-line-strong"
                  />
                  <span className="max-w-prose">{activity}</span>
                </li>
              ))}
            </ul>
          </motion.li>
        ))}
      </motion.ol>
    </Card>
  );
}
