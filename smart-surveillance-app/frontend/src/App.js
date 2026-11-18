import React from "react";
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
} from "react-router-dom";
import { Provider } from "react-redux";
import store from "./store";

import Login from "./core/misc/Login";
import Dashboard from "./core/dashboard/Dashboard";
import CameraCard from "./core/camera/CameraCard";
import ZoneManagement from "./core/zone/ZoneManagement";
import AlertsDashboard from "./core/dashboard/AlertsDashboard";
import LogsDashboard from "./core/dashboard/LogsDashboard";
import UserManagement from "./core/user/UserManagement";
import ConfigureModules from "./core/config/ConfigureModules";
import UserModuleAccess from "./core/user/UserModuleAccess";
import FaceRecognition from "./modules/FaceRecognition/FaceRecognition";
import UnattendedObject from "./modules/UnattendedObject/UnattendedObject";
import SaftyCheck from "./modules/SaftyChecks/SaftyCheck";
import SuspiciousActivity from "./modules/SuspiciousActivity/SuspiciousActivity";

import AppLayout from "./layout/AppLayout";
import { MessageProvider } from "./context/MessageContext";
import { AuthProvider } from "./context/AuthContext";
import { ApiContext } from "./context/ApiContext";
import api from "./services/api";

// ✅ Proper ProtectedRoute component
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem("access_token");
  const username = localStorage.getItem("username");

  // Require both token and username
  if (token && username) {
    return children;
  }
  return <Navigate to="/login" replace />;
};

const router = createBrowserRouter([
  {
    path: "/login",
    element: <Login onLogin={() => {}} />,
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" /> }, // default redirect
      { path: "dashboard", element: <Dashboard /> },
      { path: "cameras", element: <CameraCard /> },
      { path: "zones", element: <ZoneManagement /> },
      { path: "alerts", element: <AlertsDashboard /> },
      { path: "activity-log", element: <LogsDashboard /> },
      { path: "users", element: <UserManagement /> },
      { path: "configure-modules", element: <ConfigureModules /> },
      { path: "face-recognition", element: <FaceRecognition /> },
      { path: "unidentified-object", element: <UnattendedObject /> },
      { path: "safety-check", element: <SaftyCheck /> },
      { path: "suspicious-activity", element: <SuspiciousActivity /> },
      { path: "module-access", element: <UserModuleAccess /> },
    ],
  },
]);

function App() {
  return (
    <Provider store={store}>
      <AuthProvider>
        <ApiContext.Provider value={api}>
          <MessageProvider>
            <RouterProvider router={router} />
          </MessageProvider>
        </ApiContext.Provider>
      </AuthProvider>
    </Provider>
  );
}

export default App;
