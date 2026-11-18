// src/core/ZoneTable.js
import React from "react";
import messages from "../constants/messages";
import "../styles/global.css";

function ZoneTable({ zones, editingId, setEditingId, saveZone, deleteZone, setZones }) {
  return (
    <table className="camera-table">
      <thead>
        <tr>
          <th>Camera</th>
          <th>Polygon Coords</th>
          <th>Sensitivity</th>
          <th>Snapshot</th>
          <th>Created By</th>
          <th>Created At</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {Array.isArray(zones) &&
          zones.map((z, index) => (
            <tr key={z.id} className={index % 2 === 0 ? "row-even" : "row-odd"}>
              {editingId === z.id ? (
                <>
                  <td>{z.camera_id}</td>
                  <td>
                    <input
                      className="input-field"
                      value={z.polygon_coords}
                      onChange={(e) =>
                        setZones(
                          zones.map((zone) =>
                            zone.id === z.id
                              ? { ...zone, polygon_coords: e.target.value }
                              : zone
                          )
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      className="input-field"
                      value={z.sensitivity || ""}
                      onChange={(e) =>
                        setZones(
                          zones.map((zone) =>
                            zone.id === z.id
                              ? { ...zone, sensitivity: e.target.value }
                              : zone
                          )
                        )
                      }
                    />
                  </td>
                  <td>{z.snapshot_file || messages.NO_SNAPSHOT}</td>
                  <td>{z.created_by}</td>
                  <td>{new Date(z.created_at).toLocaleString()}</td>
                  <td>
                    <div className="edit-actions">
                      <button
                        className="primary-btn"
                        onClick={() => saveZone(z.id, z)}
                      >
                        Save
                      </button>
                      <button
                        className="secondary-btn"
                        onClick={() => setEditingId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td>{z.camera_id}</td>
                  <td className="coords-cell">{z.polygon_coords}</td>
                  <td>{z.sensitivity}</td>
                  <td>{z.snapshot_file || messages.NO_SNAPSHOT}</td>
                  <td>{z.created_by}</td>
                  <td>{new Date(z.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="icon-btn update-btn"
                      onClick={() => setEditingId(z.id)}
                      title={messages.UPDATE_ZONE_TITLE}
                    >
                      ✏️
                    </button>
                    <button
                      className="icon-btn danger-btn"
                      onClick={() => {
                        if (window.confirm(messages.ZONE_DELETE_CONFIRM)) {
                          deleteZone(z.id);
                        }
                      }}
                      title={messages.DELETE_ZONE_TITLE}
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
  );
}

export default ZoneTable;
