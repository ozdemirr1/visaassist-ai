import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "./client";
import type { ApplicationFile, Checklist, DocumentInfo, Language, Profile, User } from "./types";

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

export interface NewApplicationFile {
  destination: string;
  profile: Profile;
  trip_start: string;
  trip_end: string;
  application_date?: string;
}

export function useCreateApplicationFile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: NewApplicationFile) =>
      api<ApplicationFile>("/applications", { method: "POST", json: body }),
    onSuccess: (file) => {
      client.setQueryData(["applications", file.id], file);
      void client.invalidateQueries({ queryKey: ["applications"], exact: true });
    },
  });
}

export function useApplicationFile(id: string) {
  return useQuery({
    queryKey: ["applications", id],
    queryFn: ({ signal }) => api<ApplicationFile>(`/applications/${id}`, { signal }),
    retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 1,
  });
}

export function useUpdateApplicationFile(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<Pick<ApplicationFile, "step" | "trip_start" | "trip_end">>) =>
      api<ApplicationFile>(`/applications/${id}`, { method: "PATCH", json: body }),
    onSuccess: (file) => {
      client.setQueryData(["applications", id], file);
      void client.invalidateQueries({ queryKey: ["applications"], exact: true });
    },
  });
}

export function useDeleteApplicationFile(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>(`/applications/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      client.removeQueries({ queryKey: ["applications", id] });
      void client.invalidateQueries({ queryKey: ["applications"], exact: true });
    },
  });
}

/** Documents uploaded to an application file (which checklist items are ready). */
export function useDocuments(applicationFileId: string) {
  return useQuery({
    queryKey: ["applications", applicationFileId, "documents"],
    queryFn: ({ signal }) =>
      api<DocumentInfo[]>(`/applications/${applicationFileId}/documents`, { signal }),
  });
}
