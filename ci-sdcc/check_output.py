#!/usr/bin/env python
"""Check that a workflow run wrote the expected IDSs, each with at least one time slice.

Usage: check_output.py <config_folder> <ids> [<ids> ...]

The output entry is read from <config_folder>/input_workflow.xml, the same way the workflow opens it.
"""
import os
import sys
import xml.etree.ElementTree as ET

import imas
from imas import ids_defs


def workflow_parameters(config_folder):
    root = ET.parse(os.path.join(config_folder, "input_workflow.xml")).getroot()
    return {child.tag: (child.text or "").strip() for child in root.find("workflow_parameters")}


def main(config_folder, ids_names):
    par = workflow_parameters(config_folder)
    user_or_path = os.getenv("USER") if par["output_user_or_path"] == "default" else par["output_user_or_path"]
    database = par["input_database"] if par["output_database"] == "default" else par["output_database"]
    backend = getattr(ids_defs, f"{par.get('output_backend', 'MDSPLUS')}_BACKEND")
    shot, run = int(par["shot_nr"]), int(par["run_out"])

    print(f"> Checking output {user_or_path} {database} shot={shot} run={run}")
    entry = imas.DBEntry(backend, database, shot, run, user_or_path)
    try:
        entry.open()
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR: cannot open output entry ({exc})")
        return 1

    failed = 0
    for name in ids_names:
        try:
            ids = entry.get(name)
            written = ids.ids_properties.homogeneous_time != ids_defs.EMPTY_INT
            n_time = len(ids.time) if written else 0
        except Exception as exc:  # noqa: BLE001 - report any read error as a failed check
            print(f"  {name}: ERROR while reading ({exc})")
            failed = 1
            continue
        if n_time > 0:
            print(f"  {name}: OK ({n_time} time slices)")
        else:
            print(f"  {name}: EMPTY")
            failed = 1
    entry.close()
    return failed


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2:]))
