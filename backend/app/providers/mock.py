"""Deterministic offline provider with reproducible validation failures for grading.

Its text rules do not measure LLM accuracy. Missing facts remain null, and domain-based
company guesses are visibly ungrounded in the shared pipeline.
"""

import asyncio
import json
import re
from typing import Any

from ..schemas import Ticket
from .ticket_text import customer_text


def first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None


class MockProvider:
    def __init__(self, delay_ms: int = 650):
        self.delay_ms = delay_ms

    async def extract(self, ticket: Ticket, feedback: str | None = None) -> str:
        await asyncio.sleep(self.delay_ms / 1000)
        content = customer_text(ticket.body)
        # Current requests lead; quoted customer issues remain available as context.
        sources = (content.current, content.quoted, ticket.subject)
        body = f"{content.current}\n{content.quoted}"
        text = f"{ticket.subject}\n{body}"
        evidence: dict[str, str | None] = {}
        notes: list[str] = []

        product_quote = None
        for source in sources:
            product_quote = first_match(
                source, r"zen (?:orchestrator|studioo?|connect|insights|vault)"
            )
            if product_quote:
                break
        product = product_quote.title() if product_quote else None
        if product and product.lower() == "zen studioo":
            product = "Zen Studio"
            notes.append("Product spelling was normalized from 'zen studioo'; verify it.")
        evidence["product"] = product_quote

        company = self._company(content.current_identity) or self._company(content.quoted_identity)
        evidence["company"] = company
        if not company:
            company = ticket.from_email.split("@")[-1].split(".")[0].title()
            evidence["company"] = None
            notes.append("Company was inferred from the sender domain; confirm its full name.")
        elif ticket.from_email.split("@")[-1].split(".")[0].lower() not in company.lower():
            notes.append("Company in the body differs from the sender domain; verify the identity.")

        issue_rules = [
            ("churn_risk", r"non-renewal|do not renew|termination clause|not renew|contract lapse"),
            ("billing", r"billed|charged|invoice|refund|credit|factures|remboursement"),
            (
                "outage",
                r"failed overnight|unavailable|service down|dash(?:board|bord) is blank"
                r"|completely down|nobody can run|throwing 502",
            ),
            ("feature_request", r"any plan to add|bulk re-run|SSO|Entra ID|roadmap|row-level"),
            (
                "bug",
                r"serial numbers|serial-number|apostrophe|drops rows|échecs"
                r"|\b(?:returns?|shows?|throws?|raises?|displays?)\b[^\n.!?]{0,60}\b(?:error|erreur)\b"
                r"|\b(?:error|erreur)\s+(?:(?:code\s*)?\d{3,5}|when\b|while\b|during\b|occurs?\b)",
            ),
        ]
        category = None
        for source in sources:
            for candidate, pattern in issue_rules:
                quote = first_match(source, pattern)
                if quote:
                    category, evidence["category"] = candidate, quote
                    break
            if category:
                break
        if category is None:
            for source in sources:
                quote = first_match(source, r"how do|where do|does .*count|is there|can you")
                if quote:
                    category, evidence["category"] = "how_to", quote
                    break
        # Detect multiple issue types without a ticket-ID-specific expected output.
        issue_categories = [
            candidate for candidate, pattern in issue_rules if first_match(body, pattern)
        ]
        if len(issue_categories) > 1:
            notes.append(
                f"Multiple issues: {', '.join(issue_categories)}. Primary category is {category}."
            )
        if content.quoted.strip():
            notes.append(
                "Quoted customer content was retained as context; verify its current status."
            )

        severity_quote = first_match(
            text, r"URGENT|critical|all of our scheduled jobs|blocker|workaround"
        )
        severity = None
        if severity_quote:
            signal = severity_quote.lower()
            severity = (
                "critical"
                if signal in {"urgent", "critical"}
                else "low"
                if signal == "workaround"
                else "high"
            )
        evidence["severity"] = severity_quote
        if not severity:
            notes.append("Severity is unsupported: a reviewer must choose it from impact evidence.")

        action_rules = [
            ("refund", r"refund|remboursement|back on the card"),
            ("credit", r"credit is fine|want a credit|credit of"),
            ("callback", r"asked for a call|call with|call me|callback"),
            ("fix", r"please fix|pls fix|resolved|without a fix|can u pls fix"),
            (
                "information",
                r"confirm|written plan|explain|how do|where do|quick one|any plan|is there",
            ),
        ]
        # A support agent offering an option is not the customer's requested action.
        action = "none"
        action_source = content.current
        for source in (content.current, content.quoted):
            action_text = "\n".join(
                line
                for line in source.splitlines()
                if not line.strip().upper().startswith("AGENT:")
            )
            for candidate, pattern in action_rules:
                quote = first_match(action_text, pattern)
                if quote:
                    action, evidence["requested_action"] = candidate, quote
                    action_source = action_text
                    break
            if action != "none":
                break

        amount: float | None = None
        amount_source = action_source
        if not first_match(amount_source, r"\$|\bEUR\b"):
            amount_source = body
        if action == "refund" and not first_match(amount_source, r"\bEUR\b"):
            dollars = re.findall(r"\$\s*([\d,]+(?:\.\d{1,2})?)", amount_source)
            # A sole amount beside a refund request is a proposal for the reviewer to verify.
            if len(dollars) == 1:
                amount = float(dollars[0].replace(",", ""))
                evidence["refund_amount"] = first_match(amount_source, r"\$\s*[\d,]+(?:\.\d{1,2})?")
            elif dollars:
                notes.append("Multiple USD amounts: refund amount requires human reconciliation.")
        if first_match(body, r"\bEUR\b"):
            eur_quote = first_match(body, r"[\d ]+ EUR")
            notes.append(
                f"Original amount: {eur_quote}. Currency is EUR; no USD conversion was made."
            )
        if "nine thousand something" in body.lower():
            notes.append("Spoken amount is approximate; no exact USD refund amount was invented.")
        if action == "credit":
            notes.append("Requested action is credit; refund_amount is intentionally empty.")

        deadline = first_match(body, r"\b20\d{2}-\d{2}-\d{2}\b")
        evidence["deadline"] = deadline
        relative = first_match(body, r"by Friday|before quarter end|before the \d+(?:th|st|nd|rd)")
        if not deadline and relative:
            notes.append(f"Ambiguous deadline '{relative}' was not converted to a calendar date.")

        escalation = first_match(body, r"escalating|CFO|CTO|leadership|escalat(?:ed|ion)")
        evidence["escalated"] = escalation
        if ticket.attachments:
            notes.append("Attachments are counted in metadata but their contents are unavailable.")

        record: dict[str, Any] = {
            "company": company,
            "product": product,
            "category": category,
            "severity": severity,
            "requested_action": action,
            "refund_amount": amount,
            "deadline": deadline,
            "escalated": bool(escalation),
        }
        # Fixed examples make the retry behavior reproducible across runs and interviews.
        if ticket.id == "tkt_0005" and feedback is None:
            record["severity"] = "urgent"  # Invalid enum; the repair attempt returns 'critical'.
        if ticket.id == "tkt_0003":
            record["product"] = "Zen Unknown"  # Both attempts fail; preserve the raw proposal.
        return json.dumps(
            {"record": record, "evidence": evidence, "notes": notes}, ensure_ascii=False
        )

    @staticmethod
    def _company(body: str) -> str | None:
        patterns = [
            r"\|[^\n|]+\|\s*([^\n]+)",
            r"(?:admin,|VP Technology,)\s*([^\n]+)",
            r"CALLER:.*?from ([^.\n]+)",
            r"Regards\s*\n[^\n]+\n([^\n]+)",
            r"Cordialement,\s*\n[^\n]+\n([^\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
