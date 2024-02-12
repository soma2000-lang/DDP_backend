import os
import shutil
from pathlib import Path

import yaml
from dotenv import load_dotenv
from ninja import NinjaAPI
from ninja.errors import ValidationError
from ninja.responses import Response
from pydantic.error_wrappers import ValidationError as PydanticValidationError

from ddpui import auth
from ddpui.ddpdbt.dbt_service import setup_local_dbt_workspace
from ddpui.models.org_user import OrgUser
from ddpui.schemas.org_task_schema import DbtProjectSchema
from ddpui.utils.custom_logger import CustomLogger

transformapi = NinjaAPI(urls_namespace="transform")

load_dotenv()

logger = CustomLogger("ddpui")


@transformapi.exception_handler(ValidationError)
def ninja_validation_error_handler(request, exc):  # pylint: disable=unused-argument
    """
    Handle any ninja validation errors raised in the apis
    These are raised during request payload validation
    exc.errors is correct
    """
    return Response({"detail": exc.errors}, status=422)


@transformapi.exception_handler(PydanticValidationError)
def pydantic_validation_error_handler(
    request, exc: PydanticValidationError
):  # pylint: disable=unused-argument
    """
    Handle any pydantic errors raised in the apis
    These are raised during response payload validation
    exc.errors() is correct
    """
    return Response({"detail": exc.errors()}, status=500)


@transformapi.exception_handler(Exception)
def ninja_default_error_handler(
    request, exc: Exception
):  # pylint: disable=unused-argument # skipcq PYL-W0613
    """Handle any other exception raised in the apis"""
    print(exc)
    return Response({"detail": "something went wrong"}, status=500)


@transformapi.exception_handler(ValueError)
def handle_value_error(request, exc):
    """
    Handle ValueError exceptions.
    """
    return Response({"detail": str(exc)}, status=400)


@transformapi.post("/dbt_project/", auth=auth.CanManagePipelines())
def create_dbt_project(request, payload: DbtProjectSchema):
    """
    Create a new dbt project.
    """
    orguser: OrgUser = request.orguser
    org = orguser.org

    project_dir = Path(os.getenv("CLIENTDBT_ROOT")) / org.slug
    project_dir.mkdir(parents=True, exist_ok=True)

    os.chdir(project_dir)

    # Call the post_dbt_workspace function
    try:
        result = setup_local_dbt_workspace(
            org, project_name="dbtrepo", default_schema=payload.default_schema
        )
    except Exception as e:
        raise Exception(f"post_dbt_workspace failed with error: {str(e)}")

    if result.returncode != 0:
        raise Exception(f"dbt init command failed with return code {result.returncode}")

    return {"message": f"Project {org.slug} created successfully"}


@transformapi.get("/dbt_project/{project_name}", auth=auth.CanManagePipelines())
def get_dbt_project(request, project_name: str):
    """
    Get the details of a dbt project.
    """
    orguser: OrgUser = request.orguser
    org = orguser.org

    project_dir = Path(os.getenv("CLIENTDBT_ROOT")) / org.slug
    if not project_dir.exists():
        raise ValueError(f"No projects found for organization {org.slug}.")

    existing_projects = [p.stem for p in project_dir.iterdir() if p.is_dir()]
    if project_name not in existing_projects:
        raise ValueError(f"A project called {project_name} does not exist.")

    profile_path = os.path.expanduser("~/.dbt/profiles.yml")
    if not os.path.exists(profile_path):
        raise ValueError("No dbt profiles found.")

    with open(profile_path, "r") as file:
        profiles = yaml.safe_load(file)

    if project_name not in profiles:
        raise ValueError(f"No profile found for project {project_name}.")

    project_profile = profiles[project_name]

    return {
        "message": f"Project {project_name} details retrieved successfully",
        "profile": project_profile,
    }


@transformapi.delete("/dbt_project/{project_name}", auth=auth.CanManagePipelines())
def delete_dbt_project(request, project_name: str):
    """
    Delete a dbt project.
    """
    orguser: OrgUser = request.orguser
    org = orguser.org

    project_dir = Path(os.getenv("CLIENTDBT_ROOT")) / org.slug
    if not project_dir.exists():
        raise ValueError(f"No projects found for organization {org.slug}.")

    existing_projects = [p.stem for p in project_dir.iterdir() if p.is_dir()]
    if project_name not in existing_projects:
        raise ValueError(f"A project called {project_name} does not exist.")

    profile_path = os.path.expanduser("~/.dbt/profiles.yml")
    if not os.path.exists(profile_path):
        raise ValueError("No dbt profiles found.")

    with open(profile_path, "r") as file:
        profiles = yaml.safe_load(file)

    if project_name not in profiles:
        raise ValueError(f"No profile found for project {project_name}.")

    shutil.rmtree(project_dir / project_name)

    del profiles[project_name]

    with open(profile_path, "w") as file:
        yaml.safe_dump(profiles, file)

    return {"message": f"Project {project_name} deleted successfully"}
