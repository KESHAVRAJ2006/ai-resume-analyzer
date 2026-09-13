import { cva } from "class-variance-authority";
import { cn } from "../../lib/utils";

/**
 * Small status label. Tones are semantic, never decorative: `critical` means a
 * must-have skill is missing, not "this looks nice in red".
 */
const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-label uppercase",
  {
    variants: {
      tone: {
        neutral: "border-line bg-elevated text-muted",
        accent: "border-accent/30 bg-accent-soft text-accent-hover",
        critical: "border-band-early/30 bg-band-early/10 text-band-early",
        important: "border-band-developing/30 bg-band-developing/10 text-band-developing",
        optional: "border-line bg-elevated text-subtle",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export function Badge({ className, tone, ...props }) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
