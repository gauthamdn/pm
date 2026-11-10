import { describe, expect, it } from "vitest";
import { moveCard, type Column } from "@/lib/kanban";

describe("moveCard", () => {
  const baseColumns: Column[] = [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ];

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });

  it("moves a card into an empty column", () => {
    const result = moveCard([...baseColumns, { id: "col-empty", title: "Empty", cardIds: [] }], "card-1", "col-empty");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[2].cardIds).toEqual(["card-1"]);
  });

  it("appends a card when dropped on its own column", () => {
    expect(moveCard(baseColumns, "card-1", "col-a")[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("ignores unknown source and target IDs", () => {
    expect(moveCard(baseColumns, "missing", "col-a")).toBe(baseColumns);
    expect(moveCard(baseColumns, "card-1", "missing")).toBe(baseColumns);
  });

  it("does not mutate the original columns", () => {
    moveCard(baseColumns, "card-1", "card-3");
    expect(baseColumns[0].cardIds).toEqual(["card-1", "card-2"]);
    expect(baseColumns[1].cardIds).toEqual(["card-3"]);
  });
});
