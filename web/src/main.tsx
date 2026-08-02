import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import "@/styles/global.css";
import App from "@/App.tsx";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { ThemeProvider } from "@/lib/theme/ThemeContext";
import { WSProvider } from "@/lib/ws/WSContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <WSProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </WSProvider>
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>
);
