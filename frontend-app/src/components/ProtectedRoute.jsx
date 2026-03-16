import { Navigate, useLocation } from "react-router-dom";

// Guards application pages until a user has signed in.
export function ProtectedRoute({ children, isReady, isAuthenticated }) {
  const location = useLocation();

  if (!isReady) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}
