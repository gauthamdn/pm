import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  it("renders five columns", () => {
    render(<KanbanBoard />);
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("rejects whitespace-only titles", async () => {
    render(<KanbanBoard />);
    const column = getFirstColumn();
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText("Card title"), "   ");
    await userEvent.click(within(column).getByRole("button", { name: "Add card" }));
    expect(within(column).getAllByTestId(/^card-/)).toHaveLength(2);
    expect(within(column).getByPlaceholderText("Card title")).toBeInTheDocument();
  });

  it("clears a cancelled draft and supplies default details", async () => {
    render(<KanbanBoard />);
    const column = getFirstColumn();
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(within(column).getByPlaceholderText("Card title"), "Draft");
    await userEvent.click(within(column).getByRole("button", { name: "Cancel" }));
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    expect(within(column).getByPlaceholderText("Card title")).toHaveValue("");
    await userEvent.type(within(column).getByPlaceholderText("Card title"), "  New task  ");
    await userEvent.click(within(column).getByRole("button", { name: "Add card" }));
    expect(within(column).getByText("New task")).toBeInTheDocument();
    expect(within(column).getByText("No details yet.")).toBeInTheDocument();
  });
});
