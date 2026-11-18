import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  cameras: [],
};

const cameraSlice = createSlice({
  name: 'cameras',
  initialState,
  reducers: {
    setCameras: (state, action) => {
      state.cameras = action.payload;
    }
  },
});

export const { setCameras } = cameraSlice.actions;
export default cameraSlice.reducer;
