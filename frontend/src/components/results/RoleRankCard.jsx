import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { motion, useReducedMotion } from "framer-motion";
import { Card } from "../ui/Card";
import { DURATION, EASE } from "../../lib/motion";

const ROW_HEIGHT = 38;
const BAR_SIZE = 12;

/**
 * Track how narrow the viewport is, so the role-name gutter can shrink.
 *
 * Recharts needs the YAxis width as a number - it cannot use a CSS breakpoint -
 * so the breakpoint has to be observed in JS.
 *
 * @param {string} query a media query string
 */
function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    () => typeof window !== "undefined" && window.matchMedia(query).matches,
  );

  useEffect(() => {
    const list = window.matchMedia(query);
    const onChange = (event) => setMatches(event.matches);
    list.addEventListener("change", onChange);
    setMatches(list.matches);
    return () => list.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

/**
 * How this resume scores against all eight roles.
 *
 * The target role is highlighted in accent with a soft glow; every other role
 * is neutral. Only one thing on this chart is allowed to be coloured, because
 * only one thing on it is the answer to the user's question.
 *
 * @param {object} props
 * @param {Array} props.ranking role_ranking from the API, already sorted
 * @param {string} props.targetRoleId the role the user chose
 */
export function RoleRankCard({ ranking, targetRoleId }) {
  const reduced = useReducedMotion();
  const isNarrow = useMediaQuery("(max-width: 640px)");

  // Recharts draws the first data row at the top of a vertical layout, which is
  // what we want since the API already returns best-first.
  const data = ranking.map((role) => ({
    ...role,
    // Rounded once here so the bar, the label and the alt text cannot disagree.
    value: Math.round(role.score),
  }));

  const best = data[0];

  return (
    <Card>
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-title">Role ranking</h2>
        <span className="text-small text-subtle">All 8 roles</span>
      </div>
      <p className="mt-1.5 max-w-prose text-small text-muted">
        {best.role_id === targetRoleId
          ? `${best.role_name} is your strongest match of the eight.`
          : `Your resume scores highest for ${best.role_name}, ${Math.round(
              best.score - (data.find((r) => r.role_id === targetRoleId)?.score ?? 0),
            )} points above the role you chose.`}
      </p>

      <motion.div
        initial={reduced ? false : { opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: DURATION.slow, ease: EASE }}
        className="mt-6"
        style={{ height: data.length * ROW_HEIGHT }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 0, right: 44, bottom: 0, left: 0 }}
            barCategoryGap={10}
          >
            <defs>
              {/* The "subtle glow" on the top role. feDropShadow with zero
                  offset and the accent colour reads as light, not shadow. */}
              <filter id="bar-glow" x="-50%" y="-200%" width="200%" height="500%">
                <feDropShadow
                  dx="0"
                  dy="0"
                  stdDeviation="4"
                  floodColor="#6366F1"
                  floodOpacity="0.55"
                />
              </filter>
            </defs>

            {/* Domain pinned to 0-100: an auto domain would rescale per resume
                and make two different analyses look identical. */}
            <XAxis type="number" domain={[0, 100]} hide />

            <YAxis
              type="category"
              dataKey="role_name"
              width={isNarrow ? 116 : 188}
              axisLine={false}
              tickLine={false}
              tick={(props) => <RoleTick {...props} targetRoleId={targetRoleId} data={data} />}
            />

            <Bar
              dataKey="value"
              barSize={BAR_SIZE}
              radius={[BAR_SIZE / 2, BAR_SIZE / 2, BAR_SIZE / 2, BAR_SIZE / 2]}
              // Recharts' own animation, so it matches the brand easing.
              isAnimationActive={!reduced}
              animationDuration={700}
              animationEasing="ease-out"
              background={{ fill: "#1A1A1D", radius: BAR_SIZE / 2 }}
            >
              {data.map((role) => (
                <Cell
                  key={role.role_id}
                  fill={role.role_id === targetRoleId ? "#6366F1" : "#2E2E34"}
                  filter={role.role_id === targetRoleId ? "url(#bar-glow)" : undefined}
                />
              ))}

              <LabelList
                dataKey="value"
                position="right"
                offset={10}
                content={(props) => <ValueLabel {...props} data={data} targetRoleId={targetRoleId} />}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </motion.div>

      {/* The chart is decorative for a screen reader - it cannot read an SVG
          bar. The same data as a list is the accessible version. */}
      <ul className="sr-only">
        {data.map((role) => (
          <li key={role.role_id}>
            {role.role_name}: {role.value} percent
            {role.role_id === targetRoleId ? " (your target role)" : ""}
          </li>
        ))}
      </ul>
    </Card>
  );
}

/** Role name on the Y axis, emphasised when it is the target role. */
function RoleTick({ x, y, payload, targetRoleId, data }) {
  const role = data.find((item) => item.role_name === payload.value);
  const isTarget = role?.role_id === targetRoleId;

  return (
    <text
      x={x - 12}
      y={y}
      dy={4}
      textAnchor="end"
      className="text-small"
      fill={isTarget ? "#EDEDEF" : "#A1A1AA"}
      fontWeight={isTarget ? 500 : 400}
    >
      {payload.value}
    </text>
  );
}

/** The percentage at the end of each bar, in tabular figures. */
function ValueLabel({ x, y, width, height, value, index, data, targetRoleId }) {
  const isTarget = data[index]?.role_id === targetRoleId;
  return (
    <text
      x={x + width + 10}
      y={y + height / 2}
      dy={4}
      textAnchor="start"
      className="text-small"
      fill={isTarget ? "#EDEDEF" : "#71717A"}
      style={{ fontVariantNumeric: "tabular-nums" }}
    >
      {value}%
    </text>
  );
}
