/**
 * The design system, expressed once.
 *
 * Every colour, size and easing the UI uses is named here. Components never
 * write a raw hex value or a magic pixel number - if a token is missing, it
 * gets added here rather than inlined, so the whole product can be restyled
 * from one file.
 */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces, darkest to lightest. Three steps is enough depth for a
        // dark UI; more and the hierarchy stops reading.
        base: "#0A0A0B", // page background
        surface: "#141416", // cards
        elevated: "#1A1A1D", // inputs, hovered rows, nested panels
        line: "#232327", // default 1px border
        "line-strong": "#2E2E34", // border on hover / focus

        // Text, in descending emphasis.
        primary: "#EDEDEF",
        muted: "#A1A1AA",
        subtle: "#71717A",

        // One accent. Everything interactive is this colour or neutral.
        accent: {
          DEFAULT: "#6366F1",
          hover: "#818CF8",
          press: "#4F46E5",
          soft: "rgba(99, 102, 241, 0.12)", // tinted fills
          ring: "rgba(99, 102, 241, 0.45)", // focus rings
        },

        // Score bands. Used only for the ring and severity badges, never for
        // decoration - colour here always means something.
        band: {
          early: "#EF4444",
          developing: "#F59E0B",
          strong: "#10B981",
        },
      },

      fontFamily: {
        // Inter is loaded in index.html; the fallbacks keep metrics close
        // while the webfont is still in flight.
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },

      fontSize: {
        // [size, { lineHeight, letterSpacing, fontWeight }]
        hero: ["3.5rem", { lineHeight: "1.05", letterSpacing: "-0.03em", fontWeight: "700" }],
        "hero-sm": ["2.5rem", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "700" }],
        section: ["1.75rem", { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "600" }],
        title: ["1.0625rem", { lineHeight: "1.4", letterSpacing: "-0.01em", fontWeight: "600" }],
        body: ["0.9375rem", { lineHeight: "1.6", fontWeight: "400" }],
        small: ["0.8125rem", { lineHeight: "1.5", fontWeight: "400" }],
        label: ["0.75rem", { lineHeight: "1.4", letterSpacing: "0.04em", fontWeight: "500" }],
      },

      borderRadius: {
        card: "16px", // every card, one value
        control: "10px", // buttons, inputs
        pill: "999px",
      },

      boxShadow: {
        // Deliberately soft. Depth in this UI comes from 1px borders and
        // surface steps, not from drop shadows.
        card: "0 1px 2px rgba(0, 0, 0, 0.4)",
        lifted: "0 8px 24px -12px rgba(0, 0, 0, 0.7)",
        "accent-glow": "0 0 0 1px rgba(99, 102, 241, 0.35), 0 8px 32px -8px rgba(99, 102, 241, 0.35)",
      },

      maxWidth: {
        shell: "1200px",
        prose: "34rem", // ~62 characters, the comfortable reading measure
      },

      backgroundImage: {
        // The one gradient in the product: violet to cyan, for the hero
        // wordmark and the score ring.
        "accent-gradient": "linear-gradient(100deg, #8B5CF6 0%, #6366F1 45%, #22D3EE 100%)",
        // Radial mesh behind the hero. Two soft lobes, no hard edges.
        "hero-mesh":
          "radial-gradient(60% 55% at 18% 0%, rgba(139, 92, 246, 0.18) 0%, transparent 60%), radial-gradient(50% 50% at 82% 10%, rgba(34, 211, 238, 0.12) 0%, transparent 60%)",
      },

      transitionTimingFunction: {
        // The single easing curve used across the product.
        brand: "cubic-bezier(0.22, 1, 0.36, 1)",
      },

      transitionDuration: {
        DEFAULT: "200ms",
      },

      keyframes: {
        "dash-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },

      animation: {
        "dash-glow": "dash-glow 2.4s cubic-bezier(0.22, 1, 0.36, 1) infinite",
        shimmer: "shimmer 1.6s cubic-bezier(0.22, 1, 0.36, 1) infinite",
      },
    },
  },
  plugins: [],
};
