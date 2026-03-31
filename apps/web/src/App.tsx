import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { OrdersPage } from "./pages/OrdersPage";
import { PositionsPage } from "./pages/PositionsPage";
import { RiskPage } from "./pages/RiskPage";
import { SignalsPage } from "./pages/SignalsPage";
import { SystemHealthPage } from "./pages/SystemHealthPage";

export function App() {
  return (
    <BrowserRouter>
      <main className="container">
        <header className="page-header">
          <h1>KnoweTrade</h1>
          <p>Frontend is API-only. Broker access is backend worker only.</p>
        </header>

        <nav className="tabs" aria-label="Primary">
          <NavLink className={({ isActive }) => (isActive ? "tab active" : "tab")} to="/">
            Dashboard
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? "tab active" : "tab")} to="/positions">
            Positions
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? "tab active" : "tab")} to="/orders">
            Orders
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? "tab active" : "tab")} to="/signals">
            Signals
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? "tab active" : "tab")} to="/risk">
            Risk
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? "tab active" : "tab")} to="/system-health">
            System Health
          </NavLink>
        </nav>

        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/risk" element={<RiskPage />} />
          <Route path="/system-health" element={<SystemHealthPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
