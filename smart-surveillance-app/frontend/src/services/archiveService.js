import apiClient from './apiClient';

/**
 * ArchiveService provides helpers for managing archived footage/snapshots.
 * All calls flow through apiClient for consistency and token handling.
 */

// Fetch all archives
export const fetchArchives = async () => {
  return await apiClient.get('/archives');
};

// Fetch archives by camera ID
export const fetchArchivesByCamera = async (cameraId) => {
  return await apiClient.get(`/archives/camera/${cameraId}`);
};

// Save a new snapshot/archive
export const saveArchive = async (archiveData) => {
  // archiveData could include { cameraId, timestamp, snapshotBase64 }
  return await apiClient.post('/archives', archiveData);
};

// Delete an archive by ID
export const deleteArchive = async (id) => {
  return await apiClient.delete(`/archives/${id}`);
};

// Bulk delete archives (optional)
export const clearArchives = async () => {
  return await apiClient.delete('/archives');
};
