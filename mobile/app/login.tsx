import axios from "axios";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { TextField } from "@/components/TextField";
import { API_BASE_URL } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import { fonts, spacing } from "@/lib/theme/tokens";

type LoginFormValues = {
  email: string;
  password: string;
};

export default function LoginScreen() {
  const { login } = useAuth();
  const { colors } = useTheme();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ defaultValues: { email: "", password: "" } });

  async function onSubmit(values: LoginFormValues) {
    setServerError(null);
    try {
      await login(values.email, values.password);
      router.replace("/");
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          setServerError("Incorrect email or password.");
        } else if (!error.response) {
          setServerError(`Can't reach the server at ${API_BASE_URL}. Check EXPO_PUBLIC_API_URL in mobile/.env.`);
        } else {
          setServerError(`Login failed (${error.response.status}). Try again.`);
        }
      } else {
        setServerError("Something went wrong. Try again.");
      }
    }
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.bgBase }]}>
      <View style={styles.card}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Divum Chat</Text>
        <Text style={[styles.tagline, { color: colors.textSecondary }]}>Sign in to keep talking.</Text>

        <View style={styles.form}>
          <Controller
            control={control}
            name="email"
            rules={{ required: "Email is required" }}
            render={({ field: { onChange, onBlur, value } }) => (
              <TextField
                label="Email"
                placeholder="you@company.com"
                autoCapitalize="none"
                autoComplete="email"
                keyboardType="email-address"
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                error={errors.email?.message}
              />
            )}
          />

          <Controller
            control={control}
            name="password"
            rules={{ required: "Password is required" }}
            render={({ field: { onChange, onBlur, value } }) => (
              <TextField
                label="Password"
                placeholder="••••••••"
                secureTextEntry
                autoComplete="password"
                onBlur={onBlur}
                onChangeText={onChange}
                value={value}
                error={errors.password?.message}
              />
            )}
          />

          {serverError ? (
            <Text style={[styles.serverError, { color: colors.stateError }]}>{serverError}</Text>
          ) : null}

          {isSubmitting ? (
            <ActivityIndicator color={colors.accentMoss} />
          ) : (
            <Button label="Log in" onPress={handleSubmit(onSubmit)} disabled={isSubmitting} />
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center", padding: spacing.xl },
  card: { width: "100%", maxWidth: 380, gap: spacing.xs },
  title: { fontFamily: fonts.display, fontSize: 32, textAlign: "center" },
  tagline: { fontFamily: fonts.body, fontSize: 14, textAlign: "center", marginBottom: spacing.xl },
  form: { gap: spacing.lg },
  serverError: { fontFamily: fonts.body, fontSize: 13, textAlign: "center" },
});
