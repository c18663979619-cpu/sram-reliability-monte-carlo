"""Execute the narrative notebook with this Python environment's kernel."""
import os
from pathlib import Path
import sys
import tempfile
import json
import nbformat
from nbclient import NotebookClient

root = Path(__file__).resolve().parents[1]
path = root / "sram-reliability-monte-carlo.ipynb"
with tempfile.TemporaryDirectory() as tmp:
    kernels = Path(tmp) / "kernels" / "portfolio-python"
    kernels.mkdir(parents=True)
    (kernels / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Portfolio Python", "language": "python"}))
    os.environ["JUPYTER_PATH"] = tmp + os.pathsep + os.environ.get("JUPYTER_PATH", "")
    nb = nbformat.read(path, as_version=4)
    NotebookClient(nb, timeout=300, kernel_name="portfolio-python", resources={"metadata": {"path": str(root)}}).execute()
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbformat.write(nb, path)
print("Executed all notebook cells successfully.")
