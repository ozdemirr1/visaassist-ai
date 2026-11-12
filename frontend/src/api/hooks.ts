import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "./client";
import type {
  ApplicationFile,
  CheckResult,
  CheckRun,
  Checklist,
  Destinations,
  ConsentState,
  DocumentFields,
  DocumentInfo,
  FieldValue,
  Language,
  Profile,
  User,
} from "./types";

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
      client.removeQueries({ queryKey: ["consent"] });
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

const documentsKey = (applicationFileId: string) => ["applications", applicationFileId, "documents"];
const checkKey = (applicationFileId: string) => ["applications", applicationFileId, "check"];

/** Whether the user accepted the current consent text (ADR 0005). */
export function useConsent() {
  return useQuery({
    queryKey: ["consent"],
    queryFn: ({ signal }) => api<ConsentState>("/consent", { signal }),
  });
}

export function useGiveConsent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<ConsentState>("/consent", { method: "POST" }),
    onSuccess: (state) => client.setQueryData(["consent"], state),
  });
}

/** Withdrawing consent deletes every document of the user on the server. */
export function useWithdrawConsent() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("/consent", { method: "DELETE" }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["consent"] });
      void client.invalidateQueries({
        predicate: (query) =>
          query.queryKey[0] === "applications" &&
          (query.queryKey[2] === "documents" || query.queryKey[2] === "check"),
      });
    },
  });
}

export function useUploadDocument(applicationFileId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ requirementId, file }: { requirementId: string; file: File }) => {
      const form = new FormData();
      form.append("requirement_id", requirementId);
      form.append("file", file);
      return api<DocumentInfo>(`/applications/${applicationFileId}/documents`, {
        method: "POST",
        form,
      });
    },
    onSuccess: (document) => {
      client.setQueryData<DocumentInfo[]>(documentsKey(applicationFileId), (old) => [
        ...(old ?? []),
        document,
      ]);
      void client.invalidateQueries({ queryKey: checkKey(applicationFileId) });
    },
    onError: (error) => {
      // The consent was withdrawn elsewhere or its version changed: ask again.
      if (error instanceof ApiError && error.status === 403) {
        void client.invalidateQueries({ queryKey: ["consent"] });
      }
    },
  });
}

export function useDeleteDocument(applicationFileId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => api<void>(`/documents/${documentId}`, { method: "DELETE" }),
    onSuccess: (_, documentId) => {
      client.setQueryData<DocumentInfo[]>(documentsKey(applicationFileId), (old) =>
        old?.filter((document) => document.id !== documentId),
      );
      client.removeQueries({ queryKey: ["documents", documentId] });
      void client.invalidateQueries({ queryKey: checkKey(applicationFileId) });
    },
  });
}

/** The fields to enter for a document, with the values entered so far (FR-08). */
export function useDocumentFields(documentId: string, lang: Language) {
  return useQuery({
    queryKey: ["documents", documentId, "fields", lang],
    queryFn: ({ signal }) =>
      api<DocumentFields>(`/documents/${documentId}/fields?${new URLSearchParams({ lang })}`, {
        signal,
      }),
    // On a change of language the form stays (with the old titles) until the new ones arrive.
    placeholderData: (previous) => previous,
  });
}

export function useSaveDocumentFields(applicationFileId: string, documentId: string, lang: Language) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (values: Record<string, FieldValue>) =>
      api<DocumentFields>(`/documents/${documentId}/fields?${new URLSearchParams({ lang })}`, {
        method: "PUT",
        json: { values },
      }),
    onSuccess: (fields) => {
      client.setQueryData(["documents", documentId, "fields", lang], fields);
      void client.invalidateQueries({ queryKey: checkKey(applicationFileId) });
    },
  });
}

/** Missing documents and the result of every rule on the values entered so far (FR-09, FR-10). */
export function useCheck(applicationFileId: string, lang: Language) {
  return useQuery({
    queryKey: [...checkKey(applicationFileId), lang],
    queryFn: ({ signal }) =>
      api<CheckResult>(
        `/applications/${applicationFileId}/check?${new URLSearchParams({ lang })}`,
        { signal },
      ),
  });
}

/** What to know before applying to each pilot destination, with sources. */
export function useDestinations(lang: Language) {
  return useQuery({
    queryKey: ["destinations", lang],
    queryFn: ({ signal }) =>
      api<Destinations>(`/destinations?${new URLSearchParams({ lang })}`, { signal }),
    staleTime: 60 * 60_000,
  });
}

const runsKey = (applicationFileId: string) => ["applications", applicationFileId, "runs"];

/** The kept check runs of an application file, newest first. */
export function useCheckRuns(applicationFileId: string) {
  return useQuery({
    queryKey: runsKey(applicationFileId),
    queryFn: ({ signal }) =>
      api<CheckRun[]>(`/applications/${applicationFileId}/checks`, { signal }),
  });
}

export function useKeepCheck(applicationFileId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<CheckRun>(`/applications/${applicationFileId}/checks`, { method: "POST" }),
    onSuccess: (run) =>
      client.setQueryData<CheckRun[]>(runsKey(applicationFileId), (old) => [run, ...(old ?? [])]),
  });
}
