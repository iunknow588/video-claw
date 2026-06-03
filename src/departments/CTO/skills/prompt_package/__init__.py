from __future__ import annotations


class PromptPackageSkill:
    skill_name = "lead.research_development.prompt_package"

    def run(self, input_bundle: dict) -> dict:
        prompt_bundle = {}
        for key, value in input_bundle.items():
            if key == "trace_id":
                prompt_bundle[key] = value
                continue
            if isinstance(value, str):
                normalized = value.strip()
                if normalized:
                    prompt_bundle[key] = normalized
            elif isinstance(value, list):
                normalized_list = []
                for item in value:
                    text = str(item or "").strip()
                    if text and text not in normalized_list:
                        normalized_list.append(text)
                prompt_bundle[key] = normalized_list
            else:
                prompt_bundle[key] = value
        return {"prompt_bundle": prompt_bundle}
