import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind class names, letting later classes win.
 *
 * clsx handles conditionals ({ "x": isActive }); twMerge resolves conflicts, so
 * cn("px-4", "px-6") gives "px-6" instead of both classes fighting in the
 * stylesheet. This is the standard shadcn/ui helper and every component uses it
 * so callers can always override styling with a className prop.
 *
 * @param {...any} inputs class names, arrays or conditional objects
 * @returns {string} the merged class string
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Format a byte count as a short human string.
 *
 * @param {number} bytes
 * @returns {string} e.g. "248 KB"
 */
export function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const units = ["B", "KB", "MB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  // One decimal only for MB; KB with decimals reads as noise.
  return `${exponent === 2 ? value.toFixed(1) : Math.round(value)} ${units[exponent]}`;
}
