import type { ColumnDef } from "@tanstack/react-table";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DataTable } from "../components/DataTable";
import { ErrorState, LoadingState } from "../components/QueryState";
import { StatusBadge } from "../components/StatusBadge";

interface Row { name: string }
const columns: ColumnDef<Row>[] = [{ header: "Name", accessorKey: "name" }];

describe("shared components", () => {
  it("maps trust states to understandable badge tones", () => {
    const { rerender } = render(<StatusBadge status="aligned" />);
    expect(screen.getByText("Entspricht der ausgewählten Empfehlung").parentElement).toHaveClass("status-success");
    rerender(<StatusBadge status="not_evaluable" />);
    expect(screen.getByText("Nicht bewertbar").parentElement).toHaveClass("status-unknown");
  });

  it("paginates a keyboard-focusable table", async () => {
    const user = userEvent.setup();
    render(<DataTable data={[{ name: "One" }, { name: "Two" }]} columns={columns} label="Example table" pageSize={1} />);
    expect(screen.getByRole("region", { name: "Example table" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByText("One")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Nächste Seite" }));
    expect(screen.getByText("Two")).toBeVisible();
  });

  it("sorts an accessible column without recalculating audit data", async () => {
    const user = userEvent.setup();
    render(<DataTable data={[{ name: "Zulu" }, { name: "Alpha" }]} columns={columns} label="Sortable table" />);
    const sort = screen.getByRole("button", { name: /Name/ });
    await user.click(sort);
    expect(sort.closest("th")).toHaveAttribute("aria-sort", "ascending");
    expect(screen.getAllByRole("row")[1]).toHaveTextContent("Alpha");
  });

  it("renders empty, loading, and error states", () => {
    const { rerender } = render(<DataTable data={[]} columns={columns} label="Empty" />);
    expect(screen.getByText("Keine passenden Einträge")).toBeVisible();
    rerender(<LoadingState />);
    expect(screen.getByRole("status")).toBeVisible();
    rerender(<ErrorState error={new Error("offline")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("offline");
    fireEvent.keyDown(window, { key: "Escape" });
  });
});
