<template>
  <div id="app" class="container">
    <header>
      <h1>Buttondown Engagement Tracker</h1>
      <p class="subtitle">Monitor subscriber engagement in real-time</p>
    </header>

    <main>
      <DashboardStats :stats="stats" :loading="loading" />
      <EngagementChart :trends="trends" :loading="loading" />
      <TopSubscribers
        :subscribers="topSubscribers"
        :loading="loading"
        @subscriber-click="showSubscriberDetail"
      />
    </main>

    <SubscriberDetail
      v-if="selectedSubscriber"
      :subscriber="selectedSubscriber"
      @close="selectedSubscriber = null"
    />

    <footer>
      <p class="refresh-info">Dashboard auto-refreshes every 30 seconds</p>
    </footer>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';
import { dashboardAPI } from './services/api';
import DashboardStats from './components/DashboardStats.vue';
import TopSubscribers from './components/TopSubscribers.vue';
import EngagementChart from './components/EngagementChart.vue';
import SubscriberDetail from './components/SubscriberDetail.vue';

export default {
  name: 'App',
  components: {
    DashboardStats,
    TopSubscribers,
    EngagementChart,
    SubscriberDetail,
  },
  setup() {
    const stats = ref(null);
    const topSubscribers = ref([]);
    const trends = ref([]);
    const selectedSubscriber = ref(null);
    const loading = ref(true);
    let refreshInterval = null;

    const fetchDashboardData = async () => {
      loading.value = true;
      try {
        const [statsRes, subscribersRes, trendsRes] = await Promise.all([
          dashboardAPI.getStats(),
          dashboardAPI.getTopSubscribers(10, 'total'),
          dashboardAPI.getTrends(30),
        ]);

        stats.value = statsRes.data;
        topSubscribers.value = subscribersRes.data;
        trends.value = trendsRes.data;
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        loading.value = false;
      }
    };

    const showSubscriberDetail = (subscriber) => {
      selectedSubscriber.value = subscriber;
    };

    onMounted(() => {
      fetchDashboardData();
      // Refresh every 30 seconds
      refreshInterval = setInterval(fetchDashboardData, 30000);
    });

    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    });

    return {
      stats,
      topSubscribers,
      trends,
      selectedSubscriber,
      loading,
      showSubscriberDetail,
    };
  },
};
</script>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  background: #f5f5f5;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

header {
  text-align: center;
  margin-bottom: 2rem;
}

header h1 {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 2.5rem;
}

.subtitle {
  color: #666;
  font-size: 1.1rem;
  margin: 0;
}

footer {
  text-align: center;
  margin-top: 2rem;
  padding: 1rem;
}

.refresh-info {
  color: #999;
  font-size: 0.875rem;
  margin: 0;
}
</style>
