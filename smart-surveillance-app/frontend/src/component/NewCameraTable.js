// src/components/NewCameraTable.js
import React, { useState } from "react";
import api from "../services/api";   // ✅ axios instance
import "../styles/global.css";

export default function NewCameraTable({ cameras = [], setCameras }) {
  const [editingId, setEditingId] = useState(null);
  const [sortConfig, setSortConfig] = useState({ key: "name", direction: "asc" });
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;
  const [editForm, setEditForm] = useState({ name: "", location: "", rtsp_url: "" });

  // --- API Calls ---
  const saveCamera = async (id, data) => {
    try {
      const res = await api.put(`/cameras/${id}`, data);
      const updated = res.data?.data;

      if (updated?.id) {
        setCameras((prev) =>
          prev.map((c) => (c.id === id ? updated : c))
        );
      }

      setEditingId(null);
      setEditForm({ name: "", location: "", rtsp_url: "" });
    } catch (err) {
      console.error("Update failed:", err);
    }
  };

  const removeCamera = async (id) => {
    try {
      const res = await api.delete(`/cameras/${id}`);
      const deleted = res.data?.data;

      if (deleted?.id) {
        setCameras((prev) => prev.filter((c) => c.id !== deleted.id));
      } else {
        // fallback if backend only returns id
        setCameras((prev) => prev.filter((c) => c.id !== id));
      }
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  // --- Sorting ---
  const sortedCameras = [...(cameras || [])].sort((a, b) => {
    if (!sortConfig.key) return 0;
    const valA = a?.[sortConfig.key] || "";
    const valB = b?.[sortConfig.key] || "";
    if (valA < valB) return sortConfig.direction === "asc" ? -1 : 1;
    if (valA > valB) return sortConfig.direction === "asc" ? 1 : -1;
    return 0;
  });

  // --- Pagination ---
  const totalPages = Math.ceil(sortedCameras.length / rowsPerPage);
  const paginatedCameras = sortedCameras.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  // --- Edit Handlers ---
  const startEdit = (cam) => {
    if (!cam?.id) return;
    setEditingId(cam.id);
    setEditForm({
      name: cam.name || "",
      location: cam.location || "",
      rtsp_url: cam.rtsp_url || "",
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm({ name: "", location: "", rtsp_url: "" });
  };

  const handleSave = async (id) => {
    await saveCamera(id, editForm);  // ✅ wait for backend update
  };

  return (
    <div className="table-container">
      <table className="camera-table bordered">
        <thead>
          <tr>
            {["name", "location", "rtsp_url"].map((col) => (
              <th
                key={col}
                onClick={() =>
                  setSortConfig({
                    key: col,
                    direction: sortConfig.direction === "asc" ? "desc" : "asc",
                  })
                }
                className="sortable"
              >
                {col.replace("_", " ").toUpperCase()}
                {sortConfig.key === col &&
                  (sortConfig.direction === "asc" ? " ▲" : " ▼")}
              </th>
            ))}
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {paginatedCameras.map((cam, index) => (
            <tr key={cam?.id || index} className={index % 2 === 0 ? "row-even" : "row-odd"}>
              {editingId === cam?.id ? (
                <>
                  <td>
                    <input
                      className="input-field"
                      value={editForm.name}
                      onChange={(e) =>
                        setEditForm({ ...editForm, name: e.target.value })
                      }
                    />
                  </td>
                  <td>
                    <input
                      className="input-field"
                      value={editForm.location}
                      onChange={(e) =>
                        setEditForm({ ...editForm, location: e.target.value })
                      }
                    />
                  </td>
                  <td>
                    <input
                      className="input-field wide"
                      value={editForm.rtsp_url}
                      onChange={(e) =>
                        setEditForm({ ...editForm, rtsp_url: e.target.value })
                      }
                    />
                  </td>
                  <td>
                    <button
                      className="primary-btn success-btn"
                      onClick={() => handleSave(cam.id)}
                    >
                      Save
                    </button>
                    <button
                      className="secondary-btn cancel-btn"
                      onClick={cancelEdit}
                    >
                      Cancel
                    </button>
                  </td>
                </>
              ) : (
                <>
                  <td>{cam?.name || "N/A"}</td>
                  <td>{cam?.location || "N/A"}</td>
                  <td>{cam?.rtsp_url || "N/A"}</td>
                  <td>
                    <button
                      className="icon-btn update-btn"
                      onClick={() => startEdit(cam)}
                      title="Update Camera"
                    >
                      ✏️
                    </button>
                    <button
                      className="icon-btn danger-btn"
                      onClick={() => removeCamera(cam.id)}
                      title="Delete Camera"
                    >
                      🗑️
                    </button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="secondary-btn"
            onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            disabled={currentPage === 1}
          >
            ◀ Prev
          </button>
          <span className="page-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="secondary-btn"
            onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            disabled={currentPage === totalPages}
          >
            Next ▶
          </button>
        </div>
      )}
    </div>
  );
}
