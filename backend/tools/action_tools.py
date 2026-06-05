import logging
from typing import Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from backend.tools.query_tools import get_client_and_portal

logger = logging.getLogger("zoho_chatbot")

@tool
async def create_task_tool(
    project_id: str,
    name: str,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    config: RunnableConfig = None
) -> str:
    """
    Creates a new task in a project.
    Arguments:
    - project_id: Unique ID of the project.
    - name: Name of the task (required).
    - assignee: Optional Zoho user ID of the assignee.
    - due_date: Optional end date string (MM-DD-YYYY).
    - priority: Optional priority ('low', 'medium', 'high').
    """
    try:
        zoho_client, portal_id = await get_client_and_portal(config)
        task = await zoho_client.create_task(
            portal_id=portal_id,
            project_id=project_id,
            name=name,
            assignee=assignee,
            due_date=due_date,
            priority=priority
        )
        return (
            f"Success: Task **{task.get('name')}** has been created with ID `{task.get('id')}` "
            f"in project `{project_id}`."
        )
    except Exception as e:
        logger.error(f"Error in create_task_tool: {e}")
        return f"Error creating task: {str(e)}"


@tool
async def update_task_tool(
    project_id: str,
    task_id: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    config: RunnableConfig = None
) -> str:
    """
    Updates an existing task's parameters in a project.
    Arguments:
    - project_id: Unique ID of the project.
    - task_id: Unique ID of the task.
    - status: Optional status name/value ('open', 'closed' or custom status ID).
    - assignee: Optional Zoho user ID of the assignee.
    - due_date: Optional end date string (MM-DD-YYYY).
    - priority: Optional priority ('low', 'medium', 'high').
    """
    try:
        zoho_client, portal_id = await get_client_and_portal(config)
        
        # Build update fields dictionary
        update_fields = {}
        if status is not None:
            update_fields["status"] = status
        if assignee is not None:
            update_fields["assignee"] = assignee
        if due_date is not None:
            update_fields["due_date"] = due_date
        if priority is not None:
            update_fields["priority"] = priority

        task = await zoho_client.update_task(
            portal_id=portal_id,
            project_id=project_id,
            task_id=task_id,
            **update_fields
        )
        return f"Success: Task `{task_id}` (**{task.get('name')}**) has been updated."
    except Exception as e:
        logger.error(f"Error in update_task_tool: {e}")
        return f"Error updating task: {str(e)}"


@tool
async def delete_task_tool(
    project_id: str,
    task_id: str,
    config: RunnableConfig = None
) -> str:
    """
    Deletes a task from a project.
    Arguments:
    - project_id: Unique ID of the project.
    - task_id: Unique ID of the task.
    """
    try:
        zoho_client, portal_id = await get_client_and_portal(config)
        await zoho_client.delete_task(
            portal_id=portal_id,
            project_id=project_id,
            task_id=task_id
        )
        return f"Success: Task `{task_id}` has been deleted from project `{project_id}`."
    except Exception as e:
        logger.error(f"Error in delete_task_tool: {e}")
        return f"Error deleting task: {str(e)}"
