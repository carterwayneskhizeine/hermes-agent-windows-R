"""Reproduce the exact write_file flow hermes AI used."""
import os
os.chdir(r"D:\Code\hermes-agent-2026.4.16")

from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations

env = LocalEnvironment()
ops = ShellFileOperations(env)

print("env.cwd:", getattr(env, "cwd", None))
print("ops.cwd:", ops.cwd)

path = r"D:\Doc\_hermes_repro_\test.md"
print("Input path:", path)
print("Normalized:", ops._expand_path(path))

result = ops.write_file(path, "reproduce test\n")
print("Result:", result)

import pathlib
expected = pathlib.Path(r"D:\Doc\_hermes_repro_\test.md")
print("Expected file at D:\\Doc\\_hermes_repro_\\test.md exists:", expected.exists())

# Also check if junk got into cwd
junk = list(pathlib.Path.cwd().glob("D*"))
print("D* in cwd:", [str(j) for j in junk])
