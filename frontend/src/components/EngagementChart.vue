<template>
  <div class="engagement-chart">
    <h2>Engagement Trends (Last 30 Days)</h2>

    <div v-if="loading" class="loading">Loading chart...</div>

    <div v-else-if="chartData.labels.length === 0" class="empty-state">
      No trend data available yet. Data will appear after the next sync.
    </div>

    <canvas v-else ref="chartCanvas"></canvas>
  </div>
</template>

<script>
import { ref, watch, onMounted, nextTick } from 'vue';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

export default {
  props: {
    trends: Array,
    loading: Boolean,
  },
  setup(props) {
    const chartCanvas = ref(null);
    let chartInstance = null;

    const chartData = ref({
      labels: [],
      datasets: []
    });

    const updateChart = () => {
      if (!props.trends || props.trends.length === 0) {
        chartData.value = { labels: [], datasets: [] };
        if (chartInstance) {
          chartInstance.destroy();
          chartInstance = null;
        }
        return;
      }

      const labels = props.trends.map(t => t.date);
      const opens = props.trends.map(t => t.opens);
      const clicks = props.trends.map(t => t.clicks);

      chartData.value = {
        labels,
        datasets: [
          {
            label: 'Opens',
            data: opens,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.3
          },
          {
            label: 'Clicks',
            data: clicks,
            borderColor: 'rgb(255, 99, 132)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            tension: 0.3
          }
        ]
      };

      nextTick(() => {
        if (chartCanvas.value && chartData.value.labels.length > 0) {
          if (chartInstance) {
            chartInstance.destroy();
          }

          const ctx = chartCanvas.value.getContext('2d');
          chartInstance = new Chart(ctx, {
            type: 'line',
            data: chartData.value,
            options: {
              responsive: true,
              maintainAspectRatio: true,
              plugins: {
                legend: {
                  position: 'top',
                },
                tooltip: {
                  mode: 'index',
                  intersect: false,
                }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  ticks: {
                    precision: 0
                  }
                }
              }
            }
          });
        }
      });
    };

    watch(() => props.trends, updateChart, { deep: true });
    watch(() => props.loading, (newLoading) => {
      if (!newLoading) {
        updateChart();
      }
    });

    onMounted(() => {
      if (!props.loading) {
        updateChart();
      }
    });

    return {
      chartCanvas,
      chartData
    };
  }
};
</script>

<style scoped>
.engagement-chart {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-top: 2rem;
}

.engagement-chart h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
  font-size: 1.5rem;
}

canvas {
  max-height: 300px;
}

.loading, .empty-state {
  text-align: center;
  padding: 2rem;
  color: #666;
}
</style>
