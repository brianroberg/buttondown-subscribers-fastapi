<template>
  <div class="top-subscribers">
    <h2>Most Engaged Subscribers</h2>

    <div v-if="loading" class="loading">Loading...</div>

    <table v-else>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Email</th>
          <th>Opens</th>
          <th>Clicks</th>
          <th>Total</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(subscriber, index) in subscribers"
          :key="subscriber.subscriber_id"
          @click="$emit('subscriber-click', subscriber)"
          class="clickable"
        >
          <td>{{ index + 1 }}</td>
          <td>{{ subscriber.email || 'No email' }}</td>
          <td>{{ subscriber.total_opens }}</td>
          <td>{{ subscriber.total_clicks }}</td>
          <td><strong>{{ subscriber.total_engagement }}</strong></td>
        </tr>
      </tbody>
    </table>

    <div v-if="!loading && subscribers.length === 0" class="empty-state">
      No subscriber data available yet. Webhooks will populate this table.
    </div>
  </div>
</template>

<script>
export default {
  props: {
    subscribers: Array,
    loading: Boolean,
  },
  emits: ['subscriber-click'],
};
</script>

<style scoped>
.top-subscribers {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-top: 2rem;
}

.top-subscribers h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
  font-size: 1.5rem;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  text-align: left;
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
}

th {
  font-weight: 600;
  color: #666;
  background: #f9f9f9;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.clickable {
  cursor: pointer;
  transition: background-color 0.2s;
}

.clickable:hover {
  background: #f5f5f5;
}

.loading, .empty-state {
  text-align: center;
  padding: 2rem;
  color: #666;
}
</style>
