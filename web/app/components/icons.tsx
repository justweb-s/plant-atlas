type P = { className?: string };

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export const IconSearch = ({ className }: P) => (
  <svg {...base} className={className}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </svg>
);

export const IconArrow = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);

export const IconDoc = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5M9 13h6M9 17h6" />
  </svg>
);

export const IconShield = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z" />
    <path d="m9 12 2 2 4-4" />
  </svg>
);

export const IconClock = ({ className }: P) => (
  <svg {...base} className={className}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </svg>
);

export const IconRobot = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M5 21h8M9 21v-5l-3-6 5-5 4 3M15 8l4 1-1 4" />
    <circle cx="6" cy="10" r="1.5" />
    <circle cx="11" cy="5" r="1.5" />
  </svg>
);

export const IconScan = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M12 20a8 8 0 0 1 8-8M12 20a8 8 0 0 0-8-8M12 20V10" />
    <circle cx="12" cy="6" r="2" />
  </svg>
);

export const IconLift = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M5 21V4M19 21V4M3 21h18M5 11h14M8 11V8h8v3" />
  </svg>
);

export const IconDownload = ({ className }: P) => (
  <svg {...base} className={className}>
    <path d="M12 4v11M7 11l5 5 5-5M5 20h14" />
  </svg>
);
