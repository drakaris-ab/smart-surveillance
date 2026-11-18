import { useState, useEffect } from "react";
import api from "../services/api";

export default function useAlerts(pollInterval = 5000) {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await api.get("/alerts/");
        const data = res.data.data || res.data;
        if (Array.isArray(data)) {
          setAlerts(data);
        }
      } catch (err) {
        console.error("Error fetching alerts:", err);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, pollInterval);
    return () => clearInterval(interval);
  }, [pollInterval]);

  return { alerts, setAlerts };
}
