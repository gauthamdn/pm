export type User = { username: string };

export async function getSession(): Promise<User | null> {
  const response = await fetch("/api/session", {
    cache: "no-store",
    credentials: "same-origin",
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Unable to check your session. Please try again.");
  return response.json();
}

export async function signIn(username: string, password: string): Promise<User> {
  const response = await fetch("/api/session", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (response.status === 401) throw new Error("Invalid username or password.");
  if (!response.ok) throw new Error("Unable to sign in. Please try again.");
  return response.json();
}

export async function signOut(): Promise<void> {
  const response = await fetch("/api/session", {
    method: "DELETE",
    credentials: "same-origin",
  });
  if (!response.ok) throw new Error("Unable to sign out. Please try again.");
}
