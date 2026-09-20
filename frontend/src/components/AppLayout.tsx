import React from "react";
import { NavLink } from "react-router-dom";

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-wrap">
          <span className="brand-mark">AGT</span>
          <span className="brand-text">Automated Grading Tool</span>
        </div>

        <nav className="main-nav" aria-label="Main navigation">
          <NavLink to="/" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Upload Form
          </NavLink>
          <NavLink to="/guide" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            How to Use
          </NavLink>
        </nav>
      </header>

      <main className="page-shell">{children}</main>
    </div>
  );
};
