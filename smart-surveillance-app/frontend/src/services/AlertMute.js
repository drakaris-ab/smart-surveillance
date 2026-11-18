import api from "./api";

const BASE_URL = "/alert-mute";

export const useAlertMuteApi = () => {
  const getSchedules = async () => {
    try {
      const res = await api.get(`${BASE_URL}/`);
      return res.data || res;
    } catch {
      return [];
    }
  };

  const createSchedule = async (schedule) => {
    // The backend router is @router.post("")
    const res = await api.post(BASE_URL, schedule);
    return res.data || res;
  };

  const updateSchedule = async (id, schedule) => {
    const res = await api.put(`${BASE_URL}/${id}`, schedule);
    return res.data || res;
  };

  const deleteSchedule = async (id) => {
    const res = await api.delete(`${BASE_URL}/${id}`);
    return res.data || res;
  };

  const getActiveOrUpcomingMute = async () => {
    try {
      const res = await api.get(`${BASE_URL}/`);
      const data = res.data || res;
      const now = new Date();

      if (!Array.isArray(data)) return [];

      return data.filter((s) => {
        const end = new Date(s.end_time);
        return s.is_active && end > now;
      });
    } catch (error) {
      console.error("Error fetching mute schedules:", error);
      return [];
    }
  };

  return {
    getSchedules,
    createSchedule,
    updateSchedule,
    deleteSchedule,
    getActiveOrUpcomingMute,
  };
};
