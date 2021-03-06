import tarfile
import os.path
import subprocess
from hwctool import __version__ as version


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


if __name__ == "__main__":
    make_tarfile('pyu-data/new/HWCT-data', 'casting_html')
    subprocess.run(
        f'.\\.venv\\Scripts\\pyupdater.exe archive --name HWCT-data --version {version}', shell=True, check=True)
