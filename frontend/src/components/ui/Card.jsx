import { cn } from "../../lib/utils";

/**
 * The one card shell: 16px radius, 24px padding, 1px border, soft shadow.
 *
 * Depth in this UI comes from the border and the surface step, not from a drop
 * shadow - which is why the shadow token is deliberately almost invisible.
 */
export function Card({ className, as: Tag = "div", ...props }) {
  return (
    <Tag
      className={cn(
        "rounded-card border border-line bg-surface p-6 shadow-card",
        className,
      )}
      {...props}
    />
  );
}

/**
 * Card that reacts to the pointer. Used for anything clickable or hoverable.
 */
export function InteractiveCard({ className, ...props }) {
  return (
    <Card
      className={cn(
        "transition-colors duration-200 ease-brand",
        "hover:border-line-strong hover:bg-elevated",
        className,
      )}
      {...props}
    />
  );
}
