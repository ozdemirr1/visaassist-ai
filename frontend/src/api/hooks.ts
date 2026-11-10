import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "./client";
import type { ApplicationFile, Checklist, Language, Profile, User } from "./types";

export function useChecklist(destination: string, profile: Profile, lang: Language) {
  return useQuery({
    queryKey: ["checklist", destination, profile, lang],
    queryFn: ({ signal }) =>
      api<Checklist>(
        `/checklist?${new URLSearchParams({ destination, profile, lang })}`,
        { signal },
      ),
  });
}

/** The logged-in user, or null when there is no valid session. */
export function useCurrentUser() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async ({ signal }) => {
      try {
        return await api<User>("/auth/me", { signal });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 60_000,
  });
}

interface Credentials {
  email: string;
  password: string;
}

export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Credentials) => api<User>("/auth/login", { method: "POST", json: body }),
    onSuccess: (user) => client.setQueryData(["me"], user),
  });
}

export function useRegister() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Credentials & { language: Language }) =>
      api<User>("/auth/register", { method: "POST", json: body }),
    onSuccess: (user) => client.setQueryData(["me"], user),
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      client.setQueryData(["me"], null);
      client.removeQueries({ queryKey: ["applications"] });
    },
  });
}

export function useApplicationFiles(enabled: boolean) {
  const client = useQueryClient();
  return useQuery({
    queryKey: ["applications"],
    queryFn: async ({ signal }) => {
      try {
        return await api<ApplicationFile[]>("/applications", { signal });
      } catch (error) {
        // The session ended (expired, logged out elsewhere, or the cookie was refused):
        // show the logged-out state instead of an empty page.
        if (error instanceof ApiError && error.status === 401) client.setQueryData(["me"], null);
        throw error;
      }
    },
    enabled,
    retry: (count, error) => !(error instanceof ApiError && error.status === 401) && count < 1,
  });
}
