# API Planning & Roadmap

This document outlines the architectural roadmap for the Savra Video Generator API. The primary objective is to evolve the current monolithic, admin-only API into a tiered system that safely supports public consumer traffic without exposing the infrastructure to abuse or unmanageable cloud costs.

---

## 1. Current State vs. Target State

### Current State (Alpha)
*   **Monolithic Auth:** All generation endpoints (`/upload`, `/generate/async`) share the same `require_auth_if_enabled` dependency.
*   **Binary Access:** Either everyone needs a JWT admin token (`ENABLE_AUTH=true`), or the API is entirely open to the world (`ENABLE_AUTH=false`).

### Target State (Production)
*   **Tiered Access:** Separate public (consumer) endpoints from private (admin) endpoints.
*   **Strict Security:** Public endpoints protected by ReCAPTCHA/Turnstile and strict IP/Session rate limiting.
*   **Resource Throttling:** Hard caps on generation limits based on the access tier.

---

## 2. Proposed API Architecture

We propose splitting the generation APIs into two distinct routers:

### A. Admin APIs (`/api/v1/admin/*`)
*   **Endpoints:** `/admin/generate`, `/admin/jobs`, `/admin/metrics`
*   **Auth:** Requires valid Admin JWT.
*   **Limits:** High rate limits (e.g., 100 requests/hour), max scenes up to 8, bypasses bot checks.

### B. Public Consumer APIs (`/api/v1/public/*`)
*   **Endpoints:** `/public/generate`, `/public/upload`
*   **Auth:** No JWT required, but requires a valid anti-bot token (e.g., `X-Recaptcha-Token`).
*   **Limits:** 
    *   Strict rate limit (e.g., 2 successful generations per hour per IP).
    *   `max_scenes` hard-capped to 3 on the backend.
    *   `extracted_text` max length reduced.

---

## 3. Implementation Phases

### Phase 1: Abuse Protection & Bot Mitigation
Before exposing any public endpoints, we must prevent automated scripts from draining our LLM API credits and Cloud Run compute.
*   **Frontend Integration:** Add Cloudflare Turnstile or Google reCAPTCHA v3 to the `ConsumerFlow` input form.
*   **Backend Validation:** Create a new dependency `verify_humanity` that validates the anti-bot token against the provider's API before queuing the job.

### Phase 2: Redis-Backed Rate Limiting
The current `_AuthRateLimiter` is an in-memory Python dictionary. This fails in a multi-instance Cloud Run environment.
*   **Infrastructure:** Provision a minimal Redis instance (e.g., Google Memorystore or Upstash).
*   **Middleware:** Implement Redis-based rate limiting (e.g., Token Bucket algorithm) keyed by the client's IP Address and a generated Session ID.

### Phase 3: Hardware Quotas & Alerts
To protect the financial bottom line:
*   Implement daily generation quotas (e.g., maximum 500 total jobs per day across the platform).
*   Once the daily quota is reached, the `/public/generate` endpoint immediately returns `503 Service Unavailable` with a friendly "Daily Capacity Reached" message, preventing any further LLM or Renderer calls.

---

## 4. Open Questions for Technical Review
1.  **Storage Costs:** Should public consumer videos auto-delete after 24 hours to save on GCS storage costs?
2.  **Concurrency:** If public traffic spikes, do we queue jobs indefinitely, or do we start rejecting requests with `429 Too Many Requests` if the queue exceeds 50 items?
3.  **Monetization / API Keys:** Do we plan to offer an API-key tier for developers to integrate our generation engine into their apps? If so, we need an API Gateway setup.
