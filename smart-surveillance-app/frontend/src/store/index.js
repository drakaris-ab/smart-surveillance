import { configureStore } from '@reduxjs/toolkit';
import authReducer from './authSlice';
import cameraReducer from './cameraSlice';
import alertReducer from './alertSlice';

const store = configureStore({
  reducer: {
    auth: authReducer,
    cameras: cameraReducer,
    alerts: alertReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false, // allows non-serializable values like Date if needed
    }),
  devTools: process.env.NODE_ENV !== 'production',
});

export default store;
