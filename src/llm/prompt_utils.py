from os.path import join
import re


def load_prompt_template_from_file(path: str):
    with open(path, 'r') as prompt_file:
        template = prompt_file.read()
    return template


def load_input_variables_from_prompt_template(template: str):
    res = re.findall(r'\{.*?\}', template)
    return [input_var[1:-1] for input_var in res]
