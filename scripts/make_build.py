import re
import os
import shutil
import zipfile
from sys import exit
from argparse import ArgumentParser, ArgumentTypeError

SOURCE_DIR = "C:/dev/remember_installation_choices"
SOURCES = [
    "__init__.py",
]
BASE_BUILD_DIR = os.path.join(SOURCE_DIR, "builds")

class Version():
    def __init__(self, version_string: str):
        pattern = r"^(\d+)\.(\d+)\.(\d+)$"
        match = re.match(pattern, version_string)
        if not match:
            raise ArgumentTypeError(f"Invalid version format: '{version_string}'. Expected format is X.Y.Z.")
        
        major, minor, patch = match.groups()
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

def version_parser(version_string: str) -> Version:
    return Version(version_string)

def update_version_in_init_py(init_py_path: str, version: Version) -> None:
    with open(init_py_path, 'r+') as file:
        content = file.readlines()
        in_version_block = False
    
        for i, line in enumerate(content):
            if '# VERSION_BEGIN' in line.strip():
                in_version_block = True
            elif '# VERSION_END' in line.strip() and in_version_block:
                in_version_block = False
            elif in_version_block:
                # replaces everything between leading spaces and trailing spaces (including newlines)
                content[i] = re.sub(
                    r"(^\s*)(.*?)(\s*$)",
                    lambda m: (
                        m.group(1) +
                        f"return mobase.VersionInfo({version.major}, {version.minor}, {version.patch}, 0)" +
                        m.group(3)
                    ),
                    line
                )

        file.seek(0)
        file.writelines(content)
        file.truncate() # Make sure to truncate if the new content is shorter than the original

def zip_directory(zip_filename: str, directory_to_zip: str) -> None:
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(directory_to_zip):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                zipf.write(file_path, os.path.relpath(file_path, directory_to_zip))

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('version', type=version_parser)
    parser.add_argument('--allow-overwrite', action='store_true', help='Allow overwriting of existing files')
    args = parser.parse_args()

    print(f"Version: {args.version}")

    build_dir = os.path.join(BASE_BUILD_DIR, str(args.version))
    print(f"Using build directory: {build_dir}")

    if os.path.exists(build_dir):
        if not args.allow_overwrite:
            print(f"Directory for version {args.version} already exists ({build_dir}).")
            print(f"Use '--allow-overwrite' to overwrite directory.")
            exit(1)
        shutil.rmtree(build_dir)

    output_dir = os.path.join(build_dir, "zip/remember_installation_choices")
    os.makedirs(output_dir)

    for file_name in SOURCES:
        src = os.path.join(SOURCE_DIR, file_name)
        dst = os.path.join(output_dir, file_name)
        shutil.copy(src, dst)

    update_version_in_init_py(os.path.join(output_dir, "__init__.py"), args.version)
    update_version_in_init_py(os.path.join(SOURCE_DIR, "__init__.py"), args.version)

    zip_path = os.path.join(build_dir, "remember_installation_choices.zip")
    zip_directory(zip_path, os.path.join(build_dir, "zip"))
    print(f"Created zip file with build: {zip_path}")
