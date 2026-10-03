# Extraction Workbench

A human review tool for structured extraction from customer support tickets.

The project is being developed in working increments. The supplied assignment is
preserved in [ASSIGNMENT.md](ASSIGNMENT.md); the original 150-ticket dataset is in
[data/tickets.jsonl](data/tickets.jsonl).

## Planned implementation

- Python/FastAPI backend with Pydantic validation and bounded background processing.
- React, Vite, and TypeScript frontend for selection, progress, and human review.
- Deterministic mock provider that runs without API keys and exercises retry failures.
- Field provenance, explicit uncertainty, and reviewed CSV export.

The assignment specifies Next.js App Router. React/Vite is a deliberate departure
requested for this implementation; it may affect assignment compliance.

Setup instructions will be added with the runnable services.
