import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  alerts: [],
};

const alertSlice = createSlice({
  name: 'alerts',
  initialState,
  reducers: {
    addAlert: (state, action) => {
      // Just a dummy implementation since we adapted to MessageContext earlier
      state.alerts.push(action.payload);
    },
    removeAlert: (state, action) => {
      state.alerts = state.alerts.filter((a, index) => index !== action.payload);
    }
  },
});

export const { addAlert, removeAlert } = alertSlice.actions;
export default alertSlice.reducer;
