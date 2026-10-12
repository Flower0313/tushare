# ADR 0005: Shared runtime optimization policy

Status: Accepted.

Bundle work is evidence-driven. Route and heavy-modal lazy loading are preferred; manual chunk rules are not added merely to lower a raw bundle number. Revisit when build warnings, measured first-load regression, or bundle analysis identifies a separable high-cost dependency.
