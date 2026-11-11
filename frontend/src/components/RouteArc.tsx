const PATH = "M40 118 Q280 -30 520 104";

/** Decorative route from Türkiye to the destination country; the line draws, a dot travels it. */
export function RouteArc({ from, to, label }: { from: string; to: string; label: string }) {
  return (
    <svg role="img" aria-label={label} viewBox="0 0 560 150" className="relative max-h-[170px] w-full">
      <path d={PATH} fill="none" stroke="#22304f" strokeWidth="2" />
      <path d={PATH} fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" className="va-draw" />
      <circle cx="40" cy="118" r="6" fill="#0b1324" stroke="#fff" strokeWidth="3" />
      <circle cx="520" cy="104" r="7" stroke="#fff" strokeWidth="2" className="fill-brand" />
      <circle
        r="6"
        stroke="#fff"
        strokeWidth="2"
        className="va-fly fill-brand"
        style={{ offsetPath: `path('${PATH}')` }}
      />
      <text x="40" y="142" textAnchor="middle" fontSize="12" fontWeight="600" fill="#fff" className="font-mono">
        {from}
      </text>
      <text x="520" y="132" textAnchor="middle" fontSize="12" fontWeight="600" fill="#fff" className="font-mono">
        {to}
      </text>
    </svg>
  );
}
