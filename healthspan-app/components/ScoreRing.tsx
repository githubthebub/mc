"use client";

interface Props {
  score: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
}

function scoreColor(score: number) {
  if (score >= 75) return "#10b981"; // emerald
  if (score >= 50) return "#f59e0b"; // amber
  return "#f43f5e"; // rose
}

export default function ScoreRing({
  score,
  size = 120,
  strokeWidth = 10,
  label,
}: Props) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = scoreColor(score);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgb(30 41 59)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center" style={{ marginTop: size / 2 - 16 }}>
      </div>
      <div className="-mt-[calc(50%+20px)] flex flex-col items-center" style={{ marginTop: `-${size / 2 + 20}px` }}>
        <span className="text-3xl font-bold" style={{ color }}>{score}</span>
        {label && <span className="text-xs text-slate-400">{label}</span>}
      </div>
    </div>
  );
}
