import React, { createContext, useState, useCallback } from "react";
import { Snackbar, Alert } from "@mui/material";

export const MessageContext = createContext();

export function MessageProvider({ children }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [severity, setSeverity] = useState("info");

  const showMessage = useCallback((type, text) => {
    setSeverity(type); // "success" | "error" | "warning" | "info"
    setMessage(text);
    setOpen(true);
  }, []);

  const handleClose = (_, reason) => {
    if (reason === "clickaway") return;
    setOpen(false);
  };

  return (
    <MessageContext.Provider value={{ showMessage }}>
      {children}
      <Snackbar
        open={open}
        autoHideDuration={4000}
        onClose={handleClose}
        anchorOrigin={{ vertical: "top", horizontal: "right" }}
      >
        <Alert onClose={handleClose} severity={severity} sx={{ width: "100%" }}>
          {message}
        </Alert>
      </Snackbar>
    </MessageContext.Provider>
  );
}
