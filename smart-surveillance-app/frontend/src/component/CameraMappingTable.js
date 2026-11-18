// src/components/CameraMappingTable.js
import React from "react";
import "../styles/global.css";

function CameraMappingTable({ cameras, selectedCamera, handleCameraAssign, handleCameraDelete }) {
  return (
    <table className="camera-table">
      <thead>
        <tr>
          <th>Camera</th>
          <th>Location</th>
          <th>Assigned</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {cameras.map((cam, index) => (
          <tr
            key={cam.id}
            className={`${index % 2 === 0 ? "row-even" : "row-odd"} ${
              selectedCamera?.id === cam.id ? "has-access" : ""
            }`}
          >
            <td>{cam.name}</td>
            <td>{cam.location}</td>
            <td>{selectedCamera?.id === cam.id ? "Yes" : "No"}</td>
            <td>
              {selectedCamera?.id === cam.id ? (
                <button
                  className="secondary-btn danger-btn"
                  onClick={() => handleCameraDelete(cam.id)}
                >
                  Remove
                </button>
              ) : (
                <button
                  className="primary-btn"
                  onClick={() => handleCameraAssign(cam.id)}
                >
                  Assign
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default CameraMappingTable;
