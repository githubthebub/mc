"use client";

import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (v: number) => void;
  lowLabel?: string;
  highLabel?: string;
  colorScale?: boolean;
}

function scaleColor(value: number, min: number, max: number, invert = false) {
  const pct = (value - min) / (max - min);
  const v = invert ? 1 - pct : pct;
  if (v >= 0.7) return "text-emerald-400";
  if (v >= 0.4) return "text-amber-400";
  return "text-rose-400";
}

export default function MetricSlider({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  onChange,
  lowLabel,
  highLabel,
  colorScale = false,
}: Props) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-slate-300">{label}</label>
        <span
          className={cn(
            "text-sm font-bold tabular-nums",
            colorScale ? scaleColor(value, min, max) : "text-slate-100"
          )}
        >
          {value}
          {unit}
        </span>
      </div>
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full h-2 rounded-full appearance-none cursor-pointer bg-slate-700 accent-emerald-500"
          style={{
            background: `linear-gradient(to right, rgb(16 185 129) ${pct}%, rgb(51 65 85) ${pct}%)`,
          }}
        />
      </div>
      {(lowLabel || highLabel) && (
        <div className="flex justify-between text-xs text-slate-500">
          <span>{lowLabel}</span>
          <span>{highLabel}</span>
        </div>
      )}
    </div>
  );
}
