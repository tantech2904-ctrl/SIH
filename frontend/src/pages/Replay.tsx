import { Navigate } from "react-router-dom";

// Replay is exposed via Event Detail and Quarantine pages. This route
// redirects to the Quarantine center which handles the common case.
export default function Replay() {
  return <Navigate to="/quarantine" replace />;
}