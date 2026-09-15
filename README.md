# Autonomous Revenue Engine V3

A practical AI-assisted micro-service engine designed for real business outcomes.

## Core loop
1. Discover repeated public demand.
2. Score demand by urgency, specificity, buyer intent, and repeatability.
3. Fuse the strongest signal into a small service offer.
4. Generate a concrete deliverable checklist and price hypothesis.
5. Generate a permission-based outreach draft.
6. Track prospect → conversation → sale → fulfillment → result.
7. Feed results back into offer selection.

## Modes
- Manual: research only.
- Approval: generate drafts and queue actions for review.
- Autopilot: run bounded background jobs, while still refusing spam, impersonation,
  fabricated claims, private-data access, or purchases.

## AI
The app uses an OpenAI-compatible endpoint. Configure it with environment variables.
API usage is separate from a ChatGPT subscription; the API is usage-billed. Keep keys
in environment variables/secrets and never commit them.

## Real-revenue design
The software cannot guarantee revenue. It is built to improve the path from public
demand -> offer -> outreach -> paid pilot -> repeatable service. You still need to
communicate with real prospects and actually deliver the promised work.

## Computer 24/7
Install Python 3.11+, run `pip install -r requirements.txt`, set `.env`, then:
`python app.py`

Keep the computer powered and connected.

## iPhone 24/7
The included GitHub Actions worker runs the scheduled analysis in the cloud. The
iPhone dashboard is a control/readout interface. iOS itself does not provide a
reliable always-on Python server.

## Security
Never put an OpenAI API key in frontend code. Use environment variables or repository
secrets. Set an API project spend limit before enabling unattended jobs.
