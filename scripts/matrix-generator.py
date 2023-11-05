import subprocess
import json
import os
import yaml
import sys

def find_git_root():
    # Find the repository root
    result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError('Could not find Git repository root.')
    return result.stdout.strip()

def find_dockerfile_and_build_yaml(file_path):
    git_root = find_git_root()
    current_path = os.path.dirname(file_path)

    # print(f"current_path: {current_path} and root_path: {git_root}")
    while current_path and os.path.abspath(current_path) != git_root:
        dockerfile_path = os.path.join(current_path, 'Dockerfile')
        build_yaml_path = os.path.join(current_path, 'build.yaml')
        
        if os.path.isfile(dockerfile_path) and os.path.isfile(build_yaml_path):
            return dockerfile_path, build_yaml_path
        
        current_path = os.path.dirname(current_path)
    
    return None, None

def get_changed_dockerfiles():
    base_sha = os.environ.get('GH_BASE_SHA')
    commit_sha = os.environ.get('GITHUB_SHA')

    # if not base_sha or not commit_sha:
    #     print("Could not find GH_BASE_SHA or GITHUB_SHA environment variables, skipping matrix generation")
    #     return []
    
    command = ['git', 'diff', '--name-only', '--diff-filter=ACMRT', f'{base_sha}', f'{commit_sha}']
    # print(f"Running command {command}")
    
    result = subprocess.run(command, capture_output=True, text=True)
    changed_files = result.stdout.strip().split('\n')

    unique_directories = set()
    dockerfile_info = []

    if not changed_files or changed_files == ['']:
        # print("No files changed, skipping matrix generation")
        return dockerfile_info

    for file_path in changed_files:
        # print(f"Checking {file_path}")
        dockerfile_path, build_yaml_path = find_dockerfile_and_build_yaml(file_path)
        
        if dockerfile_path and build_yaml_path:
            # Get the directory of the Dockerfile
            dockerfile_dir = os.path.dirname(dockerfile_path)
            
            if dockerfile_dir not in unique_directories:
                unique_directories.add(dockerfile_dir)
                with open(build_yaml_path, 'r') as file:
                    build_info = yaml.safe_load(file)
                    dockerfile_info.append({
                        'context': dockerfile_dir,  # Change 'dockerfile' to 'context' to indicate directory
                        'name': build_info['name'],
                        'sign': build_info.get('sign', False),
                        'disabled': build_info.get('disabled', False),
                        'architecture': build_info.get('architecture', ['linux/amd64'])
                    })

    return dockerfile_info

def create_matrix(dockerfile_info):
    matrix_include = [info for info in dockerfile_info if not info['disabled']]
    return {'include': matrix_include}

def main():
    dockerfile_info = get_changed_dockerfiles()
    matrix = create_matrix(dockerfile_info)
    print(json.dumps(matrix))

if __name__ == "__main__":
    main()
