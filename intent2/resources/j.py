from jinja2 import Environment, FileSystemLoader, StrictUndefined
import ruamel.yaml

def render_file(
    path,
    template,
    **kwargs
    ):
    env = Environment(
        loader=FileSystemLoader(path), undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True
    )
    t = env.get_template(template)
    return t.render(**kwargs)

def load_vars(
    filename,
    ):
    with open(filename, "r") as f:
        yml = ruamel.yaml.YAML(typ="safe")
        data = yml.load(f)
    return data


