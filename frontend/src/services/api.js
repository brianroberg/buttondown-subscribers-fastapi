import axios from 'axios';

// Use relative URLs to work with any domain (localhost or GitHub Codespaces)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const dashboardAPI = {
  getStats: (startDate, endDate) =>
    api.get('/api/dashboard/stats', {
      params: { start_date: startDate, end_date: endDate }
    }),

  getTopSubscribers: (limit = 10, metric = 'opens') =>
    api.get('/api/dashboard/subscribers/top', {
      params: { limit, metric }
    }),

  getTrends: (days = 30) =>
    api.get('/api/dashboard/trends', {
      params: { days }
    }),

  getSubscriberEvents: (subscriberId, limit = 50) =>
    api.get(`/api/dashboard/subscribers/${subscriberId}/events`, {
      params: { limit }
    }),
};
