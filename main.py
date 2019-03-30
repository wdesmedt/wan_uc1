from typing import Optional, Any

from nornir import InitNornir
from nornir.core.connections import Connections
from nornir.core.task import Result, Task
from nornir.plugins.functions.text import print_title, print_result

from bics_nornir.plugins.connections.ncclient import Ncclient
from bics_nornir.plugins.tasks.networking import nc
from bics_nornir.plugins.tasks.data import load_merge_yaml, render_templates

import ruamel

def validate_intent(
    task: Optional[Task] = None,
    intent_dir: str = None,
) -> None:

    r = task.run(
        name = "Load vars",
        task = load_merge_yaml,
        directory = "intent2/resources/vars"
    )
    task.host["vars"] = r.result

    r = task.run(
        name = "render templates",
        task = render_templates,
        src_path = "intent2/resources/templates",
        dst_path = "intent2/resources/data",
        **task.host["vars"]
    )

    r = task.run(
        name = "Load intent",
        task = load_merge_yaml,
        directory = f"intent2/resources/data/{task.host.name}"
#        directory = intent_dir,
    )    

    task.host["intent"] = r.result 

    for res_path, resource in task.host["intent"].items():
        dry_run = True
        if resource.get("_action", None):
            if resource["_action"].lower() == "enforce":
                dry_run = False
                
        r = task.run(
            name = f"Send {res_path} - dry-run: {dry_run}",
            task = nc.nc_configure,
            dry_run = dry_run,
            configuration = resource,
            path=res_path,
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

    results = nr.run(task=validate_intent, intent_dir="intents")
#    results = nr2.run(task=validate_intent, intent_dir="intents")

    print_title("Runbook to push intent")
    print_result(results)

if __name__ == "__main__":
    main()


        
