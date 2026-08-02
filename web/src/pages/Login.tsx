import axios from "axios";
import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { API_BASE_URL } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthContext";
import styles from "./Login.module.css";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setServerError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          setServerError("Incorrect email or password.");
        } else if (!error.response) {
          setServerError(`Can't reach the server at ${API_BASE_URL}. Check VITE_API_URL in web/.env.`);
        } else {
          setServerError(`Login failed (${error.response.status}). Try again.`);
        }
      } else {
        setServerError("Something went wrong. Try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <form className={styles.card} onSubmit={handleSubmit}>
        <h1 className={styles.title}>Divum Chat</h1>
        <p className={styles.tagline}>Sign in to keep talking.</p>

        <label className={styles.field}>
          <span className={styles.label}>Email</span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Password</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
        </label>

        {serverError ? <p className={styles.error}>{serverError}</p> : null}

        <button type="submit" className={styles.submit} disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Log in"}
        </button>
      </form>
    </div>
  );
}
