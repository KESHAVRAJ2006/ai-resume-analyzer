import { motion, useReducedMotion } from "framer-motion";
import { Card } from "../ui/Card";
import { cn } from "../../lib/utils";
import { fadeUp, respectMotion, staggerChildren } from "../../lib/motion";

/**
 * Skills the resume evidenced, grouped by category.
 *
 * Grouping is the whole point: a flat list of 30 chips is a wall, while
 * "Programming Languages: 6" tells a candidate something about the shape of
 * their profile at a glance.
 *
 * @param {object} props
 * @param {Record<string, Array>} props.byCategory skills_by_category from the API
 * @param {number} props.total skills_found.length
 */
export function SkillChips({ byCategory, total }) {
  const reduced = useReducedMotion();

  // Biggest group first - it is the strongest signal about this candidate.
  const groups = Object.entries(byCategory).sort(
    ([, a], [, b]) => b.length - a.length,
  );

  if (!groups.length) {
    return (
      <Card>
        <h2 className="text-title">Skills found</h2>
        <p className="mt-2 max-w-prose text-body text-muted">
          No known skills were detected. That usually means the resume is image-based, or
          lists tools in a format the parser could not read - try exporting it as a
          text-based PDF.
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-title">Skills found</h2>
        <span className="text-small tabular-nums text-subtle">{total} detected</span>
      </div>

      <motion.div
        variants={staggerChildren(0.06)}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px" }}
        className="mt-6 space-y-6"
      >
        {groups.map(([category, skills]) => (
          <motion.section key={category} variants={respectMotion(fadeUp, reduced)}>
            <h3 className="mb-3 flex items-center gap-2 text-label uppercase text-subtle">
              {category}
              <span className="tabular-nums text-subtle/70">{skills.length}</span>
            </h3>

            {/* Chips stagger within their group, not across the whole card, so
                a long list does not take five seconds to finish arriving. */}
            <motion.ul
              variants={staggerChildren(0.025)}
              className="flex flex-wrap gap-2"
            >
              {skills.map((skill) => (
                <motion.li key={skill.skill_id} variants={respectMotion(fadeUp, reduced)}>
                  <Chip skill={skill} />
                </motion.li>
              ))}
            </motion.ul>
          </motion.section>
        ))}
      </motion.div>
    </Card>
  );
}

/**
 * One skill chip.
 *
 * A skill named in the Skills section is a claim; one that also appears in
 * Experience or Projects is evidence. The accent border marks the second kind.
 */
function Chip({ skill }) {
  const isEvidenced = skill.found_in.some((section) =>
    section === "experience" || section === "projects",
  );

  return (
    <span
      title={`Found in: ${skill.found_in.join(", ")}${
        skill.matched_text.toLowerCase() !== skill.name.toLowerCase()
          ? ` (written as "${skill.matched_text}")`
          : ""
      }`}
      className={cn(
        "inline-flex items-center gap-2 rounded-pill border px-3 py-1.5 text-small",
        "transition-colors duration-200 ease-brand",
        isEvidenced
          ? "border-accent/25 bg-accent-soft text-primary hover:border-accent/45"
          : "border-line bg-elevated text-muted hover:border-line-strong hover:text-primary",
      )}
    >
      {skill.name}
      {skill.occurrences > 1 && (
        <span className="tabular-nums text-subtle">&times;{skill.occurrences}</span>
      )}
    </span>
  );
}
