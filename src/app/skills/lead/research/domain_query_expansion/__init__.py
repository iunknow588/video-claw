from __future__ import annotations


class DomainQueryExpansionSkill:
    skill_name = "lead.research.domain_query_expansion"

    def run(self, input_bundle: dict) -> dict:
        domain = input_bundle.get("domain", "")
        return {"expanded_queries": [domain, f"{domain} 热点", f"{domain} 爆款"]}

