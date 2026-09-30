"use client";

import { Badge, type BadgeVariant } from "@/components/ui/badge";
import type {
  MaintenancePriority,
  MaintenanceRequest,
  MaintenanceStatus,
} from "@/types/api";

const statusColumns: Array<{
  status: MaintenanceStatus;
  label: string;
  accent: string;
}> = [
  { status: "open", label: "Open", accent: "bg-sky-500" },
  { status: "assigned", label: "Assigned", accent: "bg-violet-500" },
  { status: "in_progress", label: "In progress", accent: "bg-amber-500" },
  { status: "resolved", label: "Resolved", accent: "bg-emerald-500" },
  { status: "closed", label: "Closed", accent: "bg-slate-500" },
];

const statusLabels: Record<MaintenanceStatus, string> = Object.fromEntries(
  statusColumns.map(({ status, label }) => [status, label]),
) as Record<MaintenanceStatus, string>;

const nextStatuses: Record<MaintenanceStatus, MaintenanceStatus[]> = {
  open: ["assigned"],
  assigned: ["in_progress"],
  in_progress: ["resolved"],
  resolved: ["closed", "open"],
  closed: ["open"],
};

const priorityVariants: Record<MaintenancePriority, BadgeVariant> = {
  low: "neutral",
  medium: "info",
  high: "warning",
  emergency: "danger",
};

const dateFormatter = new Intl.DateTimeFormat("en-CA", {
  dateStyle: "medium",
});

export interface MaintenanceBoardProps {
  requests: MaintenanceRequest[];
  unitLabels: Record<string, string>;
  updatingIds?: ReadonlySet<string>;
  canManageStatus?: boolean;
  onStatusChange: (
    request: MaintenanceRequest,
    status: MaintenanceStatus,
  ) => void | Promise<void>;
}

function RequestCard({
  request,
  unitLabel,
  isUpdating,
  canManageStatus,
  onStatusChange,
}: {
  request: MaintenanceRequest;
  unitLabel: string;
  isUpdating: boolean;
  canManageStatus: boolean;
  onStatusChange: MaintenanceBoardProps["onStatusChange"];
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold leading-5 text-slate-900">
          {request.title}
        </h3>
        <Badge variant={priorityVariants[request.priority]}>
          {request.priority}
        </Badge>
      </div>

      <p className="mt-2 line-clamp-3 text-sm leading-5 text-slate-600">
        {request.description}
      </p>

      <div className="mt-3 space-y-1 text-xs text-slate-500">
        <p className="font-medium text-slate-700">{unitLabel}</p>
        <p>Reported {dateFormatter.format(new Date(request.created_at))}</p>
      </div>

      {canManageStatus ? (
        <div className="mt-4">
          <label
            className="sr-only"
            htmlFor={`maintenance-status-${request.id}`}
          >
            Change status for {request.title}
          </label>
          <select
            id={`maintenance-status-${request.id}`}
            value=""
            disabled={isUpdating}
            onChange={(event) => {
              const status = event.target.value as MaintenanceStatus;
              if (status) void onStatusChange(request, status);
            }}
            className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-xs font-medium text-slate-700 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100 disabled:cursor-wait disabled:opacity-60"
          >
            <option value="" disabled>
              {isUpdating ? "Updating..." : "Change status"}
            </option>
            {nextStatuses[request.status].map((status) => (
              <option key={status} value={status}>
                {status === "open"
                  ? "Reopen"
                  : status === "assigned"
                    ? "Assign to me"
                    : `Move to ${statusLabels[status]}`}
              </option>
            ))}
          </select>
        </div>
      ) : null}
    </article>
  );
}

export function MaintenanceBoard({
  requests,
  unitLabels,
  updatingIds = new Set<string>(),
  canManageStatus = true,
  onStatusChange,
}: MaintenanceBoardProps) {
  return (
    <div className="overflow-x-auto pb-2">
      <div className="grid min-w-[1180px] grid-cols-5 gap-4">
        {statusColumns.map((column) => {
          const columnRequests = requests.filter(
            (request) => request.status === column.status,
          );

          return (
            <section
              key={column.status}
              aria-labelledby={`maintenance-column-${column.status}`}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50"
            >
              <div className={`h-1 ${column.accent}`} />
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
                <h2
                  id={`maintenance-column-${column.status}`}
                  className="text-sm font-semibold text-slate-900"
                >
                  {column.label}
                </h2>
                <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-600 shadow-sm">
                  {columnRequests.length}
                </span>
              </div>

              <div className="min-h-40 space-y-3 p-3">
                {columnRequests.length ? (
                  columnRequests.map((request) => (
                    <RequestCard
                      key={request.id}
                      request={request}
                      unitLabel={
                        unitLabels[request.unit_id] ??
                        `Unit ${request.unit_id.slice(0, 8)}`
                      }
                      isUpdating={updatingIds.has(request.id)}
                      canManageStatus={canManageStatus}
                      onStatusChange={onStatusChange}
                    />
                  ))
                ) : (
                  <div className="rounded-xl border border-dashed border-slate-300 px-3 py-8 text-center text-xs text-slate-400">
                    No requests
                  </div>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
