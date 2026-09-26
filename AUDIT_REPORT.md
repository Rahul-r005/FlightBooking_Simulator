# SkyBook Full Audit Report

## Phase 1 scope

This audit was performed against the feature branch before final verification. Render's existing service configuration was inspected first.

## Build and deployment health

| Check | Finding | Severity | Status |
|---|---|---:|---|
| Render runtime | Python web service | — | Verified |
| Render build | pip install -r requirements.txt | — | Preserved |
| Render start | uvicorn FlightBooking_backend:app --host 0.0.0.0 --port $PORT | — | Preserved |
| Render health | /health | — | Preserved |
| package.json | Not present; repository is Python/FastAPI | — | Not applicable |
| Procfile | Not present | — | Not required by Render config |
| .env.example | Missing in baseline | Low | Added |
| Python version | Baseline was unpinned while CI used Python 3.11 | Medium | Fixed with .python-version = 3.11 |
| localhost API fallback | Browser falls back to same-origin window.location.origin and only uses localhost for local development | Low | Reviewed; safe |
| Static frontend | Served by the same FastAPI service | — | Preserved |

The current Render service is linked to main with automatic deploys. The build and start commands were read from the live Render service and match render.yaml. Render's documentation confirms that pushing/merging to the linked branch triggers an automatic redeploy when auto-deploy is enabled.

## Local execution limitation

A direct local clone of the feature branch could not be performed in the agent runtime because DNS/network access to github.com is unavailable. This is an environment limitation, not a code pass. The equivalent checks were added to GitHub Actions so the branch is compiled, dependency-audited, tested, and started using the real uvicorn command in a clean Ubuntu runner.

## Code-level findings

### Blocker — unauthenticated booking creation

Baseline POST /db/booking accepted unauthenticated requests.

Status: FIXED.

The endpoint now requires a server-side authenticated session and returns HTTP 401 before booking work begins. The legacy /legacy/book endpoint is also protected.

### High — no account/session model

Baseline had no authentication or authorization mechanism.

Status: FIXED.

Added Users, UserSessions, password hashing with Argon2 through pwdlib, account registration/login/logout, account suspension, server-side session lookup, and role enforcement.

### High — no booking ownership

Baseline bookings were not tied to an authenticated account.

Status: FIXED for new bookings.

Bookings now store user_id. Historical bookings remain nullable because they were created before account ownership existed. New booking creation always writes the authenticated user's ID.

### High — admin controls absent

Status: FIXED.

Added protected admin APIs for account search/details, suspension/reactivation, booking filtering, booking history, editing, and cancellation.

### High — client-only authorization risk

Status: FIXED.

The /admin page itself rejects non-admin sessions server-side, and every /admin API route uses the require_admin dependency.

### Medium — cancellation notification service absent

Status: FIXED to minimum required behavior.

No email provider existed in the baseline repository. Admin cancellation now uses a shared cancellation service that restores inventory, marks the booking Cancelled, and creates an in-app notification for the affected user. Email is deferred rather than introducing an unrelated provider.

### Medium — booking lookup exposure

Status: FIXED.

Authenticated users can only list/get/pay/cancel their own bookings. Administrators can access records through protected admin routes.

### Medium — booking search/indexing

Status: FIXED.

User IDs, flight IDs, passenger IDs, booking status/date, PNRs, flight origin/destination/departure, sessions, notifications, and account role/suspension fields have indexes appropriate to the new access patterns.

### Medium — database migration

Status: FIXED.

Added migrations/002_authenticated_booking_admin.sql. The application also performs an idempotent startup compatibility migration for the new nullable booking user_id column so the existing Render database can boot without changing the current Render build/start commands.

### Low — production debug output

Status: REVIEWED.

No production console.log/debug path was found in the existing browser flow. Unexpected booking/cancellation exceptions are logged only through the server framework's normal error path and return generic client-facing messages.

## Authentication/session security

- Passwords are hashed with pwdlib's recommended Argon2 configuration.
- Session IDs are generated with Python's secrets module and stored in the database as SHA-256 digests.
- Session cookies are HttpOnly and SameSite=Lax.
- Secure is enabled outside explicit development mode.
- Authentication credentials are not stored in localStorage.
- Sessions expire after SESSION_TTL_HOURS, default 12.
- Suspended accounts are rejected server-side.
- Role checks are performed server-side.

These choices follow the general session-management guidance to use unpredictable server-side session identifiers and Secure/HttpOnly/SameSite cookie attributes.

## Dependency/security audit

The repository has no Node package manifest, so npm audit is not applicable. The workflow now runs pip-audit against requirements.txt. Any vulnerability reported by that step is treated as a CI failure rather than silently ignored.

## Functional flow

### Unauthenticated user

1. User can search and view flights.
2. Selecting Book without a session redirects to /login with a return URL containing the selected flight.
3. Successful sign-in returns to the original page.
4. The selected flight is reopened in the booking modal.
5. The server requires the authenticated session before POST /db/booking.

### Authenticated user

1. Booking is created with user_id.
2. Booking history is scoped to that user.
3. Cancellation preserves the booking record and restores the seat.
4. Cancellation creates an in-app notification.

### Administrator

1. Non-admin users receive 403 from /admin and /admin/* APIs.
2. Admins can search accounts and view account booking history.
3. Admins can suspend/reactivate accounts.
4. Admins can filter bookings by upcoming/past/cancelled status and search by PNR/name/email.
5. Admin cancellation preserves the booking, restores the seat, and creates the customer's notification.

## Guest checkout conflict

The baseline README described a flight-booking simulator but did not document intentional guest checkout. Because authenticated booking is an explicit security requirement, guest booking was not preserved.

## Deferred items

1. Transactional email: no existing mail service was present; in-app notification is implemented.
2. Password reset and email verification: not part of the existing product flow and not required for this pass.
3. MFA: not present in the baseline and outside this feature scope.
4. Full migration runner: Render's current free service has no configured pre-deploy migration command. The checked-in PostgreSQL migration is available for explicit execution, and the startup migration protects the existing deployment from missing-column failures.

## Verification gates

The branch workflow is configured to run:

- Python compilation
- JavaScript syntax checks for the booking, authentication, and admin clients
- pip-audit
- the full pytest suite
- a real uvicorn start using the Render start command shape
- an HTTP request to /health

No final production deployment should be considered verified until these checks pass and the new commit is live on Render.
