import React, { useState, useEffect, useContext } from "react";
import api from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import messages from "../../constants/messages";
import UserTable from "../../component/UserTable";   // ✅ import table
import "../../styles/global.css";

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("Monitor");
  const [editingId, setEditingId] = useState(null);
  const { showMessage } = useContext(MessageContext);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const res = await api.get("/users");
      setUsers(res.data.data || []);
      showMessage("success", messages.USER_FETCH_SUCCESS);
    } catch {
      showMessage("error", messages.USER_FETCH_FAIL);
      setUsers([]);
    }
  };

  const addUser = async () => {
    if (!username.trim() || !password.trim() || !role.trim()) {
      showMessage("error", messages.MANDATORY_USER_FIELDS);
      return;
    }
    try {
      await api.post("/users", { username, password, role });
      showMessage("success", messages.USER_ADD_SUCCESS);
      setUsername("");
      setPassword("");
      setRole("Monitor");
      loadUsers();
    } catch {
      showMessage("error", messages.USER_ADD_FAIL);
    }
  };

  const saveUser = async (id, updated) => {
    if (!updated.username || !updated.role) {
      showMessage("error", messages.MANDATORY_USER_FIELDS);
      return;
    }
    try {
      await api.put(`/users/${id}`, updated);
      showMessage("success", messages.USER_UPDATE_SUCCESS);
      setEditingId(null);
      loadUsers();
    } catch {
      showMessage("error", messages.USER_UPDATE_FAIL);
    }
  };

  const deleteUser = async (id) => {
    try {
      await api.delete(`/users/${id}`);
      showMessage("success", messages.USER_DELETE_SUCCESS);
      setUsers(users.filter((u) => u.id !== id));
    } catch {
      showMessage("error", messages.USER_DELETE_FAIL);
    }
  };

  return (
    <div className="round-card">
     
      {/* Add User Form */}
      <div className="form-container">
        <input
          className="input-field half-width"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          className="input-field half-width"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <select
          className="input-field half-width"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        >
          <option value="Admin">Admin</option>
          <option value="Monitor">Monitor</option>
        </select>
      </div>
      <div className="form-container">
        <button className="primary-btn full-width" onClick={addUser}>
          + Add User
        </button>
      </div>

      {/* Users Table */}
      <UserTable
        users={users}
        editingId={editingId}
        setEditingId={setEditingId}
        saveUser={saveUser}
        deleteUser={deleteUser}
        setUsers={setUsers}
      />
    </div>
  );
}

export default UserManagement;
