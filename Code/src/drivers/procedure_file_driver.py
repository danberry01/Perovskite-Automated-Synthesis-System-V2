import os
import yaml
import logging

class ProcedureFile:
    def _resolve_open_path(self, path: str):
        if os.path.isabs(path):
            return path

        candidates = [
            path,
            os.path.normpath(os.path.join(os.path.dirname(__file__), '..', path)),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return path

    def _resolve_save_path(self, path: str):
        if not path.endswith(".yml"):
            path += ".yml"
        if os.path.isabs(path):
            return path
        return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', path))

    def Open(self, path: str):
        try:
            resolved_path = self._resolve_open_path(path)
            with open(resolved_path, 'r', encoding='utf-8') as input_file:
                config = yaml.safe_load(input_file)
                return config
        except FileNotFoundError as e:
            return None

    def Save(self, path: str, procedure):
        resolved_path = self._resolve_save_path(path)
        parent_dir = os.path.dirname(resolved_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(resolved_path, 'w', encoding='utf-8') as output_file:
            yaml.dump(procedure, output_file, default_flow_style=None, Dumper=ProcedureDumper)

class ProcedureDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(ProcedureDumper, self).increase_indent(flow, False)
    
