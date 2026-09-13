import { cn } from "../../lib/utils";

/**
 * The 1200px content column with the responsive gutter.
 *
 * Every screen wraps in this, so the gutter is defined once: 16px on mobile as
 * the brief specifies, widening on larger screens.
 */
export function Shell({ className, ...props }) {
  return (
    <div className={cn("mx-auto w-full max-w-shell px-4 sm:px-6 lg:px-8", className)} {...props} />
  );
}
