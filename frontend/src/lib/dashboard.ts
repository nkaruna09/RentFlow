import type { Lease, Unit } from "@/types/api";

type LeaseHistoryRecord = {
  status?: string;
  start_date?: string;
  end_date?: string;
  rent_amount?: string;
};

export const MAX_API_PAGE_SIZE = 100;

export async function listAllPages<T>(
  loadPage: (page: number) => Promise<{ items: T[]; total: number }>,
): Promise<T[]> {
  const firstPage = await loadPage(1);
  const pageCount = Math.ceil(firstPage.total / MAX_API_PAGE_SIZE);
  if (pageCount <= 1) return firstPage.items;

  const remainingPages = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) => loadPage(index + 2)),
  );
  return [firstPage, ...remainingPages].flatMap((response) => response.items);
}

export function computeOverviewStats(
  units: Pick<Unit, "status">[],
  leases: Pick<Lease, "status">[],
) {
  const totalUnits = units.length;
  const vacantUnits = units.filter((unit) => unit.status === "vacant").length;
  const activeLeaseCount = leases.filter((lease) => lease.status === "active").length;
  const occupancyPercentage =
    totalUnits === 0 ? 0 : Math.round(((totalUnits - vacantUnits) / totalUnits) * 100);

  return {
    totalUnits,
    vacantUnits,
    activeLeaseCount,
    occupancyPercentage,
  };
}

export function filterUnits<T extends { property_id: string; status: string }>(
  rows: T[],
  propertyId?: string,
  status?: string,
): T[] {
  return rows.filter((row) => {
    const matchesProperty = !propertyId || row.property_id === propertyId;
    const matchesStatus = !status || row.status === status;
    return matchesProperty && matchesStatus;
  });
}

export function summarizeLeaseHistory(leases: LeaseHistoryRecord[]): string {
  if (!leases.length) {
    return "No lease history on record.";
  }

  const sorted = [...leases].sort(
    (left, right) =>
      new Date(right.start_date ?? "1970-01-01").getTime() -
      new Date(left.start_date ?? "1970-01-01").getTime(),
  );

  const latest = sorted[0];
  if (!latest) {
    return "No lease history on record.";
  }

  const status = latest.status
    ? latest.status.charAt(0).toUpperCase() + latest.status.slice(1)
    : "Unknown";
  const rent = latest.rent_amount
    ? `$${Number(latest.rent_amount).toFixed(2)}`
    : "Rent unavailable";

  return `${status} lease · ${latest.start_date ?? "n/a"} to ${latest.end_date ?? "n/a"} · ${rent}`;
}
