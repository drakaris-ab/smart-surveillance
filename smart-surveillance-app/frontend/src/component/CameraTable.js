// src/core/CameraTable.js
import React from "react";
import messages from "../constants/messages";
import "../styles/global.css";

function CameraTable({ cameras, editingId, setEditingId, saveCamera, deleteCamera, setCameras }) {
  return (
    <table className="camera-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>RTSP URL</th>
          <th>Location</th>
          <th>Created By</th>
          <th>Created At</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {Array.isArray(cameras) &&
          cameras.map((c, index) => (
            <tr key={c.id} className={index % 2 === 0 ? "row-even" : "row-odd"}>
              {editingId === c.id ? (
                <>
                  <td>
                    <input
                      className="input-field"
                      value={c.name}
                      onChange={(e) =>
                        setCameras(
                          cameras.map((cam) =>
                            cam.id === c.id ? { ...cam, name: e.target.value } : cam
                          )
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      className="input-field"
                      value={c.rtsp_url}
                      onChange={(e) =>
                        setCameras(
                          cameras.map((cam) =>
                            cam.id === c.id ? { ...cam, rtsp_url: e.target.value } : cam
                          )
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      className="input-field"
                      value={c.location || ""}
                      onChange={(e) =>
                        setCameras(
                          cameras.map((cam) =>
                            cam.id === c.id ? { ...cam, location: e.target.value } : cam
                          )
                        )
                      }
                    />
                  </td>
                  <td>{c.created_by}</td>
                  <td>{new Date(c.created_at).toLocaleString()}</td>
                  <td>
                    <div className="edit-actions">
                      <button className="primary-btn" onClick={() => saveCamera(c.id, c)}>
                        Save
                      </button>
                      <button className="secondary-btn" onClick={() => setEditingId(null)}>
                        Cancel
                      </button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td>{c.name}</td>
                  <td>{c.rtsp_url}</td>
                  <td>{c.location}</td>
                  <td>{c.created_by}</td>
                  <td>{new Date(c.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="icon-btn update-btn"
                      onClick={() => setEditingId(c.id)}
                      title="Update Camera"
                    >
                      ✏️
                    </button>
                    <button
                      className="icon-btn danger-btn"
                      onClick={() => {
                        if (window.confirm(messages.CAMERA_DELETE_CONFIRM)) {
                          deleteCamera(c.id);
                        }
                      }}
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
  );
}

export default CameraTable;
