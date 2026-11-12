// Inline stroke icons (decorative: always next to a text label or inside a labelled control).
import type { ReactNode } from "react";

function Svg({ children, size = 18, strokeWidth = 1.8 }: { children: ReactNode; size?: number; strokeWidth?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0"
    >
      {children}
    </svg>
  );
}

export const IconBrand = () => (
  <Svg size={20} strokeWidth={2.2}>
    <rect x="5" y="3" width="14" height="18" rx="2.5" />
    <circle cx="12" cy="10" r="3" />
    <path d="M9 17h6" />
  </Svg>
);
export const IconList = () => (
  <Svg>
    <path d="M9 6h11M9 12h11M9 18h11M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2" />
  </Svg>
);
export const IconFolder = () => (
  <Svg>
    <path d="M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z" />
  </Svg>
);
export const IconPlus = () => (
  <Svg size={16} strokeWidth={2}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
);
export const IconLogout = () => (
  <Svg>
    <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 8l-4 4 4 4M6 12h10" />
  </Svg>
);
export const IconLogin = () => (
  <Svg>
    <path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3M14 8l4 4-4 4M18 12H8" />
  </Svg>
);
export const IconCheck = () => (
  <Svg size={14} strokeWidth={3.2}>
    <path d="M5 12l5 5 9-10" />
  </Svg>
);
export const IconSearch = () => (
  <Svg size={16} strokeWidth={2}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  </Svg>
);
export const IconUpload = () => (
  <Svg size={22}>
    <path d="M12 16V5M7.5 9.5 12 5l4.5 4.5M5 19h14" />
  </Svg>
);
export const IconDownload = () => (
  <Svg size={16} strokeWidth={2}>
    <path d="M12 5v11M7.5 11.5 12 16l4.5-4.5M5 19h14" />
  </Svg>
);
export const IconLock = () => (
  <Svg size={22}>
    <rect x="5" y="10.5" width="14" height="9.5" rx="2.5" />
    <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" />
  </Svg>
);
export const IconFile = () => (
  <Svg>
    <path d="M7 3h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
    <path d="M14 3v5h5" />
  </Svg>
);
export const IconGlobe = () => (
  <Svg>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18M12 3c2.8 3 2.8 15 0 18M12 3c-2.8 3-2.8 15 0 18" />
  </Svg>
);
