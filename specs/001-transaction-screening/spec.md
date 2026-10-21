# Feature Specification: Transaction screening

**Feature Branch**: `001-transaction-screening`  
**Status**: Ready  
**Input**: Screen synthetic USD transfers with explainable demonstration rules.

## User Scenarios & Testing

As an analyst, I submit one synthetic transfer and receive stable reason codes.
As an operator, I verify a release against the same acceptance criteria after deployment.
As a reviewer, I require specification and implementation evidence before merging.

## Acceptance Criteria

- **AC-001**: GET /health returns 200 with status ok and rules_version demo-v1.
- **AC-002**: A USD 25.00 transfer to CA with an ordinary beneficiary is not flagged.
- **AC-003**: A USD 10000.00 transfer is flagged with LARGE_TRANSFER.
- **AC-004**: A transfer to synthetic destination XZ is flagged with DEMO_HIGH_RISK_DESTINATION.
- **AC-005**: Beneficiary Blocked Demo Entity is flagged with DEMO_WATCHLIST_MATCH.
- **AC-006**: Zero amount is rejected with HTTP 422 and a validation detail.

## Requirements

- Decimal arithmetic, two decimal places, positive amounts, USD only.
- Multiple matching rules return all applicable reasons in deterministic order.
- Screening is stateless; neither request bodies nor beneficiary names enter the audit log.
- No model, network call, sanctions dataset, or random decision in the screening path.
- Machine-readable smoke inputs live in acceptance.yaml and cover every AC exactly once.

## Clarifications

- Resolved: currency is USD only; no FX conversion.
- Resolved: XZ and ZZ are synthetic policy codes, not real country-risk classifications.
- Resolved: matching is case-insensitive exact text after trimming outer whitespace.
- Resolved: rollback requires an operator at a local CLI; the agent cannot approve it.

## Out of Scope

Production AML decisions, real sanctions screening, customer data, authentication,
rate limiting, persistent transfer history, and automated rollback approval.
