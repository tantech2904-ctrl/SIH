import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import LiveStream from "@/pages/LiveStream";
import EventExplorer from "@/pages/EventExplorer";
import EventDetail from "@/pages/EventDetail";
import Ingest from "@/pages/Ingest";
import FormatDetection from "@/pages/FormatDetection";
import UnknownAnalyzer from "@/pages/UnknownAnalyzer";
import Parsers from "@/pages/Parsers";
import SchemaExplorer from "@/pages/SchemaExplorer";
import Mappings from "@/pages/Mappings";
import SchemaDrift from "@/pages/SchemaDrift";
import Quarantine from "@/pages/Quarantine";
import Replay from "@/pages/Replay";
import ThreatIntel from "@/pages/ThreatIntel";
import GeoIP from "@/pages/GeoIP";
import ATTACK from "@/pages/ATTACK";
import Rules from "@/pages/Rules";
import Alerts from "@/pages/Alerts";
import Incidents from "@/pages/Incidents";
import AuditLogs from "@/pages/AuditLogs";
import Evidence from "@/pages/Evidence";
import TestLab from "@/pages/TestLab";
import Reports from "@/pages/Reports";
import Health from "@/pages/Health";
import Settings from "@/pages/Settings";

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
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/live" element={<LiveStream />} />
        <Route path="/events" element={<EventExplorer />} />
        <Route path="/events/:id" element={<EventDetail />} />
        <Route path="/ingest" element={<Ingest />} />
        <Route path="/format" element={<FormatDetection />} />
        <Route path="/unknown" element={<UnknownAnalyzer />} />
        <Route path="/parsers" element={<Parsers />} />
        <Route path="/schema" element={<SchemaExplorer />} />
        <Route path="/mappings" element={<Mappings />} />
        <Route path="/drift" element={<SchemaDrift />} />
        <Route path="/quarantine" element={<Quarantine />} />
        <Route path="/replay" element={<Replay />} />
        <Route path="/threat-intel" element={<ThreatIntel />} />
        <Route path="/geoip" element={<GeoIP />} />
        <Route path="/attck" element={<ATTACK />} />
        <Route path="/rules" element={<Rules />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/audit" element={<AuditLogs />} />
        <Route path="/evidence" element={<Evidence />} />
        <Route path="/testlab" element={<TestLab />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/health" element={<Health />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}