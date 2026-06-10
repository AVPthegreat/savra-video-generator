import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

import LandingPage from "./components/LandingPage.tsx";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import Dashboard from "./components/Dashboard.tsx"; // Will refactor later
import AdminPanel from "./pages/AdminPanel"; // Will create next

function App() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // NOTE: Do NOT block rendering here on `loading`.
  // The landing page is public and must render immediately.
  // ProtectedRoute handles the loading state for auth-gated pages.

  return (
    <div className="dark min-h-screen bg-black">
      <Routes>
        <Route path="/" element={<LandingPage onGetStarted={() => navigate("/dashboard")} />} />
        <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <LoginPage />} />
        <Route path="/signup" element={user ? <Navigate to="/dashboard" /> : <SignupPage />} />
        
        {/* Protected User Dashboard */}
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              {user?.is_beta_authorized ? (
                <Dashboard token="cookie" onLogout={logout} />
              ) : (
                <Navigate to="/pending" />
              )}
            </ProtectedRoute>
          } 
        />

        {/* Waitlist Pending View */}
        <Route 
          path="/pending" 
          element={
            <ProtectedRoute>
              <div className="min-h-screen flex items-center justify-center text-white px-4">
                <div className="text-center">
                  <h1 className="text-4xl font-bold mb-4">Account Pending</h1>
                  <p className="text-zinc-400">Your account is on the beta waitlist. An admin needs to approve your access.</p>
                  <button onClick={logout} className="mt-8 text-zinc-500 hover:text-white underline">Logout</button>
                </div>
              </div>
            </ProtectedRoute>
          }
        />

        {/* Protected Admin Panel */}
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute adminOnly>
              <AdminPanel />
            </ProtectedRoute>
          } 
        />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </div>
  );
}

export default App;
