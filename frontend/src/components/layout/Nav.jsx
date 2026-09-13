import { motion } from "framer-motion";
import { ScanLine } from "lucide-react";
import { Button } from "../ui/Button";
import { Shell } from "./Shell";
import { DURATION, EASE } from "../../lib/motion";

/**
 * Top bar. Stays out of the way: no shadow, a hairline base, and a single
 * action that is hidden on the screen it would navigate to.
 */
export function Nav({ onStart, showCta }) {
  return (
    <motion.header
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: DURATION.base, ease: EASE }}
      className="sticky top-0 z-40 border-b border-line bg-base/80 backdrop-blur-md"
    >
      <Shell className="flex h-16 items-center justify-between">
        <div className="flex items-center gap-2.5">
          {/* The mark: accent square, neutral wordmark. No emoji anywhere. */}
          <span className="flex h-7 w-7 items-center justify-center rounded-[8px] bg-accent-gradient">
            <ScanLine className="h-4 w-4 text-white" strokeWidth={2.25} aria-hidden="true" />
          </span>
          <span className="text-title tracking-tight">Resume Signal</span>
        </div>

        {showCta && (
          <Button size="sm" variant="secondary" onClick={onStart}>
            Analyze resume
          </Button>
        )}
      </Shell>
    </motion.header>
  );
}
