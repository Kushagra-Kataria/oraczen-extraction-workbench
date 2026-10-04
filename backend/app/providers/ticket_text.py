"""Conservative text views for mock rules; the original Ticket is never modified."""

import re
from dataclasses import dataclass

# These identify message structure, not products, categories, or individual tickets.
FOOTER_START = re.compile(
    r"^(?:this (?:e-?mail|message)(?: and [^\n]*)?[^\n]*"
    r"(?:confidential|privileged|intended (?:solely|only))"
    r"|if you (?:have )?received (?:this|the)(?: (?:e-?mail|message))?[^\n]*in error"
    r"|confidentiality (?:notice|disclaimer)\b)",
    re.IGNORECASE,
)
STANDALONE_BOILERPLATE = re.compile(
    r"^(?:sent from my (?:iphone|ipad|android|mobile)\b"
    r"|please (?:consider the environment|do not print this (?:e-?mail|message))\b)",
    re.IGNORECASE,
)
SIGNATURE_START = re.compile(
    r"^(?:--|regards|kind regards|best regards|best|thanks|thank you|sincerely"
    r"|cheers|cordialement)[,!\s]*$"
    r"|^[^|\n]{1,80}\|[^|\n]{1,100}\|[^|\n]{1,200}$"
    r"|^zen (?:orchestrator|studio|connect|insights|vault) admin,",
    re.IGNORECASE,
)
MESSAGE_HEADER = re.compile(
    r"^(?:on .+wrote:|le .+(?:écrit|ecrit)\s*:|[- ]*original message[- ]*"
    r"|[- ]*forwarded message[- ]*|begin forwarded message:)$",
    re.IGNORECASE,
)
TRANSPORT_HEADER = re.compile(r"^(?:from|to|cc|sent|date):\s", re.IGNORECASE)


@dataclass(frozen=True)
class TicketText:
    current: str
    quoted: str
    current_identity: str
    quoted_identity: str


def customer_text(body: str) -> TicketText:
    """Keep quote context and signatures separately from issue-classification text.

    A footer paragraph ends at a blank line or message boundary. Signature state
    ends at a quote-depth/message boundary, so a footer/signature in one message
    cannot suppress the next message's customer content. Dequoting leaves phrases
    unchanged, allowing extracted evidence to match the complete original source.
    """
    current: list[str] = []
    quoted: list[str] = []
    current_identity: list[str] = []
    quoted_identity: list[str] = []
    previous_depth = 0
    in_footer = False
    in_signature = False

    for raw_line in body.splitlines():
        prefix = re.match(r"^\s*(?:>\s*)+", raw_line)
        depth = prefix.group().count(">") if prefix else 0
        line = raw_line[prefix.end() :] if prefix else raw_line
        stripped = line.strip()
        if depth != previous_depth:
            in_footer = in_signature = False
        previous_depth = depth
        if MESSAGE_HEADER.match(stripped):
            in_footer = in_signature = False
            continue
        issues = quoted if depth else current
        identity = quoted_identity if depth else current_identity
        if not stripped:
            in_footer = False
            identity.append("")
            if not in_signature:
                issues.append("")
            continue
        if FOOTER_START.match(stripped):
            in_footer = True
            continue
        if in_footer or STANDALONE_BOILERPLATE.match(stripped):
            continue
        if TRANSPORT_HEADER.match(stripped):
            continue
        identity.append(line)
        if SIGNATURE_START.match(stripped):
            in_signature = True
        if not in_signature:
            issues.append(line)

    return TicketText(
        current="\n".join(current),
        quoted="\n".join(quoted),
        current_identity="\n".join(current_identity),
        quoted_identity="\n".join(quoted_identity),
    )
