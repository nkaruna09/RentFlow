"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { PropertyForm, type PropertyFormValues } from "@/components/forms/property-form";
import { DataTable, type Column, type SortDirection } from "@/components/tables/data-table";
import { Button } from "@/components/ui/button";
import {
  createProperty,
  deleteProperty,
  listProperties,
  updateProperty,
} from "@/lib/api/properties";
import type { Property } from "@/types/api";

const PAGE_SIZE = 10;

const propertyColumns: Column<Property>[] = [
  { key: "name", header: "Name", sortable: true, accessor: (row) => row.name },
  {
    key: "address_line1",
    header: "Address",
    sortable: true,
    accessor: (row) => row.address_line1,
    render: (row) => (
      <span>
        {row.address_line1}
        {row.address_line2 ? `, ${row.address_line2}` : ""}
      </span>
    ),
  },
  { key: "city", header: "City", sortable: true, accessor: (row) => row.city },
  { key: "property_type", header: "Type", sortable: true, accessor: (row) => row.property_type },
  {
    key: "actions",
    header: "Actions",
    sortable: false,
    render: () => (
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-sky-300 hover:text-sky-700"
          onClick={() => undefined}
        >
          Edit
        </button>
        <button
          type="button"
          className="rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100"
          onClick={() => undefined}
        >
          Delete
        </button>
      </div>
    ),
  },
];

function toFormValues(property: Property): PropertyFormValues {
  return {
    name: property.name,
    address_line1: property.address_line1,
    address_line2: property.address_line2 ?? "",
    city: property.city,
    region: property.region,
    postal_code: property.postal_code,
    country: property.country,
    property_type: property.property_type,
  };
}

export default function PropertiesPage() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<string | null>("name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const loadProperties = useCallback(
    async (nextPage: number) => {
      setLoading(true);
      setError(null);

      try {
        const response = await listProperties({ page: nextPage, page_size: PAGE_SIZE });
        setProperties(response.items);
        setTotal(response.total);
      } catch (apiError) {
        const message =
          apiError instanceof Error ? apiError.message : "Unable to load properties.";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadProperties(page);
  }, [loadProperties, page]);

  const handleSortChange = (key: string, direction: SortDirection) => {
    setSortKey(key);
    setSortDirection(direction);
  };

  const startNewProperty = useCallback(() => {
    setSelectedProperty(null);
    setIsFormOpen(true);
  }, []);

  const startEdit = useCallback((property: Property) => {
    setSelectedProperty(property);
    setIsFormOpen(true);
  }, []);

  const handleCloseForm = useCallback(() => {
    setSelectedProperty(null);
    setIsFormOpen(false);
  }, []);

  const handleSubmit = async (values: PropertyFormValues) => {
    setSubmitting(true);
    setError(null);

    try {
      if (selectedProperty) {
        await updateProperty(selectedProperty.id, values);
      } else {
        await createProperty(values);
      }

      setPage(1);
      setSortKey("name");
      setSortDirection("asc");
      await loadProperties(1);
      handleCloseForm();
    } catch (apiError) {
      const message =
        apiError instanceof Error ? apiError.message : "Unable to save property.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = useCallback(
    async (property: Property) => {
      if (!window.confirm(`Delete ${property.name}? This action cannot be undone.`)) {
        return;
      }

      setDeletingId(property.id);
      setError(null);

      try {
        await deleteProperty(property.id);
        const nextPage = properties.length === 1 && page > 1 ? page - 1 : page;
        setPage(nextPage);
        await loadProperties(nextPage);
      } catch (apiError) {
        const message =
          apiError instanceof Error ? apiError.message : "Unable to delete property.";
        setError(message);
      } finally {
        setDeletingId(null);
      }
    },
    [loadProperties, page, properties.length],
  );

  const displayColumns = useMemo<Column<Property>[]>(
    () => [
      ...propertyColumns.slice(0, 4),
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
    [deletingId, handleDelete, startEdit],
  );

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">Properties</h1>
          <p className="mt-1 text-sm text-slate-600">
            Manage your portfolio and property details.
          </p>
        </div>

        <Button type="button" onClick={startNewProperty}>
          Add property
        </Button>
      </div>

      {isFormOpen ? (
        <PropertyForm
          initialValues={selectedProperty ? toFormValues(selectedProperty) : null}
          submitLabel={selectedProperty ? "Update property" : "Create property"}
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
            Loading properties...
          </div>
        ) : (
          <DataTable
            columns={displayColumns}
            data={properties}
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
