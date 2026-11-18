// src/component/VisitorTrackingTable.js
import React from "react";
import "../styles/global.css";

function VisitorTrackingTable({ visitor, cameras, toggleAccess }) {
  return (
    <table className="camera-table">
      <thead>
        <tr>
          <th>Camera</th>
          <th>Location</th>
          <th>Access</th>
        </tr>
      </thead>
      <tbody>
        {cameras.map((cam, index) => {
          const hasAccess = visitor.cameras?.includes(cam.id);
          return (
            <tr
              key={cam.id}
              className={index % 2 === 0 ? "row-even" : "row-odd"}
            >
              <td>{cam.name}</td>
              <td>{cam.location}</td>
              <td>
                <button
                  className={hasAccess ? "secondary-btn danger-btn" : "primary-btn"}
                  onClick={() => toggleAccess(cam.id)}
                >
                  {hasAccess ? "Revoke" : "Grant"}
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default VisitorTrackingTable;
