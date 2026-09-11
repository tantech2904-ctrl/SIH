import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { Page } from "@/types";

export function useDashboard() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => api.dashboard() });
}

export function useEvents(params: Record<string, any>) {
  return useQuery({
    queryKey: ["events", params],
    queryFn: () => api.listEvents(params),
    placeholderData: (prev) => prev,
  });
}

export function useEvent(id: string | undefined) {
  return useQuery({
    queryKey: ["event", id],
    queryFn: () => api.getEvent(id!),
    enabled: !!id,
  });
}

export function useEventRaw(id: string | undefined) {
  return useQuery({
    queryKey: ["event-raw", id],
    queryFn: () => api.getRaw(id!),
    enabled: !!id,
  });
}

export function useEventTimeline(id: string | undefined) {
  return useQuery({
    queryKey: ["event-timeline", id],
    queryFn: () => api.getTimeline(id!),
    enabled: !!id,
  });
}

export function useEventIntegrity(id: string | undefined, enabled = false) {
  return useQuery({
    queryKey: ["event-integrity", id],
    queryFn: () => api.getIntegrity(id!),
    enabled: !!id && enabled,
  });
}

export function useEventEnrichment(id: string | undefined) {
  return useQuery({
    queryKey: ["event-enrichment", id],
    queryFn: () => api.getEnrichment(id!),
    enabled: !!id,
  });
}

export function useEventReplay(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (parserId?: string) => api.replay(id!, parserId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["event", id] });
      qc.invalidateQueries({ queryKey: ["event-timeline", id] });
    },
  });
}

export function useQuarantine(params: Record<string, any>) {
  return useQuery({
    queryKey: ["quarantine", params],
    queryFn: () => api.listQuarantine(params),
    placeholderData: (prev: Page<any> | undefined) => prev,
  });
}

export function useParsers() {
  return useQuery({ queryKey: ["parsers"], queryFn: () => api.listParsers() });
}

export function useProviders() {
  return useQuery({ queryKey: ["providers"], queryFn: () => api.providersStatus() });
}

export function useAlerts(params: Record<string, any>) {
  return useQuery({ queryKey: ["alerts", params], queryFn: () => api.listAlerts(params) });
}

export function useIncidents(params: Record<string, any>) {
  return useQuery({ queryKey: ["incidents", params], queryFn: () => api.listIncidents(params) });
}

export function useAudit(params: Record<string, any>) {
  return useQuery({ queryKey: ["audit", params], queryFn: () => api.listAudit(params) });
}

export function useDrift() {
  return useQuery({ queryKey: ["drift"], queryFn: () => api.listDrift() });
}

export function useMappings(parserId?: string) {
  return useQuery({
    queryKey: ["mappings", parserId],
    queryFn: () => api.listMappings(parserId),
  });
}

export function useCSESchema() {
  return useQuery({ queryKey: ["cse-schema"], queryFn: () => api.cseSchema() });
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.ready(),
    refetchInterval: 10_000,
  });
}

export function useTestLabScenarios() {
  return useQuery({ queryKey: ["testlab-scenarios"], queryFn: () => api.testlabScenarios() });
}