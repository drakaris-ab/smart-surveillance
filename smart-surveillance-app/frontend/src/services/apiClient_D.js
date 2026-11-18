import axios from 'axios';

// Create an axios instance with base config
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (attach token if available)
apiClient.interceptors.request.use(
  (config) => {
    const userData = localStorage.getItem('cctvUser');
    if (userData) {
      const { token } = JSON.parse(userData);
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor (handle errors globally)
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response) {
      console.error('API Error:', error.response.data);
      throw new Error(error.response.data.message || 'API request failed');
    } else {
      console.error('Network Error:', error.message);
      throw new Error('Network error, please try again later');
    }
  }
);

export default apiClient;
