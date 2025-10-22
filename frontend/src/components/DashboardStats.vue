<template>
  <div class="stats-grid">
    <div class="stat-card">
      <h3>Total Subscribers</h3>
      <p class="stat-value">{{ stats?.total_subscribers || 0 }}</p>
    </div>

    <div class="stat-card">
      <h3>Active Subscribers</h3>
      <p class="stat-value">{{ stats?.active_subscribers || 0 }}</p>
    </div>

    <div class="stat-card">
      <h3>Email Opens</h3>
      <p class="stat-value">{{ stats?.total_opens || 0 }}</p>
    </div>

    <div class="stat-card">
      <h3>Link Clicks</h3>
      <p class="stat-value">{{ stats?.total_clicks || 0 }}</p>
    </div>

    <div class="stat-card">
      <h3>Engagement Rate</h3>
      <p class="stat-value">{{ stats?.engagement_rate || 0 }}%</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    stats: Object,
    loading: Boolean,
  },
};
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-card h3 {
  font-size: 0.875rem;
  font-weight: 600;
  color: #666;
  margin: 0 0 0.5rem 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #333;
  margin: 0.5rem 0 0 0;
}
</style>
