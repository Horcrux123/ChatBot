import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from backend.config import settings

logger = logging.getLogger("zoho_chatbot")

class ZohoAPIError(Exception):
    """Custom exception raised for Zoho API response failures."""
    def __init__(self, message: str, status_code: int = 500, response_body: str = ""):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"{message} (Status: {status_code}, Response: {response_body})")


class ZohoClient:
    """
    Async Zoho Projects API Client.
    All methods run asynchronously using httpx.AsyncClient.
    """
    def __init__(self, access_token: str, portal_id: Optional[str] = None):
        self.access_token = access_token
        self.portal_id = portal_id
        self.headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Accept": "application/json"
        }

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Any:
        url = f"{settings.ZOHO_API_BASE.rstrip('/')}/{path.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    data=data,
                    json=json_data
                )
                
                # Check for errors
                if not (200 <= response.status_code < 300):
                    raise ZohoAPIError(
                        message=f"Zoho Projects API request to {path} failed.",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                
                # DELETE operations might return 204 or empty string
                if response.status_code == 204 or not response.text.strip():
                    return {}
                    
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP request to {url} encountered an error: {e}")
                raise ZohoAPIError(
                    message=f"Network error requesting Zoho Projects API: {str(e)}",
                    status_code=500
                )

    async def get_portals(self) -> List[Dict[str, Any]]:
        """GET /restapi/portals/"""
        result = await self._request("GET", "/portals/")
        return result.get("portals", [])

    async def list_projects(self, portal_id: str) -> List[Dict[str, Any]]:
        """GET /restapi/portal/{portal_id}/projects/"""
        result = await self._request("GET", f"/portal/{portal_id}/projects/")
        return result.get("projects", [])

    async def list_tasks(
        self,
        portal_id: str,
        project_id: str,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        GET /restapi/portal/{portal_id}/projects/{project_id}/tasks/
        Support optional query filters.
        """
        params = {}
        if status:
            # Zoho supports status: open, closed, or custom status ID
            params["status"] = status
        if assignee:
            # Zoho filter by task assignee/owner
            params["owner"] = assignee
        if due_date:
            # Zoho filter by end date
            params["due_date"] = due_date

        result = await self._request("GET", f"/portal/{portal_id}/projects/{project_id}/tasks/", params=params)
        return result.get("tasks", [])

    async def get_task_details(self, portal_id: str, project_id: str, task_id: str) -> Dict[str, Any]:
        """GET /restapi/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/"""
        result = await self._request("GET", f"/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/")
        tasks = result.get("tasks", [])
        if not tasks:
            raise ZohoAPIError(f"Task with ID {task_id} not found.", status_code=404)
        return tasks[0]

    async def create_task(
        self,
        portal_id: str,
        project_id: str,
        name: str,
        assignee: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        POST /restapi/portal/{portal_id}/projects/{project_id}/tasks/
        Zoho Projects API expects form parameters (application/x-www-form-urlencoded).
        """
        data = {"name": name}
        if assignee:
            # Zoho uses 'person_responsible' for assignee ID
            data["person_responsible"] = assignee
        if due_date:
            # Zoho expects end date format: MM-DD-YYYY or similar. 
            # We will accept and forward string representation.
            data["end_date"] = due_date
        if priority:
            # low, medium, high
            data["priority"] = priority

        result = await self._request(
            "POST",
            f"/portal/{portal_id}/projects/{project_id}/tasks/",
            data=data
        )
        tasks = result.get("tasks", [])
        if not tasks:
            raise ZohoAPIError("Failed to create task, response empty.", status_code=500)
        return tasks[0]

    async def update_task(
        self,
        portal_id: str,
        project_id: str,
        task_id: str,
        **fields
    ) -> Dict[str, Any]:
        """
        PUT /restapi/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/
        Zoho Projects API expects form parameters for update.
        """
        data = {}
        for key, value in fields.items():
            if value is not None:
                if key == "assignee":
                    data["person_responsible"] = value
                elif key == "due_date":
                    data["end_date"] = value
                else:
                    data[key] = value

        if not data:
            # Nothing to update, return current details
            return await self.get_task_details(portal_id, project_id, task_id)

        result = await self._request(
            "PUT",
            f"/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/",
            data=data
        )
        tasks = result.get("tasks", [])
        if not tasks:
            raise ZohoAPIError(f"Failed to update task {task_id}, response empty.", status_code=500)
        return tasks[0]

    async def delete_task(self, portal_id: str, project_id: str, task_id: str) -> bool:
        """DELETE /restapi/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/"""
        await self._request(
            "DELETE",
            f"/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/"
        )
        return True

    async def list_project_members(self, portal_id: str, project_id: str) -> List[Dict[str, Any]]:
        """GET /restapi/portal/{portal_id}/projects/{project_id}/users/"""
        result = await self._request("GET", f"/portal/{portal_id}/projects/{project_id}/users/")
        return result.get("users", [])

    async def get_task_utilisation(self, portal_id: str, project_id: str) -> Dict[str, Any]:
        """
        Call list_tasks + list_project_members, then compute:
        - tasks_per_member: {member_name: count}
        - overdue_per_member: {member_name: count}
        - Return summary dict
        """
        tasks = await self.list_tasks(portal_id, project_id)
        members = await self.list_project_members(portal_id, project_id)

        # Create mapping of member ID to name
        # Also initialize data counters
        member_map = {str(m["id"]): m["name"] for m in members}
        member_map["Unassigned"] = "Unassigned"

        tasks_per_member = {name: 0 for name in member_map.values()}
        overdue_per_member = {name: 0 for name in member_map.values()}
        
        current_time = datetime.now(timezone.utc)

        for task in tasks:
            # Find assignee(s)
            # Zoho might return 'details' or 'person_responsible' fields
            # Let's inspect person_responsible or owners/assignees
            resp = task.get("person_responsible")
            
            # Find the name
            name = "Unassigned"
            if resp:
                # person_responsible might be a dict or a string ID
                resp_id = None
                if isinstance(resp, dict):
                    resp_id = str(resp.get("id", ""))
                else:
                    resp_id = str(resp)
                
                name = member_map.get(resp_id, "Unknown Member")

            if name not in tasks_per_member:
                tasks_per_member[name] = 0
            tasks_per_member[name] += 1

            # Check if overdue
            # Is task open?
            # In Zoho open status are typical or there is a boolean/string flag
            status_info = task.get("status", {})
            is_completed = False
            if isinstance(status_info, dict):
                is_completed = status_info.get("type") == "closed" or status_info.get("name", "").lower() in ["closed", "completed"]
            
            # end_date
            end_date_str = task.get("end_date") # Format MM-DD-YYYY or similar
            if end_date_str and not is_completed:
                try:
                    # Let's try to parse the end_date. Zoho returns it as "MM-DD-YYYY" or epoch millisecond.
                    # If it's a digit string, treat as ms timestamp
                    if end_date_str.isdigit():
                        end_date = datetime.fromtimestamp(int(end_date_str) / 1000, tz=timezone.utc)
                    else:
                        # Attempt to parse MM-DD-YYYY
                        end_date = datetime.strptime(end_date_str, "%m-%d-%Y").replace(tzinfo=timezone.utc)
                    
                    if current_time > end_date:
                        if name not in overdue_per_member:
                            overdue_per_member[name] = 0
                        overdue_per_member[name] += 1
                except Exception as e:
                    logger.warning(f"Could not parse task end_date '{end_date_str}': {e}")
                    pass

        return {
            "tasks_per_member": tasks_per_member,
            "overdue_per_member": overdue_per_member,
            "total_tasks": len(tasks),
            "total_members": len(members)
        }
