"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Dashboard", icon: "⚡" },
  { href: "/checkin", label: "Check In", icon: "✅" },
  { href: "/history", label: "Trends", icon: "📈" },
  { href: "/goals", label: "Goals", icon: "🎯" },
];

export default function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-800 bg-slate-950/95 backdrop-blur supports-[backdrop-filter]:bg-slate-950/80 md:static md:border-t-0 md:border-b md:bg-transparent">
      <div className="mx-auto flex max-w-5xl items-center justify-around px-4 py-2 md:justify-start md:gap-1 md:px-6 md:py-4">
        <span className="hidden text-lg font-bold text-emerald-400 md:block md:mr-8">
          HealthSpan
        </span>
        {links.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-col items-center gap-0.5 rounded-lg px-3 py-2 text-xs font-medium transition-colors md:flex-row md:gap-2 md:text-sm",
              pathname === href
                ? "bg-emerald-500/10 text-emerald-400"
                : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
            )}
          >
            <span className="text-base md:text-sm">{icon}</span>
            <span>{label}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
