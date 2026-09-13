import { useEffect } from "react";
import {
  animate,
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useTransform,
} from "framer-motion";
import { cn } from "../../lib/utils";
import { EASE } from "../../lib/motion";

/**
 * Each band owns two stops. The conic gradient runs from the lighter stop to
 * the heavier one, so the stroke deepens as it sweeps - a flat single colour
 * reads as a progress bar bent into a circle, which is exactly what we are
 * trying not to look like.
 */
const BAND_STOPS = {
  early: { from: "#FCA5A5", to: "#EF4444", glow: "rgba(239, 68, 68, 0.25)" },
  developing: { from: "#FCD34D", to: "#F59E0B", glow: "rgba(245, 158, 11, 0.25)" },
  strong: { from: "#6EE7B7", to: "#10B981", glow: "rgba(16, 185, 129, 0.25)" },
};

const BAND_LABEL = {
  early: "Early match",
  developing: "Developing match",
  strong: "Strong match",
};

const COUNT_DURATION = 1.2; // seconds, per the brief
const STROKE = 12; // ring thickness in px

/**
 * The hero number: a circular gauge whose stroke is a real conic gradient.
 *
 * Implemented with a masked conic-gradient rather than an SVG circle. An SVG
 * stroke can only carry a linear gradient, which on a circle looks like a
 * lighting error rather than a sweep; masking a conic-gradient div gives a
 * stroke whose colour genuinely follows the arc.
 *
 * @param {object} props
 * @param {number} props.score 0-100
 * @param {"early"|"developing"|"strong"} props.band
 * @param {number} [props.size] diameter in px
 */
export function ScoreRing({ score, band, size = 176, className }) {
  const reduced = useReducedMotion();
  const stops = BAND_STOPS[band] ?? BAND_STOPS.developing;

  // One motion value drives everything: the number, the sweep angle and the
  // cap position. Because it lives outside React state, the 1.2s animation
  // causes zero re-renders.
  const progress = useMotionValue(0);

  const displayed = useTransform(progress, (value) => Math.round(value));
  const degrees = useTransform(progress, (value) => (value / 100) * 360);
  const sweep = useTransform(degrees, (value) => `${value}deg`);
  const capRotation = useTransform(degrees, (value) => value - 90);

  // transparent, not "transparent": some browsers interpolate the keyword to
  // transparent-black and leave a grey smear at the gradient's hard edge.
  const gradient = useMotionTemplate`conic-gradient(from -90deg, ${stops.from} 0deg, ${stops.to} ${sweep}, rgba(0,0,0,0) ${sweep})`;

  // The cap dot is only drawn once the arc is long enough to have a visible
  // end; below ~2% it would sit on top of the start cap.
  const capOpacity = useTransform(progress, [0, 1.5, 2.5], [0, 0, 1]);

  useEffect(() => {
    const controls = animate(progress, score, {
      duration: reduced ? 0 : COUNT_DURATION,
      ease: EASE,
    });
    return () => controls.stop();
  }, [progress, score, reduced]);

  const inner = size - STROKE * 2;

  return (
    <div
      className={cn("relative shrink-0", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${Math.round(score)} percent match. ${BAND_LABEL[band]}.`}
    >
      {/* Glow. Sits behind everything, blurred, band-tinted. Small enough to
          read as light rather than as a drop shadow. */}
      <div
        aria-hidden="true"
        className="absolute inset-3 rounded-full blur-2xl"
        style={{ background: stops.glow }}
      />

      {/* Track: the unfilled part of the ring. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 rounded-full bg-line"
        style={{
          // The mask punches out the middle, turning a filled circle into a
          // ring of exactly STROKE px.
          WebkitMaskImage: `radial-gradient(farthest-side, transparent calc(100% - ${STROKE}px), #000 calc(100% - ${STROKE}px))`,
          maskImage: `radial-gradient(farthest-side, transparent calc(100% - ${STROKE}px), #000 calc(100% - ${STROKE}px))`,
        }}
      />

      {/* The animated stroke. */}
      <motion.div
        aria-hidden="true"
        className="absolute inset-0 rounded-full"
        style={{
          background: gradient,
          WebkitMaskImage: `radial-gradient(farthest-side, transparent calc(100% - ${STROKE}px), #000 calc(100% - ${STROKE}px))`,
          maskImage: `radial-gradient(farthest-side, transparent calc(100% - ${STROKE}px), #000 calc(100% - ${STROKE}px))`,
        }}
      />

      {/* Rounded end cap. A conic gradient ends in a hard radial edge; this dot
          restores the rounded terminal an SVG strokeLinecap would give. */}
      <motion.div
        aria-hidden="true"
        className="absolute inset-0"
        style={{ rotate: capRotation, opacity: capOpacity }}
      >
        <span
          className="absolute left-1/2 top-0 block rounded-full"
          style={{
            width: STROKE,
            height: STROKE,
            marginLeft: -STROKE / 2,
            background: stops.to,
          }}
        />
      </motion.div>

      {/* Centre well. A surface disc so the number never sits on the glow. */}
      <div
        className="absolute rounded-full bg-surface"
        style={{ inset: STROKE, width: inner, height: inner }}
      />

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <p className="flex items-start leading-none">
          {/* tabular-nums is essential here: without it the number visibly
              jitters as it counts, because 1 is narrower than 8. */}
          <motion.span
            className="text-[3.25rem] font-bold tabular-nums tracking-[-0.03em] text-primary"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {displayed}
          </motion.span>
          <span className="mt-1.5 text-xl font-semibold text-subtle">%</span>
        </p>
        <p className="mt-0.5 text-label uppercase text-subtle">match</p>
      </div>
    </div>
  );
}

export { BAND_LABEL };
