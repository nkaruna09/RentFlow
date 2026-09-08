"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { listLeases } from "@/lib/api/leases";
import { listUnits } from "@/lib/api/units";
import { computeOverviewStats, listAllPages, MAX_API_PAGE_SIZE } from "@/lib/dashboard";
import type { Lease, Unit } from "@/types/api";

export default function DashboardPage() {
  const [units, setUnits] = useState<Unit[]>([]);
  const [leases, setLeases] = useState<Lease[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [allUnits, allLeases] = await Promise.all([
        listAllPages<Unit>((page) => listUnits({ page, page_size: MAX_API_PAGE_SIZE })),
        listAllPages<Lease>((page) => listLeases({ page, page_size: MAX_API_PAGE_SIZE })),
      ]);

      setUnits(allUnits);
      setLeases(allLeases);
    } catch (apiError) {
      const message =
        apiError instanceof Error ? apiError.message : "Unable to load dashboard stats.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();

    const intervalId = window.setInterval(() => {
      void loadOverview();
    }, 30000);

    return () => window.clearInterval(intervalId);
  }, [loadOverview]);

  const stats = useMemo(() => computeOverviewStats(units, leases), [leases, units]);

  const cards = [
    {
      label: "Occupancy",
      value: `${stats.occupancyPercentage}%`,
      detail: `${Math.max(stats.totalUnits - stats.vacantUnits, 0)} of ${stats.totalUnits} units occupied`,
      tone: "bg-sky-50 text-sky-700 ring-sky-200",
    },
    {
      label: "Active leases",
      value: String(stats.activeLeaseCount),
      detail: "Current active lease count",
      tone: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    },
    {
      label: "Vacant units",
      value: String(stats.vacantUnits),
      detail: "Units currently marked vacant",
      tone: "bg-amber-50 text-amber-700 ring-amber-200",
    },
    {
      label: "Rent collected",
      value: "TBD",
      detail: "Placeholder for M4",
      tone: "bg-slate-100 text-slate-600 ring-slate-200",
    },
    {
      label: "Open work orders",
      value: "TBD",
      detail: "Placeholder for M5",
      tone: "bg-slate-100 text-slate-600 ring-slate-200",
    },
  ];

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600">
            Live portfolio snapshot across units and leases.
          </p>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
          Loading dashboard stats...
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {cards.map((card) => (
            <div key={card.label} className={`rounded-2xl border p-5 shadow-sm ring-1 ${card.tone}`}>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-current/80">
                {card.label}
              </p>
              <p className="mt-4 text-3xl font-semibold text-slate-900">{card.value}</p>
              <p className="mt-2 text-sm text-slate-600">{card.detail}</p>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Rent collected and open work orders remain placeholders until the M4 and M5 milestones are implemented.
      </div>
    </section>
  );
}
