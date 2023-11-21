import os
import shutil
from ddpui.models.org_user import Org
from ddpui.models.org import OrgPrefectBlock
from ddpui.ddpprefect import prefect_service
from ddpui.ddpprefect import DBTCORE, SHELLOPERATION
from ddpui.utils import secretsmanager


def delete_dbt_workspace(org: Org):
    """deletes the dbt workspace on disk as well as in prefect"""
    if org.dbt:
        dbt = org.dbt
        org.dbt = None
        org.save()
        if os.path.exists(dbt.project_dir):
            shutil.rmtree(dbt.project_dir)
        dbt.delete()

    for dbtblock in OrgPrefectBlock.objects.filter(org=org, block_type=DBTCORE):
        try:
            prefect_service.delete_dbt_core_block(dbtblock.block_id)
        except Exception:  # pylint:disable=broad-exception-caught
            pass
        dbtblock.delete()

    for shellblock in OrgPrefectBlock.objects.filter(
        org=org, block_type=SHELLOPERATION
    ):
        if shellblock.block_name.find("-git-pull") > -1:
            try:
                prefect_service.delete_shell_block(shellblock.block_id)
            except Exception:  # pylint:disable=broad-exception-caught
                pass
            shellblock.delete()

    secretsmanager.delete_github_token(org)
