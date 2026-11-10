import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Workspace } from "@/components/Workspace";
import { getSession, signIn, signOut, type User } from "@/lib/auth";

vi.mock("@/lib/auth", () => ({ getSession: vi.fn(), signIn: vi.fn(), signOut: vi.fn() }));

let currentUser: User | null;

beforeEach(() => {
  vi.resetAllMocks();
  currentUser = null;
  vi.mocked(getSession).mockImplementation(async () => currentUser);
  vi.mocked(signIn).mockImplementation(async () => {
    currentUser = { username: "user" };
    return currentUser;
  });
  vi.mocked(signOut).mockImplementation(async () => { currentUser = null; });
});

afterEach(() => vi.useRealTimers());

async function enterCredentials() {
  await userEvent.type(await screen.findByLabelText("Username"), "user");
  await userEvent.type(screen.getByLabelText("Password"), "password");
}

async function expectBoard() {
  expect(await screen.findByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();
}

describe("Workspace", () => {
  it("keeps the board hidden while resolving the session", async () => {
    let resolve!: (user: User | null) => void;
    vi.mocked(getSession).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    render(<Workspace />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking your session");
    expect(screen.queryByText("Align roadmap themes")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Username")).not.toBeInTheDocument();
    await act(async () => resolve({ username: "user" }));
    await expectBoard();
  });

  it("requires both fields and rejects whitespace-only usernames", async () => {
    render(<Workspace />);
    await screen.findByLabelText("Username");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(signIn).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText("Username"), "   ");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(signIn).not.toHaveBeenCalled();
  });

  it("disables duplicate submissions while signing in", async () => {
    let resolve!: (user: User) => void;
    vi.mocked(signIn).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    render(<Workspace />);
    await enterCredentials();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    const button = screen.getByRole("button", { name: "Signing in..." });
    expect(button).toBeDisabled();
    expect(screen.getByLabelText("Password")).toBeDisabled();
    await userEvent.click(button);
    expect(signIn).toHaveBeenCalledTimes(1);
    currentUser = { username: "user" };
    await act(async () => resolve(currentUser!));
    await expectBoard();
  });

  it("shows invalid credentials and retains inputs for retry", async () => {
    vi.mocked(signIn).mockRejectedValueOnce(new Error("Invalid username or password."));
    render(<Workspace />);
    await enterCredentials();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username or password.");
    expect(screen.getByLabelText("Username")).toHaveValue("user");
    expect(screen.getByLabelText("Password")).toHaveValue("password");
    expect(screen.queryByText("Align roadmap themes")).not.toBeInTheDocument();
  });

  it("shows a friendly network error and allows another sign-in attempt", async () => {
    vi.mocked(signIn).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    render(<Workspace />);
    await enterCredentials();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to sign in. Please try again.");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await expectBoard();
  });

  it("retries failed initial session lookup", async () => {
    vi.mocked(getSession).mockRejectedValueOnce(new Error("offline"));
    render(<Workspace />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to check your session");
    expect(screen.queryByText("Align roadmap themes")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByLabelText("Username")).toBeInTheDocument();
  });

  it("clears private board state on sign-out and clears credential fields", async () => {
    currentUser = { username: "user" };
    render(<Workspace />);
    await expectBoard();
    const column = screen.getByTestId("column-col-backlog");
    await userEvent.click(within(column).getByRole("button", { name: "Add a card" }));
    await userEvent.type(within(column).getByLabelText("Card title"), "Private draft");
    await userEvent.click(within(column).getByRole("button", { name: "Add card" }));
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByLabelText("Password")).toHaveValue("");
    expect(screen.queryByText("Private draft")).not.toBeInTheDocument();
    await enterCredentials();
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await expectBoard();
    expect(screen.queryByText("Private draft")).not.toBeInTheDocument();
  });

  it("keeps the board available if sign-out fails", async () => {
    currentUser = { username: "user" };
    vi.mocked(signOut).mockRejectedValueOnce(new Error("offline"));
    render(<Workspace />);
    await expectBoard();
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to sign out");
    await expectBoard();
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByLabelText("Username")).toBeInTheDocument();
  });

  it("returns to sign-in when the session is revoked on focus", async () => {
    currentUser = { username: "user" };
    render(<Workspace />);
    await expectBoard();
    currentUser = null;
    fireEvent(window, new Event("focus"));
    expect(await screen.findByLabelText("Username")).toBeInTheDocument();
    expect(screen.queryByText("Align roadmap themes")).not.toBeInTheDocument();
  });

  it("checks for expiry every minute", async () => {
    vi.useFakeTimers();
    currentUser = { username: "user" };
    render(<Workspace />);
    await act(async () => {});
    expect(screen.getByText("Align roadmap themes")).toBeInTheDocument();
    currentUser = null;
    await act(async () => { vi.advanceTimersByTime(60_000); });
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.queryByText("Align roadmap themes")).not.toBeInTheDocument();
  });

  it("ignores a late session response after sign-out", async () => {
    currentUser = { username: "user" };
    render(<Workspace />);
    await expectBoard();
    let resolve!: (user: User) => void;
    vi.mocked(getSession).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
    fireEvent(window, new Event("focus"));
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await screen.findByLabelText("Username");
    await act(async () => resolve({ username: "user" }));
    expect(screen.queryByText("Align roadmap themes")).not.toBeInTheDocument();
  });

  it("retains board edits when a background session check has a network failure", async () => {
    currentUser = { username: "user" };
    render(<Workspace />);
    await expectBoard();
    const title = within(screen.getByTestId("column-col-backlog")).getByLabelText("Column title");
    await userEvent.clear(title);
    await userEvent.type(title, "My draft column");
    vi.mocked(getSession).mockRejectedValueOnce(new Error("offline"));
    fireEvent(window, new Event("focus"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to check your session");
    expect(title).toHaveValue("My draft column");
    fireEvent(window, new Event("focus"));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(title).toHaveValue("My draft column");
  });
});
