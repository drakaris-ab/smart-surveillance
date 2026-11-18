import React, { useState } from "react";
import messages from "../constants/messages";
import "../styles/global.css";

function UserTable({ users, editingId, setEditingId, saveUser, deleteUser, setUsers }) {
  const [sortConfig, setSortConfig] = useState({ key: "username", direction: "asc" });
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  // Sorting logic
  const sortedUsers = [...users].sort((a, b) => {
    if (!sortConfig.key) return 0;
    const valA = a[sortConfig.key];
    const valB = b[sortConfig.key];
    if (valA < valB) return sortConfig.direction === "asc" ? -1 : 1;
    if (valA > valB) return sortConfig.direction === "asc" ? 1 : -1;
    return 0;
  });

  // Pagination logic
  const totalPages = Math.ceil(sortedUsers.length / rowsPerPage);
  const paginatedUsers = sortedUsers.slice(
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

  return (
    <div className="table-container">
      <table className="camera-table bordered">
        <thead>
          <tr>
            {["username", "role", "created_by", "created_at"].map((col) => (
              <th key={col} onClick={() => requestSort(col)} className="sortable">
                {col.replace("_", " ").toUpperCase()}
                {sortConfig.key === col && (sortConfig.direction === "asc" ? " ▲" : " ▼")}
              </th>
            ))}
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          {Array.isArray(paginatedUsers) &&
            paginatedUsers.map((u, index) => (
              <tr key={u.id} className={index % 2 === 0 ? "row-even" : "row-odd"}>
                {editingId === u.id ? (
                  <>
                    <td>
                      <input
                        className="input-field"
                        value={u.username}
                        onChange={(e) =>
                          setUsers(users.map((usr) =>
                            usr.id === u.id ? { ...usr, username: e.target.value } : usr
                          ))
                        }
                      />
                    </td>
                    <td>
                      <select
                        className="input-field"
                        value={u.role}
                        onChange={(e) =>
                          setUsers(users.map((usr) =>
                            usr.id === u.id ? { ...usr, role: e.target.value } : usr
                          ))
                        }
                      >
                        <option value="Admin">Admin</option>
                        <option value="Monitor">Monitor</option>
                      </select>
                    </td>
                    <td>{u.created_by}</td>
                    <td>{new Date(u.created_at).toLocaleString()}</td>
                    <td>
                      <div className="edit-actions">
                        <button className="primary-btn success-btn" onClick={() => saveUser(u.id, u)}>Save</button>
                        <button className="secondary-btn cancel-btn" onClick={() => setEditingId(null)}>Cancel</button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td>{u.username}</td>
                    <td>{u.role}</td>
                    <td>{u.created_by}</td>
                    <td>{new Date(u.created_at).toLocaleString()}</td>
                    <td>
                      <button className="icon-btn update-btn" onClick={() => setEditingId(u.id)} title="Update User">✏️</button>
                      <button
                        className="icon-btn danger-btn"
                        onClick={() => {
                          if (window.confirm(messages.USER_DELETE_CONFIRM)) {
                            deleteUser(u.id);
                          }
                        }}
                        title="Delete User"
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

      {/* Pagination Controls */}
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

export default UserTable;
