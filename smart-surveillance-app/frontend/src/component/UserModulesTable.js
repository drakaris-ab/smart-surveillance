// src/components/UserModulesTable.js
import React from "react";
import "../styles/global.css";

function UserModulesTable({ modules, userModules, toggleModuleAccess }) {
  return (
    <table className="camera-table">
      <thead>
        <tr>
          <th>Module</th>
          <th>Enabled</th>
          <th>Access</th>
        </tr>
      </thead>
      <tbody>
        {modules.map((m, index) => (
          <tr
            key={m.id}
            className={`${index % 2 === 0 ? "row-even" : "row-odd"} ${
              userModules.includes(m.id) ? "has-access" : ""
            }`}
          >
            <td>{m.name}</td>
            <td>{m.enabled ? "Yes" : "No"}</td>
            <td>
              <button
                className={
                  userModules.includes(m.id)
                    ? "secondary-btn danger-btn"
                    : "primary-btn"
                }
                onClick={() => toggleModuleAccess(m.id)}
              >
                {userModules.includes(m.id) ? "Revoke" : "Grant"}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default UserModulesTable;
