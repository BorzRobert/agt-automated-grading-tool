import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { TutorialPage } from "./components/TutorialPage";
import { UploadForm } from "./components/UploadForm";
import "./App.css";

const App: React.FC = () => {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<UploadForm />} />
        <Route path="/guide" element={<TutorialPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  );
};

export default App;
