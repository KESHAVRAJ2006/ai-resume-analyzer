import { cva } from "class-variance-authority";
import { cn } from "../../lib/utils";

/**
 * Button variants, defined with CVA the way shadcn/ui does it.
 *
 * Every variant carries hover AND focus-visible states - the design brief
 * requires both on every interactive element, and defining them here means no
 * individual button can forget.
 */
const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "rounded-control font-medium",
    "transition-all duration-200 ease-brand",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring",
    "focus-visible:ring-offset-2 focus-visible:ring-offset-base",
    "disabled:pointer-events-none disabled:opacity-40",
    // Tiny press response. 1px is enough to feel physical without looking like
    // a novelty.
    "active:translate-y-px",
  ],
  {
    variants: {
      variant: {
        primary: [
          "bg-accent text-white",
          "hover:bg-accent-hover",
          "active:bg-accent-press",
          "shadow-[0_1px_2px_rgba(0,0,0,0.4)]",
        ],
        secondary: [
          "bg-elevated text-primary border border-line",
          "hover:border-line-strong hover:bg-[#202024]",
        ],
        ghost: ["text-muted", "hover:text-primary hover:bg-elevated"],
        // Used only for destructive-feeling actions like removing a file.
        subtle: ["text-subtle", "hover:text-primary hover:bg-elevated"],
      },
      size: {
        sm: "h-8 px-3 text-small",
        md: "h-10 px-4 text-body",
        lg: "h-12 px-6 text-[0.9375rem]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

/**
 * The product's only button.
 *
 * @param {object} props
 * @param {"primary"|"secondary"|"ghost"|"subtle"} [props.variant]
 * @param {"sm"|"md"|"lg"|"icon"} [props.size]
 */
export function Button({ className, variant, size, type = "button", ...props }) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export { buttonVariants };
