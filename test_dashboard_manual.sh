#!/bin/bash
# Manual Testing Guide for Phase 4: Dashboard API Endpoints

echo "=========================================="
echo "Phase 4 Manual Verification Tests"
echo "=========================================="
echo ""

# Test 1: Basic Stats
echo "✓ Test 1: Get Dashboard Stats (last 30 days)"
echo "---"
curl -s "http://localhost:8000/api/dashboard/stats" | python3 -m json.tool
echo ""
echo "Expected: total_subscribers, active_subscribers, total_opens, total_clicks, engagement_rate"
echo "Verify: Numbers make sense (engagement_rate should be percentage)"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 2: Date Range Filtering
echo "✓ Test 2: Test Date Range Filtering (last 7 days)"
echo "---"
START_DATE=$(date -u -d '7 days ago' '+%Y-%m-%dT%H:%M:%S')
END_DATE=$(date -u '+%Y-%m-%dT%H:%M:%S')
curl -s "http://localhost:8000/api/dashboard/stats?start_date=${START_DATE}&end_date=${END_DATE}" | python3 -m json.tool
echo ""
echo "Expected: Stats only for last 7 days (should have fewer events than 30 days)"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 3: Top Subscribers by Opens
echo "✓ Test 3: Top Subscribers Ranked by Opens"
echo "---"
curl -s "http://localhost:8000/api/dashboard/subscribers/top?limit=5&metric=opens" | python3 -m json.tool
echo ""
echo "Verify: Subscribers sorted by total_opens (descending)"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 4: Top Subscribers by Clicks
echo "✓ Test 4: Top Subscribers Ranked by Clicks"
echo "---"
curl -s "http://localhost:8000/api/dashboard/subscribers/top?limit=5&metric=clicks" | python3 -m json.tool
echo ""
echo "Verify: Subscribers sorted by total_clicks (descending)"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 5: Top Subscribers by Total Engagement
echo "✓ Test 5: Top Subscribers Ranked by Total Engagement"
echo "---"
curl -s "http://localhost:8000/api/dashboard/subscribers/top?limit=5&metric=total" | python3 -m json.tool
echo ""
echo "Verify: Subscribers sorted by total_engagement (opens + clicks, descending)"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 6: Pagination with Different Limits
echo "✓ Test 6: Test Pagination - Top 3 Subscribers"
echo "---"
curl -s "http://localhost:8000/api/dashboard/subscribers/top?limit=3" | python3 -m json.tool
echo ""
echo "Expected: Only 3 subscribers returned"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 7: Engagement Trends (30 days)
echo "✓ Test 7: Engagement Trends - Last 30 Days"
echo "---"
curl -s "http://localhost:8000/api/dashboard/trends?days=30" | python3 -m json.tool
echo ""
echo "Verify: Array of daily aggregates with date, opens, clicks, total"
echo "Verify: Dates are sorted chronologically"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 8: Engagement Trends (7 days)
echo "✓ Test 8: Engagement Trends - Last 7 Days"
echo "---"
curl -s "http://localhost:8000/api/dashboard/trends?days=7" | python3 -m json.tool
echo ""
echo "Expected: Fewer days than 30-day query"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 9: Individual Subscriber Events
echo "✓ Test 9: Get Events for Top Subscriber"
echo "---"
# Get top subscriber ID
SUBSCRIBER_ID=$(curl -s "http://localhost:8000/api/dashboard/subscribers/top?limit=1" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['subscriber_id']) if data else print('0')")
echo "Testing subscriber ID: $SUBSCRIBER_ID"
curl -s "http://localhost:8000/api/dashboard/subscribers/${SUBSCRIBER_ID}/events?limit=10" | python3 -m json.tool
echo ""
echo "Verify: Array of events sorted by created_at (newest first)"
echo "Verify: All events belong to this subscriber"
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 10: JSON Schema Validation
echo "✓ Test 10: Verify JSON Response Schemas"
echo "---"
echo "All responses should match the Pydantic schemas:"
echo "- DashboardStats: total_subscribers, active_subscribers, total_opens, total_clicks, engagement_rate, period_start, period_end"
echo "- TopSubscriber: subscriber_id, email, first_name, last_name, total_opens, total_clicks, total_engagement"
echo "- EngagementTrend: date, opens, clicks, total"
echo "- EventResponse: id, event_type, created_at, event_metadata"
echo ""
echo "All fields present and correct types? (review above outputs)"
echo ""
read -p "Press Enter to continue..."
echo ""

echo "=========================================="
echo "Manual Verification Complete!"
echo "=========================================="
echo ""
echo "Summary Checklist:"
echo "- [ ] Stats calculations are accurate"
echo "- [ ] Date range filtering works"
echo "- [ ] Ranking order is correct (opens/clicks/total)"
echo "- [ ] Pagination with limit parameter works"
echo "- [ ] JSON response formats match schemas"
echo "- [ ] Trends show daily aggregated data"
echo "- [ ] Individual subscriber events retrievable"
echo ""
echo "If all items above look correct, Phase 4 is ready to proceed!"
