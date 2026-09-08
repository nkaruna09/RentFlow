"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { UnitForm, type UnitFormValues } from "@/components/forms/unit-form";
import { DataTable, type Column, type SortDirection } from "@/components/tables/data-table";
import { Button } from "@/components/ui/button";
import { listProperties } from "@/lib/api/properties";
import { createUnit, deleteUnit, listUnits, updateUnit } from "@/lib/api/units";
import type { Property, Unit, UnitStatus } from "@/types/api";

const PAGE_SIZE = 10;

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

function toFormValues(unit: Unit): UnitFormValues {
  return {
    property_id: unit.property_id,
    label: unit.label,
    bedrooms: unit.bedrooms,
    bathrooms: unit.bathrooms,
    square_feet: unit.square_feet ?? null,
    market_rent: unit.market_rent,
    status: unit.status,
  };
}

const statusOptions: Array<{ value: UnitStatus | "all"; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "vacant", label: "Vacant" },
  { value: "occupied", label: "Occupied" },
  { value: "unavailable", label: "Unavailable" },
];

export default function UnitsPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState<Unit | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [propertyFilter, setPropertyFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<UnitStatus | "all">("all");
  const [sortKey, setSortKey] = useState<string | null>("label");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const loadProperties = useCallback(async () => {
    try {
      const response = await listProperties({ page: 1, page_size: 100 });
      setProperties(response.items);
    } catch (apiError) {
      const message =
        apiError instanceof Error ? apiError.message : "Unable to load properties.";
      setError(message);
    }
  }, []);

  const loadUnits = useCallback(
    async (nextPage: number) => {
      setLoading(true);
      setError(null);

      try {
        const response = await listUnits({
          page: nextPage,
          page_size: PAGE_SIZE,
          property_id: propertyFilter === "all" ? undefined : propertyFilter,
          status: statusFilter === "all" ? undefined : statusFilter,
        });
        setUnits(response.items);
        setTotal(response.total);
      } catch (apiError) {
        const message = apiError instanceof Error ? apiError.message : "Unable to load units.";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [propertyFilter, statusFilter],
  );

  useEffect(() => {
    void loadProperties();
  }, [loadProperties]);

  useEffect(() => {
    void loadUnits(page);
  }, [loadUnits, page]);

  const propertyLookup = useMemo(
    () => Object.fromEntries(properties.map((property) => [property.id, property.name])),
    [properties],
  );

  const filteredUnits = useMemo(
    () =>
      filterUnits(
        units,
        propertyFilter === "all" ? undefined : propertyFilter,
        statusFilter === "all" ? undefined : statusFilter,
      ),
    [propertyFilter, statusFilter, units],
  );

  const handleSortChange = (key: string, direction: SortDirection) => {
    setSortKey(key);
    setSortDirection(direction);
  };

  const startNewUnit = useCallback(() => {
    setSelectedUnit(null);
    setIsFormOpen(true);
  }, []);

  const startEdit = useCallback((unit: Unit) => {
    setSelectedUnit(unit);
    setIsFormOpen(true);
  }, []);

  const handleCloseForm = useCallback(() => {
    setSelectedUnit(null);
    setIsFormOpen(false);
  }, []);

  const handleSubmit = async (values: UnitFormValues) => {
    setSubmitting(true);
    setError(null);

    try {
      if (selectedUnit) {
        const { property_id: _property_id, ...updates } = values;
        await updateUnit(selectedUnit.id, updates);
      } else {
        await createUnit(values);
      }

      setPage(1);
      setSortKey("label");
      setSortDirection("asc");
      handleCloseForm();
    } catch (apiError) {
      const message = apiError instanceof Error ? apiError.message : "Unable to save unit.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = useCallback(
    async (unit: Unit) => {
      if (!window.confirm(`Delete ${unit.label}? This action cannot be undone.`)) {
        return;
      }

      setDeletingId(unit.id);
      setError(null);

      try {
        await deleteUnit(unit.id);
        const nextPage = units.length === 1 && page > 1 ? page - 1 : page;
        setPage(nextPage);
      } catch (apiError) {
        const message = apiError instanceof Error ? apiError.message : "Unable to delete unit.";
        setError(message);
      } finally {
        setDeletingId(null);
      }
    },
    [page, units.length],
  );

  const handleFilterChange = (nextProperty: string, nextStatus: UnitStatus | "all") => {
    setPropertyFilter(nextProperty);
    setStatusFilter(nextStatus);
    setPage(1);
  };

  const displayColumns = useMemo<Column<Unit>[]>(
    () => [
      { key: "label", header: "Unit", sortable: true, accessor: (row) => row.label },
      {
        key: "property_id",
        header: "Property",
        sortable: true,
        accessor: (row) => propertyLookup[row.property_id] ?? row.property_id,
        render: (row) => <span>{propertyLookup[row.property_id] ?? "Unknown property"}</span>,
      },
      {
        key: "status",
        header: "Status",
        sortable: true,
        accessor: (row) => row.status,
        render: (row) => (
          <span className="inline-flex rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-xs font-medium capitalize text-slate-700">
            {row.status}
          </span>
        ),
      },
      { key: "bedrooms", header: "Bedrooms", sortable: true, accessor: (row) => row.bedrooms },
      { key: "bathrooms", header: "Bathrooms", sortable: true, accessor: (row) => row.bathrooms },
      {
        key: "market_rent",
        header: "Rent",
        sortable: true,
        accessor: (row) => row.market_rent,
        render: (row) => <span>${Number(row.market_rent).toFixed(2)}</span>,
      },
      {
        key: "actions",
        header: "Actions",
        sortable: false,
        render: (row) => (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-sky-300 hover:text-sky-700"
              onClick={() => startEdit(row)}
            >
              Edit
            </button>
            <button
              type="button"
              className="rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => handleDelete(row)}
              disabled={deletingId === row.id}
            >
              {deletingId === row.id ? "Deleting..." : "Delete"}
            </button>
          </div>
        ),
      },
    ],
    [deletingId, handleDelete, propertyLookup, startEdit],
  );

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">Units</h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage unit availability, rent, and portfolio assignments.
          </p>
        </div>

        <Button type="button" onClick={startNewUnit}>
          Add unit
        </Button>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-property-filter">
              Property
            </label>
            <select
              id="unit-property-filter"
              value={propertyFilter}
              onChange={(event) => handleFilterChange(event.target.value, statusFilter)}
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            >
              <option value="all">All properties</option>
              {properties.map((property) => (
                <option key={property.id} value={property.id}>
                  {property.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700" htmlFor="unit-status-filter">
              Status
            </label>
            <select
              id="unit-status-filter"
              value={statusFilter}
              onChange={(event) =>
                handleFilterChange(propertyFilter, event.target.value as UnitStatus | "all")
              }
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <Button
              type="button"
              variant="secondary"
              className="w-full"
              onClick={() => handleFilterChange("all", "all")}
              disabled={propertyFilter === "all" && statusFilter === "all"}
            >
              Reset filters
            </Button>
          </div>
        </div>
      </div>

      {isFormOpen ? (
        <UnitForm
          initialValues={selectedUnit ? toFormValues(selectedUnit) : null}
          properties={properties}
          submitLabel={selectedUnit ? "Update unit" : "Create unit"}
          isSaving={submitting}
          onSubmit={handleSubmit}
          onCancel={handleCloseForm}
        />
      ) : null}

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-lg shadow-slate-200/50 sm:p-6">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-sm text-slate-600">
            Loading units...
          </div>
        ) : (
          <DataTable
            columns={displayColumns}
            data={filteredUnits}
            rowKey={(row) => row.id}
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            sortKey={sortKey}
            sortDirection={sortDirection}
            onPageChange={setPage}
            onSortChange={handleSortChange}
          />
        )}
      </div>
    </section>
  );
}
