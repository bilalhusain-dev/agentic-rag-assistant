# NEXUS CLOUD PLATFORM — SERVICE LEVEL AGREEMENT (SLA)
Document ID: SLA-ENTERPRISE-2026-Q1
Target Audience: Enterprise Tier Customers

## 1. Service Availability Commitment
Nexus Cloud commits to providing an Monthly Uptime Percentage of at least **99.95%** across all production core API clusters and distributed storage systems during any billing month.

| Monthly Uptime Percentage | Service Credit Percentage |
| :--- | :--- |
| Equal to or greater than 99.95% | 0% (Standard SLA met) |
| Less than 99.95% but ≥ 99.00% | 10% credit applied to monthly invoice |
| Less than 99.00% but ≥ 95.00% | 25% credit applied to monthly invoice |
| Less than 95.00% | 50% credit applied to monthly invoice |

## 2. Support Severity Levels and Response Time Targets
When an incident is reported via the customer portal or automated webhook, Nexus Support commits to the following first-response time targets:

### Priority 1 — Critical Outage (P1)
- **Definition:** Production system completely down, critical customer business operations halted, or data corruption detected.
- **Initial Response Target:** 15 minutes (24/7/365 coverage).
- **Update Frequency:** Every 30 minutes until mitigation.
- **Target Resolution:** Under 2 hours.

### Priority 2 — Significant Degradation (P2)
- **Definition:** Production system operational but experiencing substantial latency (>1500ms p99), or major feature unavailable with no immediate workaround.
- **Initial Response Target:** 1 hour (24/7/365 coverage).
- **Update Frequency:** Every 2 hours.
- **Target Resolution:** Under 6 hours.

### Priority 3 — Minor Issue (P3)
- **Definition:** Non-critical inquiry, minor bug affecting isolated users with acceptable workaround available.
- **Initial Response Target:** 4 business hours.
- **Update Frequency:** Daily.

### Priority 4 — General Request / Feature Inquiry (P4)
- **Definition:** Architectural questions, configuration guidance, or enhancement requests.
- **Initial Response Target:** 24 business hours.

## 3. SLA Exclusions & Scheduled Maintenance
The Service Availability calculation excludes downtime resulting from:
1. Scheduled maintenance announced at least five (5) business days in advance, occurring during standard maintenance windows (Sundays 02:00 to 06:00 UTC).
2. Customer network failures, misconfigured DNS, or misuse of API endpoints.
3. Force majeure events outside reasonable control, including third-party upstream ISP transit cuts.
