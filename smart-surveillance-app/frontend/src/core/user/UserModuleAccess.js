// src/components/UserModuleAccess.js
import React, { useState, useEffect, useContext } from "react";
import api from "../../services/api";
import { MessageContext } from "../../context/MessageContext";
import messages from "../../constants/messages";
import UserModulesTable from "../../component/UserModulesTable";   // import new table
import "../../styles/global.css";

function UserModuleAccess() {
  const [users, setUsers] = useState([]);
  const [modules, setModules] = useState([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [userModules, setUserModules] = useState([]); // store IDs only
  const { showMessage } = useContext(MessageContext);

  useEffect(() => {
    loadUsers();
    loadModules();
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

  const loadModules = async () => {
    try {
      const res = await api.get("/modules");
      setModules(res.data.data || []);
      showMessage("success", messages.MODULE_FETCH_SUCCESS);
    } catch {
      showMessage("error", messages.MODULE_FETCH_FAIL);
      setModules([]);
    }
  };

  const loadUserModules = async (userId) => {
    try {
      const res = await api.get(`/users/${userId}/modules`);
      const moduleIds = (res.data.data || []).map((m) => m.id);
      setUserModules(moduleIds);
    } catch {
      showMessage("error", "Failed to load user module access");
      setUserModules([]);
    }
  };

  const handleUserChange = (e) => {
    const userId = e.target.value;
    setSelectedUser(userId);
    if (userId) loadUserModules(userId);
  };

  const toggleModuleAccess = async (moduleId) => {
    try {
      const hasAccess = userModules.includes(moduleId);
      if (hasAccess) {
        await api.delete(`/users/${selectedUser}/modules/${moduleId}`);
        showMessage("success", messages.MODULE_ACCESS_REVOKED);
        setUserModules(userModules.filter((id) => id !== moduleId));
      } else {
        await api.post(`/users/${selectedUser}/modules`, { module_id: moduleId });
        showMessage("success", messages.MODULE_ACCESS_GRANTED);
        setUserModules([...userModules, moduleId]);
      }
    } catch {
      showMessage("error", messages.MODULE_ACCESS_FAIL);
    }
  };

  return (
    <div className="round-card">
      {/* User Dropdown */}
      <div className="form-container">
        <select
          className="input-field full-width"
          value={selectedUser}
          onChange={handleUserChange}
        >
          <option value="">-- Select User --</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              {u.username} ({u.role})
            </option>
          ))}
        </select>
      </div>

      {/* Modules Table */}
      {selectedUser && (
        <UserModulesTable
          modules={modules}
          userModules={userModules}
          toggleModuleAccess={toggleModuleAccess}
        />
      )}
    </div>
  );
}

export default UserModuleAccess;
