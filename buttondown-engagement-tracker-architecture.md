# Buttondown Subscriber Engagement Tracker - Architecture Overview

## Project Summary

A self-hosted web application that integrates with the Buttondown newsletter API (https://docs.buttondown.com/api-introduction) to track and analyze subscriber engagement metrics, specifically focusing on email opens and click-through rates to identify the most active subscribers.

## Business Goals

- Track subscriber engagement in real time
- Identify most active subscribers based on opens and clicks
- Analyze engagement patterns across different subscriber segments
- Maintain a lightweight, easy-to-maintain solution
- Keep all components open source and either self-hosted or hosted with inexpensive cloud hosting

## Core Requirements

### Functional Requirements

1. **Real-time Engagement Tracking**
   - Capture email open events
   - Capture link click events
   - Associate events with specific subscribers and newsletters
   - Timestamp all engagement activities

2. **Subscriber Management**
   - Store subscriber basic information (name, email)
   - Track subscription dates
   - Record subscriber source/origin
   - Support custom tagging for arbitrary groupings

3. **Analytics Dashboard**
   - Display engagement metrics per subscriber
   - Rank subscribers by activity level
   - Filter and segment by tags
   - Show engagement trends over time

4. **Security**
   - Basic authentication for single-user access
   - Webhook signature verification from 
   - Secure storage of subscriber data

### Non-Functional Requirements

- Minimal maintenance overhead
- Low hosting costs
- Efficient resource utilization
- Comprehensive test coverage for maintainability
- Development/production parity

## Technical Architecture

### Technology Stack

**Backend**
- **Framework**: FastAPI (Python)
  - Modern async Python web framework
  - Automatic API documentation generation
  - Built-in data validation
  - Excellent testing support
  - Efficient async operations for API calls

**Database**
- **SQLite**
  - File-based, lightweight storage
  - Sufficient for expected data volumes
  - No separate database server required
  - Easy backup and portability

**Frontend**
- **Framework**: Vue.js
  - Simple, component-based UI
  - Calls FastAPI endpoints for data
  - Dashboard for engagement analytics

**Containerization**
- **Docker**
  - Single container deployment
  - Consistent environments across dev/prod
  - Easy deployment and scaling

### System Architecture

```
Buttondown API (External)
         ↓ (webhooks)
    FastAPI Backend
         ↓
    SQLite Database
         ↑
    FastAPI REST API
         ↑
   Frontend Dashboard
         ↑
   End User (Browser)
```

### Data Flow

1. **Webhook Ingestion (Real-time)**
   - Buttondown sends webhook POST requests to FastAPI endpoints
   - Events: `email.opened`, `link.clicked`
   - FastAPI receives, validates, and processes webhook payload
   - Event data stored immediately in SQLite

2. **Data Retrieval (On-demand)**
   - Frontend requests analytics data via FastAPI endpoints
   - FastAPI queries SQLite and aggregates engagement metrics
   - Processed data returned as JSON to frontend
   - Frontend renders visualizations and rankings

3. **No Polling Required**
   - Webhook-driven architecture eliminates need for periodic API polling
   - Real-time updates with minimal API calls to Buttondown
   - Efficient use of API rate limits

## Database Schema

### Tables Overview

1. **subscribers**
   - Primary subscriber information
   - Unique identifier, email, name (stored in Buttondown metadata as `first_name` and `last_name`)
   - Subscription date and source tracking

2. **events**
   - Core engagement tracking table
   - Links to subscriber and newsletter
   - Event type (open/click), timestamp
   - Additional metadata (IP, user agent if available)

3. **tags**
   - Custom tag definitions
   - Tag name and optional description

4. **subscriber_tags**
   - Many-to-many junction table
   - Links subscribers to tags
   - Enables complex queries and filtering

### Schema Characteristics

- **Event-centric design**: Events table is central to analytics
- **Flexible tagging**: Junction table allows arbitrary groupings and complex queries
- **Temporal tracking**: All events timestamped for trend analysis
- **Referential integrity**: Foreign keys maintain data consistency

## Hosting & Deployment

### Production Environment

**Platform**: Google Cloud Run
- Container-based deployment
- Automatic public endpoint provisioning
- Scales to zero when idle (cost optimization)
- Pay-per-request pricing model
- Cold start ~1 second (acceptable for webhooks)

**Deployment Strategy**
- Docker container pushed to Google Container Registry
- Cloud Run service configured with container image
- Environment variables for configuration
- Persistent volume for SQLite database file

### Development Environment

**Local Development**
- Same Docker container runs locally
- Different environment variables for test database
- Uses ngrok or similar for webhook testing
- Full feature parity with production

**GitHub Codespaces**
- Cloud-based development environment
- Consistent with local setup
- Easy webhook testing with port forwarding

### Network Considerations

- Production requires public internet access for webhooks
- No home network exposure needed (cloud-hosted)
- Webhook endpoint must be accessible from Buttondown servers

## Security Architecture

### Authentication & Authorization

**Dashboard Access**
- HTTP Basic Auth or simple session-based login
- Single-user application design
- Username/password protection for analytics interface

**Webhook Security**
- Signature verification of Buttondown webhook payloads
- Validation of webhook source
- HTTPS for all communications

### Data Protection

- Subscriber email addresses stored securely
- No sensitive payment or authentication data stored
- Regular backup strategy for SQLite database

## Testing Strategy

### Testing Framework

**Primary Tool**: pytest
- Native FastAPI integration via TestClient
- Excellent fixture support for test isolation
- Comprehensive assertion library

### Test Coverage Areas

1. **Unit Tests**
   - Data processing logic
   - Event aggregation functions
   - Tag filtering and querying
   - Analytics calculations

2. **Integration Tests**
   - FastAPI endpoint behavior
   - Database operations
   - Mock Buttondown API responses
   - Complete request/response cycles

3. **Webhook Testing**
   - Mock webhook payload handling
   - Signature verification
   - Event processing pipeline
   - Error handling scenarios

### Testing Infrastructure

- Separate test SQLite database
- Pytest fixtures for clean database state
- Mock external API calls (no live Buttondown requests during tests)
- Automated test runs in CI/CD pipeline

## API Integration

### Buttondown Webhooks

**Most Important Events**
Among the events defined by the Buttondown API (https://docs.buttondown.com/api-webhooks-event-types), the following are most important for this application (see API doc for descriptions of what these events mean):
- `email.sent`
- `subscriber.confirmed`
- `subscriber.delivered`
- `subscriber.opened`
- `subscriber.unsubscribed`
- `subscriber.clicked`

**Webhook Configuration**
- FastAPI endpoints registered with Buttondown
- Webhook signature validation on receipt
- Idempotent event processing (handle duplicates)

**Payload Processing**
- Extract subscriber identification
- Extract newsletter identification
- Extract event metadata (timestamp, location, etc.)
- Store in events table

### Buttondown REST API (Optional)

While webhook-driven, may optionally use REST API for:
- Initial subscriber list synchronization
- Backfilling historical data
- Periodic reconciliation
- Manual data refresh

## Development Workflow

### Environment Parity

- Same Docker image for dev/staging/prod
- Environment-specific configuration via env vars
- Consistent dependencies and versions
- SQLite database path configuration

### Local Development Process

1. Run Docker container locally
2. Use ngrok for webhook endpoint
3. Configure Buttondown to send webhooks to ngrok URL
4. Develop and test against real webhook events
5. Run pytest suite before commits

### Deployment Process

1. Build Docker image
2. Push to container registry
3. Deploy to Cloud Run
4. Update Buttondown webhook configuration
5. Verify webhook delivery and processing

## Scalability Considerations

### Current Scale

- Single-user application
- Expected low traffic volume
- SQLite sufficient for thousands of subscribers and millions of events
- Cloud Run handles variable webhook traffic

### Future Scaling Options

If needed, can migrate to:
- PostgreSQL for larger datasets
- Multiple Cloud Run instances
- Separate worker processes for heavy analytics
- Caching layer for frequently accessed data

## Maintenance & Operations

### Monitoring

- Cloud Run built-in metrics
- Webhook delivery success/failure logging
- Database size monitoring
- Error tracking and alerting

### Backup Strategy

- Regular SQLite database file backups
- Cloud storage for backup retention
- Point-in-time recovery capability

### Updates & Maintenance

- Docker-based deployment simplifies updates
- Automated testing prevents regressions
- Minimal dependency footprint reduces maintenance burden
- Clear separation of concerns in codebase

## Open Questions for Implementation

1. **Authentication Method**: HTTP Basic Auth vs session-based - evaluate trade-offs
2. **Backup Automation**: Frequency and retention policy for database backups
3. **Monitoring Tools**: Specific error tracking and logging service selection
4. **CI/CD Pipeline**: GitHub Actions vs alternatives for automated testing and deployment
5. **Analytics Queries**: Specific metrics and views to implement in dashboard
6. **Tag Management**: UI for creating and managing subscriber tags
7. **Historical Data**: Strategy for backfilling engagement data before webhook setup

## Success Metrics

- Simple presentation of all email opens and clicks
- Viewing activity of subscribers over time to recognize opportunities for further connection
- 100% webhook delivery success rate
- Comprehensive test coverage (>80%)
- Monthly hosting cost < $10
- Easy maintenance requiring < 2 hours/month

## Next Steps

1. Set up development environment and Docker configuration
2. Initialize FastAPI project structure
3. Design detailed database schema with column specifications
4. Implement Buttondown webhook endpoints
5. Create pytest test suite foundation
6. Build core analytics queries and aggregations
7. Develop frontend dashboard MVP
8. Configure Cloud Run deployment
9. Set up Buttondown webhook integration
10. Implement monitoring and backup procedures
