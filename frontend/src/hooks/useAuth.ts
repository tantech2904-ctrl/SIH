// Backwards-compatible re-export. The real state lives in AuthContext so
// that every component sees the same user object.
export { useAuthContext as useAuth } from "@/context/AuthContext";