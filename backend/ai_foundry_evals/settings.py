"""Settings for Azure AI Foundry evaluation.

Read from environment variables so the package stays usable without modifying
the existing `src.config.settings` (which is OpenAI-direct).

Required:
- AZURE_AI_PROJECT_ENDPOINT — e.g. https://<account>.services.ai.azure.com/api/projects/<project>
- AZURE_AI_MODEL_DEPLOYMENT_NAME — judge model deployment, e.g. gpt-5-mini

Required only for simulators (AdversarialSimulator, Direct/Indirect attack):
- AZURE_AI_SUBSCRIPTION_ID
- AZURE_AI_RESOURCE_GROUP
- AZURE_AI_PROJECT_NAME
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FoundrySettings:
    project_endpoint: str
    model_deployment: str
    subscription_id: str | None
    resource_group: str | None
    project_name: str | None

    @property
    def azure_ai_project(self) -> dict[str, str]:
        if not (self.subscription_id and self.resource_group and self.project_name):
            raise RuntimeError(
                "Adversarial / jailbreak simulators require AZURE_AI_SUBSCRIPTION_ID, "
                "AZURE_AI_RESOURCE_GROUP, and AZURE_AI_PROJECT_NAME to be set."
            )
        return {
            "subscription_id": self.subscription_id,
            "resource_group_name": self.resource_group,
            "project_name": self.project_name,
        }


def load_settings() -> FoundrySettings:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    deployment = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    if not endpoint or not deployment:
        raise RuntimeError(
            "AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME must be set."
        )
    return FoundrySettings(
        project_endpoint=endpoint,
        model_deployment=deployment,
        subscription_id=os.environ.get("AZURE_AI_SUBSCRIPTION_ID"),
        resource_group=os.environ.get("AZURE_AI_RESOURCE_GROUP"),
        project_name=os.environ.get("AZURE_AI_PROJECT_NAME"),
    )
