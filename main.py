from typing import Optional, Any

from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir.plugins.tasks.networking import nc
from nornir.plugins.tasks.data import load_yaml, load_intent
from nornir.plugins.functions.text import print_title, print_result

import ruamel

def validate_intent(
    task: Optional[Task] = None,
    intent_dir: str = None,
) -> Result:

    r = task.run(
        name = "Load intent",
        task = load_intent,
        directory = intent_dir,
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
    nr2 = nr.filter(name='sr1.lab')

#    results = nr2.run(task=validate_intent, intent_file="intent.yml")
    results = nr.run(task=validate_intent, intent_dir="intents")

    print_title("Runbook to push intent")
    print_result(results)

if __name__ == "__main__":
    main()


        
