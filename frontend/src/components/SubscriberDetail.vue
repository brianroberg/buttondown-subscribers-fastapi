<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Subscriber Details</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <div class="subscriber-info">
          <div class="info-item">
            <strong>Email:</strong>
            <span>{{ subscriber.email || 'N/A' }}</span>
          </div>
          <div class="info-item">
            <strong>Name:</strong>
            <span>{{ fullName || 'N/A' }}</span>
          </div>
          <div class="info-item">
            <strong>Total Opens:</strong>
            <span>{{ subscriber.total_opens }}</span>
          </div>
          <div class="info-item">
            <strong>Total Clicks:</strong>
            <span>{{ subscriber.total_clicks }}</span>
          </div>
          <div class="info-item">
            <strong>Total Engagement:</strong>
            <span><strong>{{ subscriber.total_engagement }}</strong></span>
          </div>
        </div>

        <div class="events-section">
          <h3>Recent Activity</h3>
          <div v-if="loadingEvents" class="loading">Loading events...</div>
          <div v-else-if="events.length === 0" class="empty-state">No events recorded yet.</div>
          <ul v-else class="events-list">
            <li v-for="event in events" :key="event.id" class="event-item">
              <span class="event-type">{{ formatEventType(event.event_type) }}</span>
              <span class="event-date">{{ formatDate(event.created_at) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { dashboardAPI } from '../services/api';

export default {
  props: {
    subscriber: Object,
  },
  emits: ['close'],
  setup(props) {
    const events = ref([]);
    const loadingEvents = ref(true);

    const fullName = computed(() => {
      const first = props.subscriber.first_name || '';
      const last = props.subscriber.last_name || '';
      return first || last ? `${first} ${last}`.trim() : null;
    });

    const formatEventType = (eventType) => {
      const types = {
        'subscriber.opened': 'Email Opened',
        'subscriber.clicked': 'Link Clicked',
        'subscriber.confirmed': 'Subscribed',
        'subscriber.unsubscribed': 'Unsubscribed',
        'subscriber.delivered': 'Email Delivered',
        'email.sent': 'Email Sent'
      };
      return types[eventType] || eventType;
    };

    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleString();
    };

    onMounted(async () => {
      try {
        const response = await dashboardAPI.getSubscriberEvents(props.subscriber.subscriber_id);
        events.value = response.data;
      } catch (error) {
        console.error('Error loading subscriber events:', error);
      } finally {
        loadingEvents.value = false;
      }
    });

    return {
      events,
      loadingEvents,
      fullName,
      formatEventType,
      formatDate
    };
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #eee;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  cursor: pointer;
  color: #666;
  line-height: 1;
  padding: 0;
  width: 2rem;
  height: 2rem;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 1.5rem;
}

.subscriber-info {
  margin-bottom: 2rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid #eee;
}

.info-item strong {
  color: #666;
}

.events-section h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
}

.events-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.event-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
}

.event-type {
  font-weight: 500;
  color: #333;
}

.event-date {
  color: #666;
  font-size: 0.875rem;
}

.loading, .empty-state {
  text-align: center;
  padding: 2rem;
  color: #666;
}
</style>
