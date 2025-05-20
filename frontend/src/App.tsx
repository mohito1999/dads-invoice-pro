// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import MainLayout from "./components/layout/MainLayout";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import OrganizationsPage from "./pages/OrganizationsPage";
import NotFoundPage from "./pages/NotFoundPage";
import CustomersPage from "./pages/CustomersPage";
import ItemsPage from "./pages/ItemsPage";
import InvoicesPage from "./pages/InvoicesPage";
import InvoiceEditorPage from "./pages/InvoiceEditorPage";
import { useAuth } from "./contexts/AuthContext"; // Import useAuth

// Updated ProtectedRoute to use AuthContext
const ProtectedRoute = ({ children }: { children: JSX.Element }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    // Optional: Show a loading spinner or skeleton screen
    return <div className="flex justify-center items-center min-h-screen">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
};

function App() {
  const { isLoading } = useAuth(); // Get isLoading state for initial load

  if (isLoading) {
     // Prevents flicker of login page before auth state is determined
     return <div className="flex justify-center items-center min-h-screen">App Loading...</div>;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<HomePage />} /> 
          <Route path="organizations" element={<OrganizationsPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="items" element={<ItemsPage />} />
          <Route path="invoices" element={<InvoicesPage />} />
          <Route path="invoices/new" element={<InvoiceEditorPage />} />
          <Route path="invoices/edit/:invoiceId" element={<InvoiceEditorPage />} />
          <Route path="invoices/view/:invoiceId" element={<InvoiceEditorPage />} /> 
        </Route>

        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;