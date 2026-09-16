import os
from dataclasses import dataclass
from typing import Any

import httpx


class FlowAdminConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class FlowAdminAPIError(RuntimeError):
    status_code: int
    message: str
    errors: tuple[dict[str, str], ...] = ()

    def __str__(self) -> str:
        return self.message


def is_flow_admin(auth_user_id: str) -> bool:
    configured = os.getenv("FLOW_ADMIN_AUTH_USER_IDS", "")
    allowed = {
        value.strip().lower()
        for value in configured.split(",")
        if value.strip()
    }
    return bool(allowed) and str(auth_user_id).strip().lower() in allowed


class ConversationFlowAdminClient:
    def _settings(self) -> tuple[str, str]:
        base_url = os.getenv("LUKA_BACKEND_URL", "").strip().rstrip("/")
        api_key = os.getenv("FLOW_ADMIN_API_KEY", "").strip()
        if not base_url or not api_key:
            raise FlowAdminConfigurationError(
                "La administración de flujos no está configurada."
            )
        if not base_url.startswith(("http://", "https://")):
            raise FlowAdminConfigurationError("LUKA_BACKEND_URL no es válida.")
        return base_url, api_key

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        base_url, api_key = self._settings()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method,
                    f"{base_url}{path}",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Accept": "application/json",
                    },
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise FlowAdminAPIError(
                503,
                "No se pudo contactar al backend de Luka.",
            ) from exc

        if response.is_success:
            return response.json()

        message = "El backend rechazó la operación."
        errors: tuple[dict[str, str], ...] = ()
        try:
            detail = response.json().get("detail")
            if isinstance(detail, str):
                message = detail
            elif isinstance(detail, dict):
                message = str(detail.get("message") or message)
                raw_errors = detail.get("errors")
                if isinstance(raw_errors, list):
                    errors = tuple(
                        {
                            "path": str(item.get("path") or "definition"),
                            "message": str(item.get("message") or "Error de validación"),
                        }
                        for item in raw_errors
                        if isinstance(item, dict)
                    )
        except (ValueError, AttributeError):
            pass
        raise FlowAdminAPIError(response.status_code, message, errors)

    async def contracts(self) -> dict[str, Any]:
        return await self._request("GET", "/admin/conversation-flows/contracts")

    async def list(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/admin/conversation-flows")

    async def get(self, flow_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/admin/conversation-flows/{flow_id}")

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/admin/conversation-flows",
            payload=payload,
        )

    async def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/admin/conversation-flows/validate",
            payload=payload,
        )

    async def save_draft(
        self,
        flow_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/admin/conversation-flows/{flow_id}/draft",
            payload=payload,
        )

    async def discard_draft(self, flow_id: str) -> dict[str, Any]:
        return await self._request(
            "DELETE",
            f"/admin/conversation-flows/{flow_id}/draft",
        )

    async def publish(self, flow_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/admin/conversation-flows/{flow_id}/publish",
        )

    async def archive(self, flow_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/admin/conversation-flows/{flow_id}/archive",
        )


flow_admin_client = ConversationFlowAdminClient()
