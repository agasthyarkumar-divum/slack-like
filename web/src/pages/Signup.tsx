import axios from "axios";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { API_BASE_URL } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthContext";
import styles from "./Signup.module.css";

export default function Signup() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setServerError(null);

    if (password !== confirmPassword) {
      setServerError("Passwords don't match.");
      return;
    }
    if (password.length < 8) {
      setServerError("Password must be at least 8 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register(email, password, displayName);
      navigate("/");
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 409) {
          setServerError("An account with this email already exists.");
        } else if (error.response?.status === 422) {
          setServerError("Check your details and try again.");
        } else if (!error.response) {
          setServerError(`Can't reach the server at ${API_BASE_URL}. Check VITE_API_URL in web/.env.`);
        } else {
          setServerError(`Sign up failed (${error.response.status}). Try again.`);
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
        <p className={styles.tagline}>Create your account.</p>

        <label className={styles.field}>
          <span className={styles.label}>Name</span>
          <input
            type="text"
            autoComplete="name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Alice Example"
            required
          />
        </label>

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
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
            minLength={8}
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Confirm password</span>
          <input
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
            minLength={8}
            required
          />
        </label>

        {serverError ? <p className={styles.error}>{serverError}</p> : null}

        <button type="submit" className={styles.submit} disabled={isSubmitting}>
          {isSubmitting ? "Creating account…" : "Create account"}
        </button>

        <p className={styles.footer}>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
