import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    // Top-level borderRadius OVERRIDES (not extends) — flat editorial scale (ADR-2)
    borderRadius: {
      none: "0",
      sm: "1px",
      DEFAULT: "2px",
      md: "2px",
      lg: "3px",
      xl: "3px",
      "2xl": "3px",
      full: "9999px",
    },
    extend: {
      fontFamily: {
        serif: ["var(--font-newsreader)", "Georgia", "serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        // Deprecated — kept until login redesign (ADR-9)
        display: ["var(--font-league-spartan)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        // Zanovix brand namespace (ADR-4)
        zx: {
          paper: "#F4F1EA",
          "paper-2": "#ECE6D6",
          ink: "#1F2A26",
          "ink-soft": "#3B463F",
          "ink-mute": "rgba(31,42,38,0.55)",
          rule: "rgba(31,42,38,0.14)",
          night: "#14201B",
          green: {
            DEFAULT: "#2E8169",
            dark: "#1F5B49",
            light: "#6BBF96",
          },
          terra: "#B85F3D",
          status: {
            active: "#2E8169",
            pending: "#B85F3D",
            overdue: "#cc3c28",
            neutral: "rgba(31,42,38,0.5)",
          },
        },
        // shadcn semantic colors (consume HSL vars from globals.css)
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
        // Status semantic color tokens (AD-6) — kept as-is per ADR-5 note
        status: {
          success: "hsl(var(--status-success))",
          "success-foreground": "hsl(var(--status-success-foreground))",
          warning: "hsl(var(--status-warning))",
          "warning-foreground": "hsl(var(--status-warning-foreground))",
          error: "hsl(var(--status-error))",
          "error-foreground": "hsl(var(--status-error-foreground))",
          info: "hsl(var(--status-info))",
          "info-foreground": "hsl(var(--status-info-foreground))",
          pending: "hsl(var(--status-pending))",
          "pending-foreground": "hsl(var(--status-pending-foreground))",
          neutral: "hsl(var(--status-neutral))",
          "neutral-foreground": "hsl(var(--status-neutral-foreground))",
        },
      },
      backgroundImage: {
        grano: "radial-gradient(rgba(31,42,38,0.05) 1px, transparent 1px)",
      },
      backgroundSize: {
        grano: "6px 6px",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
