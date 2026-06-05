import logging
from typing import Optional
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger("zoho_chatbot")

async def get_client_and_portal(config: RunnableConfig):
    """Utility to retrieve zoho_client and ensure portal_id is available."""
    zoho_client = config["configurable"]["zoho_client"]
    portal_id = config["configurable"].get("portal_id")
    if not portal_id:
        portals = await zoho_client.get_portals()
        if not portals:
            raise ValueError("No portals found for this user. Cannot perform operations.")
        portal_id = portals[0]["id"]
        # Update config/state context
        config["configurable"]["portal_id"] = portal_id
    return zoho_client, portal_id


@tool
async def list_projects_tool(input: str = "", config: RunnableConfig = None) -> str:
    """
    Lists all projects in the user's Zoho Projects workspace.
    Input parameter can be an empty string.
    """
    try:
        zoho_client, portal_id = await get_client_and_portal(config)
        projects = await zoho_client.list_projects(portal_id)
        if not projects:
            return "No projects were found in your workspace."
        
        lines = ["Here are the projects in your workspace:"]
        for p in projects:
            desc = f" - {p['description']}" if p.get("description") else ""
            lines.append(f"- **{p['name']}** (ID: `{p['id']}`){desc}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in list_projects_tool: {e}")
        return f"Error retrieving projects: {str(e)}"


@tool
async def list_tasks_tool(
    project_id: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    due_date: Optional[str] = None,
    config: RunnableConfig = None
) -> str:
    """
    Lists tasks inside a specific project.
    Arguments:
    - project_id: The unique ID of the project.
    - status: Optional status filter (e.g. 'open', 'closed').
    - assignee: Optional assignee ID.
    - due_date: Optional due date string filter (e.g. 'MM-DD-YYYY').
    """
    try:
        zoho_client, portal_id = await get_client_and_portal(config)
        tasks = await zoho_client.list_tasks(
            portal_id=portal_id,
            project_id=project_id,
            status=status,
            assignee=assignee,
            due_date=due_date
        )
        if not tasks:
            return f"No tasks found for project ID `{project_id}` matching criteria."

        lines = [f"Found {len(tasks)} tasks:"]
        for t in tasks:
            resp_info = "Unassigned"
            resp = t.get("person_responsible")
            if resp:
                resp_info = resp.get("name") if isinstance(resp, dict) else str(resp)

            status_name = "Unknown"
            stat = t.get("status")
            if stat:
                status_name = stat.get("name") if isinstance(stat, dict) else str(stat)

            due_info = f", Due: {t['end_date']}" if t.get("end_date") else ""
            priority_info = f", Priority: {t['priority']}" if t.get("priority") else ""
            
            lines.append(
                f"- **{t['name']}** (ID: `{t['id']}`)\n"
                f"  Status: {status_name} | Assigned to: {resp_info}{priority_info}{due_info}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in list_tasks_tool: {e}")
        return f"Error retrieving tasks: {str(e)}"


@tool
async def get_task_details_tool(
    project_id: str,
    task_id: str,
    config: RunnableConfig = None
) -> str:
    """
    Retrieves full details of a specific task within a project.
    Arguments:
    - project_id: The unique ID of the project.
    - task_id: The unique ID of the task.
    """
    try:
        zoho_client, portal_id = await get_client_and_portal(config)
        task = await zoho_client.get_task_details(portal_id, project_id, task_id)
        
        status_name = "Unknown"
        stat = task.get("status")
        if stat:
            status_name = stat.get("name") if isinstance(stat, dict) else str(stat)
            
        resp_name = "Unassigned"
        resp = task.get("person_responsible")
        if resp:
            resp_name = resp.get("name") if isinstance(resp, dict) else str(resp)
            
        lines = [
            f"### Task Details: **{task.get('name')}** (ID: `{task.get('id')}`)",
            f"- **Project ID**: {project_id}",
            f"- **Status**: {status_name}",
            f"- **Assignee**: {resp_name}",
            f"- **Priority**: {task.get('priority', 'None')}",
            f"- **Start Date**: {task.get('start_date', 'N/A')}",
            f"- **Due Date**: {task.get('end_date', 'N/A')}",
            f"- **Completed**: {task.get('completed', False)}",
            f"- **Description**: {task.get('description', 'No description provided.')}"
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in get_task_details_tool: {e}")
        return f"Error retrieving task details: {str(e)}"


@tool
async def list_project_members_tool(
    project_id: str,
    config: RunnableConfig = None
) -> str:
    """
    Lists all users/members of a specific project, along with their roles and email addresses.
    Arguments:
    - project_id: The unique ID of the project.
    """
    try:
        zoho_client, portal_id = await get_client_and_portal(config)
        members = await zoho_client.list_project_members(portal_id, project_id)
        if not members:
            return f"No members found for project ID `{project_id}`."

        lines = [f"Members of project `{project_id}`:"]
        for m in members:
            role = m.get("role", "member")
            email_info = f" ({m['email']})" if m.get("email") else ""
            lines.append(f"- **{m['name']}** - Role: {role}{email_info} | User ID: `{m['id']}`")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in list_project_members_tool: {e}")
        return f"Error retrieving project members: {str(e)}"


@tool
async def get_task_utilisation_tool(
    project_id: str,
    config: RunnableConfig = None
) -> str:
    """
    Calculates and returns the task load and overdue summaries for all project members.
    Arguments:
    - project_id: The unique ID of the project.
    """
    try:
        zoho_client, portal_id = await get_client_and_portal(config)
        summary = await zoho_client.get_task_utilisation(portal_id, project_id)
        
        lines = [
            f"### Task Utilisation Summary (Project ID: `{project_id}`)",
            f"Total Tasks: {summary['total_tasks']}",
            f"Total Members: {summary['total_members']}",
            "",
            "**Task Assignment Breakdown**:"
        ]
        
        tasks_per = summary["tasks_per_member"]
        overdue_per = summary["overdue_per_member"]
        
        # Merge keys
        all_members = set(tasks_per.keys()).union(overdue_per.keys())
        for member in sorted(all_members):
            tasks_count = tasks_per.get(member, 0)
            overdue_count = overdue_per.get(member, 0)
            overdue_str = f" (*{overdue_count} overdue*)" if overdue_count > 0 else ""
            lines.append(f"- **{member}**: {tasks_count} tasks{overdue_str}")
            
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in get_task_utilisation_tool: {e}")
        return f"Error calculating task utilisation: {str(e)}"
