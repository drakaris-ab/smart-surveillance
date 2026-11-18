import React, { useState } from "react";
import "../styles/global.css";

export default function ZonesTable({ zones, onEdit, onDelete, saveZone }) {
  const [sortConfig, setSortConfig] = useState({ key: "id", direction: "asc" });
  const [currentPage, setCurrentPage] = useState(1);
  const [editingId, setEditingId] = useState(null);
  const [editedZone, setEditedZone] = useState(null);
  const rowsPerPage = 10;

  // Sorting
  const sortedZones = [...zones].sort((a, b) => {
    if (!sortConfig.key) return 0;
    const valA = a[sortConfig.key] || "";
    const valB = b[sortConfig.key] || "";
    if (valA < valB) return sortConfig.direction === "asc" ? -1 : 1;
    if (valA > valB) return sortConfig.direction === "asc" ? 1 : -1;
    return 0;
  });

  // Pagination
  const totalPages = Math.ceil(sortedZones.length / rowsPerPage);
  const paginatedZones = sortedZones.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  const requestSort = (key) => {
    let direction = "asc";
    if (sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });
  };

  const handleEditClick = (zone) => {
    setEditingId(zone.id);
    setEditedZone({ ...zone });
    onEdit(zone); // keep parent state in sync
  };

  const handleSaveClick = () => {
    if (editedZone && editedZone.id) {
      saveZone(editedZone.id, editedZone); // ✅ always passes integer id
      setEditingId(null);
      setEditedZone(null);
    }
  };

  const handleCancelClick = () => {
    setEditingId(null);
    setEditedZone(null);
  };

  return (
    <div className="table-container">
      <table className="camera-table">
        <thead>
          <tr>
            {["id", "camera_id", "polygon_coords"].map((col) => (
              <th key={col} onClick={() => requestSort(col)} className="sortable">
                {col.replace("_", " ").toUpperCase()}
                {sortConfig.key === col && (sortConfig.direction === "asc" ? " ▲" : " ▼")}
              </th>
            ))}
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {paginatedZones.map((zone, idx) => (
            <tr key={zone.id} className={idx % 2 === 0 ? "row-even" : "row-odd"}>
              <td>{zone.id}</td>
              <td>{zone.camera_id}</td>
              <td className="coords-cell">
                {editingId === zone.id ? (
                  <input
                    className="input-field"
                    value={editedZone?.polygon_coords || ""}
                    onChange={(e) =>
                      setEditedZone({ ...editedZone, polygon_coords: e.target.value })
                    }
                  />
                ) : (
                  zone.polygon_coords
                )}
              </td>
              <td>
                {editingId === zone.id ? (
                  <>
                    <button
                      onClick={handleSaveClick}
                      className="primary-btn"
                      title="Save Zone"
                    >
                      💾 Save
                    </button>
                    <button
                      onClick={handleCancelClick}
                      className="secondary-btn"
                      title="Cancel Edit"
                    >
                      ❌ Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => handleEditClick(zone)}
                      className="icon-btn update-btn"
                      title="Edit Zone"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => {
                        if (typeof onDelete === "function") {
                          onDelete(zone.id);
                        } else {
                          console.error("onDelete prop is not a function");
                        }
                      }}
                      className="icon-btn danger-btn"
                      title="Delete Zone"
                    >
                      🗑️
                    </button>
                  </>
                )}
              </td>
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
          <span className="page-info">Page {currentPage} of {totalPages}</span>
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
