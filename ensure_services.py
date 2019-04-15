import os
from typing import Optional, Any

from nornir import InitNornir
from nornir.core.connections import Connections
from nornir.core.task import Result, Task
from nornir.plugins.functions.text import print_title, print_result

from bics_nornir.plugins.connections.ncclient import Ncclient
from bics_nornir.plugins.tasks.networking import nc
from bics_nornir.plugins.tasks.data import load_service_intents, download_configs, render_templates, load_merge_yaml
import bics_nornir.plugins.tasks.services

import ruamel.yaml

def ensure_services(
    task: Optional[Task] = None,
    intent_dir: str = None,
) -> None:

    for svc_id, attrs in task.host["service_intent"].items():
        svc_type = attrs.get("_service_type", "")
        svc_func = getattr(bics_nornir.plugins.tasks.services, svc_type) 
        if not callable(svc_func):
            raise Exception(f"No function associated with svc_type {svc_type}")
 
        r_vars = task.run(
            name = f"Enrich intent vars for {svc_type}(id:{svc_id})",
            task = svc_func,
            **attrs
        )

        r_render = task.run(
            name = f"Creating low-level configlet for {svc_type}(id:{svc_id})",
            task = render_templates,
            src_path = f"{intent_dir}/{svc_type}/templates",
            dst_path = f"{intent_dir}/{svc_type}/state",
            dst_prefix = svc_id,
            **r_vars.result
        )

    for dirpath, _, files in os.walk(f"{intent_dir}/{svc_type}/state"):
        for name in files:
            if not name.lower().endswith((".yml", ".yaml")):
                continue
            with open(os.path.join(dirpath, name), "r") as f:
                yml = ruamel.yaml.YAML(typ="safe")
                data = yml.load(f)
            target_scope = data.pop("_target_scope", "")
            if target_scope.upper().strip() != "HOST":
                raise ValueError(f"State file {name} in {dirpath} should have host-specific scope")
            target_host = data.pop("_target_host", "")
            if target_host == task.host.name:
                path = data["_path"]
                action = data.get("_action", None)
                dry_run = True
                if action == "enforce":
                    dry_run = False
                r = task.run(
                    name = f"Pushing {path}:{data.get('service_name')} - dry-run: {dry_run}",
                    task = nc.nc_configure,
                    dry_run = dry_run,
                    configuration = data,
                    path = path,
                    force = True 
                )      


def main():
    nr = InitNornir(
        config_file="nornir_config.yaml",
        core={
            'num_workers':10
        }
    )
    # register the ncclient connection plugin so that host-connections have access to it
    Connections.register("ncclient", Ncclient)

    nr2 = nr.filter(name='sr1.lab')

    print_title("Loading Service Intents")
    results = nr.run(
        task=load_service_intents, 
        name="Load Service Intents",
        directory="intent2/services/eline/vars"
        )
    print_result(results)

    print_title("Updating inventory host data (partial)")
    resources_to_load = set()
    for _, host in nr.inventory.hosts.items():
        resources_needed = host.get("rsc_to_populate", None)
        if resources_needed:
            for rsc in resources_needed:
                resources_to_load.add(rsc)
    results = nr.run(
        task=download_configs,
        name="Load relevant configs into Inventory",
        resources = resources_to_load
    )
    print_result(results)

    print_title("Ensuring Service Intents")
    results = nr.run(
        task = ensure_services,
        intent_dir = "intent2/services"
    )
    print_result(results)


if __name__ == "__main__":
    main()


        
