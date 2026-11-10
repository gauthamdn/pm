"use client";

import { useEffect, useState, type FormEvent } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { getSession, signIn, signOut, type User } from "@/lib/auth";

export function Workspace() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [sessionError, setSessionError] = useState("");
  const [retry, setRetry] = useState(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (pending) return;
    let active = true;
    async function checkSession() {
      try {
        const nextUser = await getSession();
        if (active) {
          setUser(nextUser);
          setSessionError("");
        }
      } catch {
        if (active) setSessionError("Unable to check your session. Please try again.");
      } finally {
        if (active) setChecking(false);
      }
    }
    void checkSession();
    const interval = window.setInterval(checkSession, 60_000);
    const onVisible = () => {
      if (document.visibilityState === "visible") void checkSession();
    };
    window.addEventListener("focus", checkSession);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      active = false;
      window.clearInterval(interval);
      window.removeEventListener("focus", checkSession);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [retry, pending]);

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password) return;
    setError("");
    setPending(true);
    try {
      setUser(await signIn(username.trim(), password));
      setSessionError("");
      setUsername("");
      setPassword("");
    } catch (cause) {
      setError(cause instanceof Error && cause.message === "Invalid username or password."
        ? cause.message : "Unable to sign in. Please try again.");
    } finally {
      setPending(false);
    }
  }

  async function handleSignOut() {
    setError("");
    setPending(true);
    try {
      await signOut();
      setUser(null);
      setUsername("");
      setPassword("");
    } catch {
      setError("Unable to sign out. Please try again.");
    } finally {
      setPending(false);
    }
  }

  if (user) {
    return <KanbanBoard onSignOut={handleSignOut} signingOut={pending} signOutError={error || sessionError} />;
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[radial-gradient(ellipse_at_top_left,_rgba(32,157,215,0.12),_transparent_60%)] px-4 py-10">
      <section className="w-full max-w-md rounded-[32px] border border-[var(--stroke)] border-t-4 border-t-[var(--accent-yellow)] bg-white p-6 shadow-[var(--shadow)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--primary-blue)]">Kanban Studio</p>
        {checking ? (
          <p role="status" className="mt-6 text-[var(--navy-dark)]">Checking your session...</p>
        ) : sessionError ? (
          <div className="mt-6 space-y-4">
            <p role="alert">{sessionError}</p>
            <button type="button" className="rounded-full bg-[var(--secondary-purple)] px-5 py-3 font-semibold text-white" onClick={() => { setChecking(true); setRetry((value) => value + 1); }}>Try again</button>
          </div>
        ) : (
          <>
            <h1 className="mt-4 font-display text-3xl font-semibold text-[var(--navy-dark)]">Welcome back</h1>
            <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">Sign in to your workspace and keep your project moving.</p>
            <form onSubmit={handleSignIn} className="mt-8 space-y-5">
              <div>
                <label htmlFor="username" className="text-sm font-semibold">Username</label>
                <input id="username" name="username" autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} disabled={pending} className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3" />
              </div>
              <div>
                <label htmlFor="password" className="text-sm font-semibold">Password</label>
                <input id="password" name="password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} disabled={pending} className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3" />
              </div>
              {error && <p role="alert" className="text-sm text-[var(--secondary-purple)]">{error}</p>}
              <button type="submit" disabled={pending} className="w-full rounded-full bg-[var(--secondary-purple)] px-5 py-3 font-semibold text-white transition hover:brightness-110 disabled:cursor-wait disabled:opacity-60">{pending ? "Signing in..." : "Sign in"}</button>
            </form>
          </>
        )}
      </section>
    </main>
  );
}
