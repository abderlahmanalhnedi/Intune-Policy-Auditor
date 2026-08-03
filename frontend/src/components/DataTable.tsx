import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState } from "@tanstack/react-table";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  label: string;
  pageSize?: number;
  emptyMessage?: string;
}

export function DataTable<T>({ data, columns, label, pageSize = 12, emptyMessage }: DataTableProps<T>) {
  const { t } = useTranslation();
  const [page, setPage] = useState(0);
  const [sorting, setSorting] = useState<SortingState>([]);
  const pageCount = Math.max(Math.ceil(data.length / pageSize), 1);
  const safePage = Math.min(page, pageCount - 1);
  const table = useReactTable({ data, columns, state: { sorting }, onSortingChange: (update) => { setSorting((current) => typeof update === "function" ? update(current) : update); setPage(0); }, getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel() });
  const visibleRows = table.getRowModel().rows.slice(safePage * pageSize, (safePage + 1) * pageSize);

  if (data.length === 0) return <div className="empty-state"><strong>{emptyMessage ?? t("common.noResults")}</strong></div>;
  return (
    <div className="table-region">
      <div className="table-scroll" tabIndex={0} role="region" aria-label={label}>
        <table className="data-table">
          <caption className="sr-only">{label}</caption>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => <th scope="col" key={header.id} aria-sort={header.column.getIsSorted() === "asc" ? "ascending" : header.column.getIsSorted() === "desc" ? "descending" : "none"}>{header.isPlaceholder ? null : header.column.getCanSort() ? <button className="table-sort" type="button" onClick={header.column.getToggleSortingHandler()}>{flexRender(header.column.columnDef.header, header.getContext())}<span aria-hidden>{header.column.getIsSorted() === "asc" ? "▲" : header.column.getIsSorted() === "desc" ? "▼" : "↕"}</span></button> : flexRender(header.column.columnDef.header, header.getContext())}</th>)}
              </tr>
            ))}
          </thead>
          <tbody>
            {visibleRows.map((row) => (
              <tr key={row.id}>{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      {pageCount > 1 ? (
        <nav className="pagination" aria-label={t("common.pagination")}>
          <button type="button" onClick={() => setPage(Math.max(safePage - 1, 0))} disabled={safePage === 0} aria-label={t("common.previous")}><ChevronLeft size={17} aria-hidden /></button>
          <span>{t("common.pageOf", { page: safePage + 1, pages: pageCount })}</span>
          <button type="button" onClick={() => setPage(Math.min(safePage + 1, pageCount - 1))} disabled={safePage + 1 >= pageCount} aria-label={t("common.next")}><ChevronRight size={17} aria-hidden /></button>
        </nav>
      ) : null}
    </div>
  );
}
