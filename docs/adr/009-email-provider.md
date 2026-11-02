# 009. E-mail: SMTP port, provider chosen by configuration

- Status: accepted (port), provider proposed: Postmark (Q-INFRA-3)
- Date: 2026-11-02

## Context
Transactional mails (magic link, invitation, later notifications). The brief names Postmark or Resend.

## Decision
- Domain code calls the `EmailSender` port. Adapters: SMTP (`aiosmtplib`), memory (tests), console.
- Locally mailpit catches everything (http://localhost:8025).
- Production uses the provider's SMTP endpoint first, which keeps us provider-neutral. A provider HTTP API
  adapter (for webhooks on bounces) can be added later without touching services.
- Proposal: **Postmark** (strong deliverability for transactional mail, message streams, bounce webhooks).
  Data residency and DPA must be checked; Resend is the alternative.
- Templates live in `services/mail_templates.py` in de-CH, en and fr, plain text first. No long dashes.
