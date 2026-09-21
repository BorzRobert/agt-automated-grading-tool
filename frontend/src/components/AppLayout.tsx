import React from "react";
import { Link, NavLink } from "react-router-dom";

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand-link" aria-label="Go to the main page">
          <div className="brand-wrap">
            <span className="brand-mark">AGT</span>
            <span className="brand-text">Automated Grading Tool</span>
          </div>
        </Link>

        <nav className="main-nav" aria-label="Main navigation">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Upload Form
          </NavLink>
          <NavLink to="/template" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            Blank Template
          </NavLink>
          <NavLink to="/guide" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            How to Use
          </NavLink>
        </nav>
      </header>

      <div className="page-scroll">
        <main className="page-shell">{children}</main>
      </div>
    </div>
  );
};
