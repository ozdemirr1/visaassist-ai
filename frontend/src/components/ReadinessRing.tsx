/** One segment per checklist document; ready ones light up one after another. */
const RADIUS = 50;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function ReadinessRing({ total, ready, label }: { total: number; ready: number; label: string }) {
  const count = Math.max(total, 1);
  const slot = CIRCUMFERENCE / count;
  const gap = Math.min(5, slot * 0.25);
  const dash = slot - gap;
  const gapDegrees = (gap / CIRCUMFERENCE) * 360;

  return (
    <svg role="img" aria-label={label} width="176" height="176" viewBox="0 0 120 120">
      <g fill="none" strokeLinecap="butt" strokeWidth="10">
        {Array.from({ length: count }, (_, index) => {
          const lit = index < ready && total > 0;
          return (
            <circle
              key={index}
              cx="60"
              cy="60"
              r={RADIUS}
              data-ready={lit}
              strokeDasharray={`${dash} ${CIRCUMFERENCE - dash}`}
              transform={`rotate(${-90 + gapDegrees / 2 + (360 / count) * index} 60 60)`}
              className={lit ? "va-seg stroke-brand" : "stroke-line"}
              style={lit ? { animationDelay: `${0.3 + index * 0.08}s` } : undefined}
            />
          );
        })}
      </g>
    </svg>
  );
}
