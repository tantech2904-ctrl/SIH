import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import EventDetail from "@/pages/EventDetail";

import Dashboard from "@/pages/Dashboard";
import TelemetryWorkspace from "@/pages/workspaces/TelemetryWorkspace";
import DiscoveryWorkspace from "@/pages/workspaces/DiscoveryWorkspace";
import PipelineWorkspace from "@/pages/workspaces/PipelineWorkspace";
import DetectionWorkspace from "@/pages/workspaces/DetectionWorkspace";
import EvidenceWorkspace from "@/pages/workspaces/EvidenceWorkspace";
import PlatformWorkspace from "@/pages/workspaces/PlatformWorkspace";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* 1. SOC Command Center */}
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/operations" element={<Dashboard />} />

        {/* 2. Live Telemetry & Connectors Hub */}
        <Route path="/telemetry" element={<TelemetryWorkspace defaultTab="live" />} />
        <Route path="/live" element={<TelemetryWorkspace defaultTab="live" />} />
        <Route path="/connectors" element={<TelemetryWorkspace defaultTab="connectors" />} />

        {/* 3. Log Discovery & Ingestion */}
        <Route path="/discovery" element={<DiscoveryWorkspace defaultTab="explorer" />} />
        <Route path="/events" element={<DiscoveryWorkspace defaultTab="explorer" />} />
        <Route path="/ingest" element={<DiscoveryWorkspace defaultTab="ingest" />} />
        <Route path="/format" element={<DiscoveryWorkspace defaultTab="format" />} />

        {/* Event Detail Drill-down */}
        <Route path="/events/:id" element={<EventDetail />} />

        {/* 4. Log Pipeline & Schema Normalization */}
        <Route path="/pipeline" element={<PipelineWorkspace defaultTab="parsers" />} />
        <Route path="/parsers" element={<PipelineWorkspace defaultTab="parsers" />} />
        <Route path="/schema" element={<PipelineWorkspace defaultTab="schema" />} />
        <Route path="/drift" element={<PipelineWorkspace defaultTab="drift" />} />
        <Route path="/quarantine" element={<PipelineWorkspace defaultTab="quarantine" />} />
        <Route path="/replay" element={<PipelineWorkspace defaultTab="quarantine" />} />
        <Route path="/unknown" element={<PipelineWorkspace defaultTab="unknown" />} />

        {/* 5. Threat Detection & Intel */}
        <Route path="/detection" element={<DetectionWorkspace defaultTab="alerts" />} />
        <Route path="/alerts" element={<DetectionWorkspace defaultTab="alerts" />} />
        <Route path="/incidents" element={<DetectionWorkspace defaultTab="incidents" />} />
        <Route path="/rules" element={<DetectionWorkspace defaultTab="rules" />} />
        <Route path="/attck" element={<DetectionWorkspace defaultTab="attck" />} />
        <Route path="/threat-intel" element={<DetectionWorkspace defaultTab="threat-intel" />} />
        <Route path="/geoip" element={<DetectionWorkspace defaultTab="geoip" />} />

        {/* 6. Forensic Evidence & Audit */}
        <Route path="/evidence" element={<EvidenceWorkspace defaultTab="evidence" />} />
        <Route path="/audit" element={<EvidenceWorkspace defaultTab="audit" />} />
        <Route path="/reports" element={<EvidenceWorkspace defaultTab="reports" />} />

        {/* 7. Platform Admin & Test Lab */}
        <Route path="/platform" element={<PlatformWorkspace defaultTab="testlab" />} />
        <Route path="/testlab" element={<PlatformWorkspace defaultTab="testlab" />} />
        <Route path="/health" element={<PlatformWorkspace defaultTab="health" />} />
        <Route path="/settings" element={<PlatformWorkspace defaultTab="settings" />} />

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}