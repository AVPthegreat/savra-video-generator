import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // Crucial for HttpOnly Cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Global 401 interceptor: redirect to /login on session expiry
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Don't redirect if this was a background auth check or we're already on login/signup
      const isAuthCheck = error.config?.url?.includes('/auth/me');
      const isPublicPage = ['/login', '/signup', '/'].includes(window.location.pathname);
      
      if (!isAuthCheck && !isPublicPage) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
