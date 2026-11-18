import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  user: null,       // { username, role, ... }
  token: null,      // JWT or session token
  isAuthenticated: false,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    login: (state, action) => {
      const { user, token } = action.payload;
      state.user = user;
      state.token = token;
      state.isAuthenticated = true;

      // Persist to localStorage for session continuity
      localStorage.setItem('cctvUser', JSON.stringify({ user, token }));
    },
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;

      localStorage.removeItem('cctvUser');
    },
    restoreSession: (state) => {
      const saved = localStorage.getItem('cctvUser');
      if (saved) {
        const { user, token } = JSON.parse(saved);
        state.user = user;
        state.token = token;
        state.isAuthenticated = true;
      }
    },
  },
});

export const { login, logout, restoreSession } = authSlice.actions;
export default authSlice.reducer;
