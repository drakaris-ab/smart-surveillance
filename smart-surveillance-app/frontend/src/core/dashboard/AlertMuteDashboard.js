import React, { useEffect, useState } from "react";
import { useAlertMuteApi } from "../../services/AlertMute";
import useAlertService from "../../services/alertService";
import "../../styles/global.css";
import "../../styles/alertMute.css";

const DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function AlertMuteDashboard() {
  const { getSchedules, createSchedule, updateSchedule, deleteSchedule } = useAlertMuteApi();
  const alertService = useAlertService();
  const [schedules, setSchedules] = useState([]);
  const [form, setForm] = useState({
    date: "",
    start_date: "",
    end_date: "",
    start_time: "",
    end_time: "",
    days: [],
    is_active: true,
  });
  const [editingId, setEditingId] = useState(null);

  useEffect(() => {
    fetchSchedules();
  }, []);

  const fetchSchedules = async () => {
    try {
      const data = await getSchedules();
      setSchedules(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDayToggle = (day) => {
    if (day === "All") {
      if (form.days.length === DAYS_OF_WEEK.length) {
        setForm({ ...form, days: [] });
      } else {
        setForm({ ...form, days: [...DAYS_OF_WEEK] });
      }
      return;
    }

    const newDays = form.days.includes(day)
      ? form.days.filter((d) => d !== day)
      : [...form.days, day];
    
    setForm({ ...form, days: newDays });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (form.start_time && !form.end_time) {
      alertService.error("Please provide an end time to complete the time range.");
      return;
    }
    if (!form.start_time && form.end_time) {
      alertService.error("Please provide a start time to complete the time range.");
      return;
    }
    if (form.start_date && !form.end_date) {
      alertService.error("Please provide an end date to complete the date range.");
      return;
    }
    if (!form.start_date && form.end_date) {
      alertService.error("Please provide a start date to complete the date range.");
      return;
    }

    const payload = {
      date: form.date || null,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      start_time: form.start_time || null,
      end_time: form.end_time || null,
      days: form.days.length > 0 ? form.days.join(",") : null,
      is_active: form.is_active,
    };

    try {
      if (editingId) {
        await updateSchedule(editingId, payload);
        alertService.success("✅ Schedule updated successfully!");
        setEditingId(null);
      } else {
        await createSchedule(payload);
        alertService.success(`✅ Mute Scheduled Successfully!`);
      }

      setForm({ date: "", start_date: "", end_date: "", start_time: "", end_time: "", days: [], is_active: true });
      fetchSchedules();
    } catch (error) {
      console.error("Error saving schedule:", error);
      alertService.error("❌ Failed to save schedule. Please try again.");
    }
  };

  const handleEdit = (schedule) => {
    const daysArr = schedule.days ? schedule.days.split(",").map(d => d.trim()) : [];
    
    setForm({
      date: schedule.date || "",
      start_date: schedule.start_date || "",
      end_date: schedule.end_date || "",
      start_time: schedule.start_time || "",
      end_time: schedule.end_time || "",
      days: daysArr,
      is_active: schedule.is_active,
    });
    setEditingId(schedule.id);
    alertService.info("Editing schedule...");
  };

  const handleDelete = async (id) => {
    try {
      await deleteSchedule(id);
      alertService.success("✅ Schedule deleted successfully!");
      fetchSchedules();
    } catch (error) {
      console.error("Error deleting schedule:", error);
      alertService.error("❌ Failed to delete schedule.");
    }
  };

  const formatDays = (daysStr) => {
    if (!daysStr) return "Any Day";
    const arr = daysStr.split(",");
    if (arr.length === 7) return "Every Day";
    return daysStr;
  };

  return (
    <div className="alert-mute-container">
      <h2>Alert Mute Schedules</h2>

      <div className="premium-mute-form">
        <form onSubmit={handleSubmit}>
          
          <div className="form-section">
            <div className="form-section-title">
              📅 Specific Date (Optional)
            </div>
            <div className="datetime-grid">
              <div className="premium-input-wrap">
                <label>Single Date</label>
                <input
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                  className="premium-input"
                />
              </div>
              <div className="premium-input-wrap">
                <label>Start Date</label>
                <input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                  className="premium-input"
                />
              </div>
              <div className="premium-input-wrap">
                <label>End Date</label>
                <input
                  type="date"
                  value={form.end_date}
                  onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                  className="premium-input"
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <div className="form-section-title">
              ⏰ Time Range (Optional)
            </div>
            <div className="datetime-grid">
              <div className="premium-input-wrap">
                <label>Start Time</label>
                <input
                  type="time"
                  value={form.start_time}
                  onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                  className="premium-input"
                />
              </div>
              <div className="premium-input-wrap">
                <label>End Time</label>
                <input
                  type="time"
                  value={form.end_time}
                  onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                  className="premium-input"
                />
              </div>
            </div>
          </div>

          <div className="form-section">
            <div className="form-section-title">
              🗓️ Days of the Week (Optional)
            </div>
            <div className="days-selector">
              <label className="day-pill">
                <input
                  type="checkbox"
                  checked={form.days.length === DAYS_OF_WEEK.length}
                  onChange={() => handleDayToggle("All")}
                />
                <span>All</span>
              </label>
              {DAYS_OF_WEEK.map((day) => (
                <label key={day} className="day-pill">
                  <input
                    type="checkbox"
                    checked={form.days.includes(day)}
                    onChange={() => handleDayToggle(day)}
                  />
                  <span>{day}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="action-row">
            <label className="toggle-wrap">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              <span style={{color: '#000', fontWeight: '500'}}>Schedule is Active</span>
            </label>

            <button type="submit" className="premium-submit-btn">
              {editingId ? "Update Schedule" : "Add Schedule"}
            </button>
          </div>

        </form>
      </div>

      {/* Logs Table */}
      <div className="premium-table-wrap">
        <table className="premium-table">
          <thead>
            <tr>
              <th>Date / Range</th>
              <th>Time Range</th>
              <th>Days</th>
              <th>Status</th>
              <th style={{textAlign: 'right'}}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {schedules.map((s) => (
              <tr key={s.id}>
                <td>
                  {s.date ? s.date : s.start_date && s.end_date ? `${s.start_date} to ${s.end_date}` : <span style={{color: '#666'}}>Any Date</span>}
                </td>
                <td>
                  {s.start_time && s.end_time 
                    ? `${s.start_time} - ${s.end_time}` 
                    : <span style={{color: '#666'}}>All Day</span>
                  }
                </td>
                <td>{formatDays(s.days)}</td>
                <td>
                  <span className={`status-badge ${s.is_active ? 'status-active' : 'status-inactive'}`}>
                    {s.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td style={{textAlign: 'right'}}>
                  <button type="button" onClick={() => handleEdit(s)} className="action-btn">
                    Edit
                  </button>
                  <button type="button" onClick={() => handleDelete(s.id)} className="action-btn delete">
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {schedules.length === 0 && (
              <tr>
                <td colSpan="5" className="empty-state">
                  No mute schedules found. Add one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
