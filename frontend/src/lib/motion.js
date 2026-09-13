/**
 * The motion system, in one place.
 *
 * Rules from the design brief, encoded once so no component invents its own:
 *   - durations 200-400ms
 *   - easing [0.22, 1, 0.36, 1] everywhere
 *   - children stagger by 60ms
 *   - prefers-reduced-motion is respected
 *
 * Framer Motion reads the OS setting through useReducedMotion(); these variants
 * are written so that when motion is reduced, elements simply appear.
 */

export const EASE = [0.22, 1, 0.36, 1];

export const DURATION = {
  fast: 0.2,
  base: 0.3,
  slow: 0.4,
};

export const STAGGER = 0.06; // 60ms

/** Fade up. The default entrance for almost everything. */
export const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.base, ease: EASE },
  },
};

/** Plain fade, for elements where movement would be distracting. */
export const fade = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: DURATION.base, ease: EASE } },
};

/**
 * Parent variant that staggers its children.
 *
 * @param {number} [stagger] seconds between children
 * @param {number} [delay] seconds before the first child
 */
export const staggerChildren = (stagger = STAGGER, delay = 0) => ({
  hidden: {},
  visible: {
    transition: { staggerChildren: stagger, delayChildren: delay },
  },
});

/** Screen-level transition, used when swapping between the four screens. */
export const screenTransition = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE } },
  exit: { opacity: 0, y: -8, transition: { duration: DURATION.fast, ease: EASE } },
};

/**
 * Strip movement from a variant when the user asked for reduced motion.
 *
 * Opacity is kept - a fade is not what triggers motion sickness, translation
 * and scale are - but the distance goes to zero and the duration to near zero.
 *
 * @param {object} variant a variants object with hidden/visible
 * @param {boolean} reduced result of useReducedMotion()
 */
export function respectMotion(variant, reduced) {
  if (!reduced) return variant;
  return {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.01 } },
  };
}
