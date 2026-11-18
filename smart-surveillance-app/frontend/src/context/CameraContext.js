import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import api from '../services/api';
import { MessageContext } from './MessageContext';

const CameraContext = createContext();

export const CameraProvider = ({ children }) => {
  const [cameras, setCameras] = useState([]);
  const { showMessage } = useContext(MessageContext);

  const fetchCameras = useCallback(async () => {
    try {
      const res = await api.get("/cameras/");
      setCameras(res.data.data || res.data || []);
    } catch (err) {
      console.error("Error fetching cameras:", err);
      showMessage("error", "Failed to fetch cameras");
    }
  }, [showMessage]);

  useEffect(() => {
    fetchCameras();
  }, [fetchCameras]);

  const addCamera = useCallback(async (form) => {
    try {
      await api.post("/cameras/", { ...form, rtsp_url: form.stream_url });
      fetchCameras();
      showMessage("success", "Camera added successfully");
    } catch (err) {
      console.error("Error adding camera:", err);
      showMessage("error", "Failed to add camera");
    }
  }, [fetchCameras, showMessage]);

  const removeCamera = useCallback(async (id) => {
    try {
      await api.delete(`/cameras/${id}`);
      fetchCameras();
      showMessage("success", "Camera removed successfully");
    } catch (err) {
      console.error("Error deleting camera:", err);
      showMessage("error", "Failed to remove camera");
    }
  }, [fetchCameras, showMessage]);

  const updateCamera = useCallback(async (id, form) => {
    try {
      await api.put(`/cameras/${id}`, { ...form, rtsp_url: form.stream_url });
      fetchCameras();
      showMessage("success", "Camera updated successfully");
    } catch (err) {
      console.error("Error updating camera:", err);
      showMessage("error", "Failed to update camera");
    }
  }, [fetchCameras, showMessage]);

  return (
    <CameraContext.Provider value={{ cameras, setCameras, fetchCameras, addCamera, removeCamera, updateCamera }}>
      {children}
    </CameraContext.Provider>
  );
};

export const useCamera = () => useContext(CameraContext);
