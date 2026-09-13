import { motion, useReducedMotion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "../../lib/utils";
import { fadeUp, respectMotion, staggerChildren } from "../../lib/motion";

/**
 * The role selector, as a pill group.
 *
 * Implemented as a radiogroup rather than a row of buttons so arrow keys move
 * between options and screen readers announce "2 of 8" - behaviour a plain
 * <button> group silently loses.
 *
 * @param {object} props
 * @param {Array<{role_id: string, role_name: string}>} props.roles
 * @param {string|null} props.value selected role_id
 * @param {(roleId: string) => void} props.onChange
 * @param {boolean} props.loading
 */
export function RolePills({ roles, value, onChange, loading }) {
  const reduced = useReducedMotion();

  if (loading) {
    return (
      <div className="flex flex-wrap gap-2" aria-busy="true" aria-label="Loading roles">
        {/* Skeletons at the real pill size, so nothing shifts when data lands. */}
        {Array.from({ length: 8 }).map((_, index) => (
          <span
            key={index}
            className="h-9 w-32 animate-pulse rounded-pill border border-line bg-elevated"
          />
        ))}
      </div>
    );
  }

  return (
    <motion.div
      role="radiogroup"
      aria-label="Target role"
      variants={staggerChildren(0.03)}
      initial="hidden"
      animate="visible"
      className="flex flex-wrap gap-2"
    >
      {roles.map((role) => {
        const selected = role.role_id === value;
        return (
          <motion.button
            key={role.role_id}
            type="button"
            role="radio"
            aria-checked={selected}
            variants={respectMotion(fadeUp, reduced)}
            onClick={() => onChange(role.role_id)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-pill border px-3.5 py-2 text-small",
              "transition-colors duration-200 ease-brand",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring",
              "focus-visible:ring-offset-2 focus-visible:ring-offset-base",
              selected
                ? "border-accent/50 bg-accent-soft text-accent-hover"
                : "border-line bg-surface text-muted hover:border-line-strong hover:text-primary",
            )}
          >
            {/* The check only appears when selected, and it is the reason the
                pill has gap-1.5 at all times - no layout shift on selection. */}
            {selected && <Check className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden="true" />}
            {role.role_name}
          </motion.button>
        );
      })}
    </motion.div>
  );
}
