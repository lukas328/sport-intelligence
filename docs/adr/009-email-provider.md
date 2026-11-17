# 009. E-mail: SMTP port, provider chosen by configuration

- Status: accepted (port); provider: Azure Communication Services (2026-11-17, Q-INFRA-3)
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

## Update 2026-11-17: Azure Communication Services
Lukas chose Azure Communication Services Email. It runs in the same Azure subscription as the app,
with data in Switzerland (`data_location = "Switzerland"`), under the Microsoft agreement we have
anyway, so no further processor.
- Adapter `AcsEmailSender` (`HB_EMAIL_BACKEND=acs`): the REST API signed with the resource's access
  key (`HB_ACS_CONNECTION_STRING`, from the Key Vault). This needs no SMTP user and no Entra app
  registration, and Terraform can write the key itself.
- Sending domain: the site's domain, managed by us (`noreply@handball-intelligence.com`). Its DNS
  records are set by hand. The deploy verifies them and switches the apps over only once Azure has
  verified the domain (`infra/terraform/azure/README.md`, «E-mail»).
- Open: bounces and complaints (Event Grid) are not handled yet; the app logs only failed sends.
