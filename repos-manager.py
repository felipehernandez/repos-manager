import os
import shutil
import subprocess
import sys

COLOR_DEFAULT = "\033[0m"
COLOR_BLACK = "\033[0;30m"
COLOR_RED = "\033[0;31m"
COLOR_GREEN = "\033[0;32m"
COLOR_YELLOW = "\033[0;33m"
COLOR_BLUE = "\033[0;34m"
COLOR_PINK = "\033[0;35m"
COLOR_CYAN = "\033[0;36m"
COLOR_WHITE = "\033[0;37m"

GIT_DIFF_NO_CHANGES = ''

SCRIPT_EXECUTION_FOLDER = os.getcwd()


# Model
class Repo:
    name: str
    url: str

    def __init__(self, name: str, base_url: str) -> None:
        self.name = name
        self.url = '{base_url}/{name}.git'.format(base_url=base_url, name=name)


class Folder:
    path: str
    repos: [Repo]

    def __init__(self, path: str, repos: [Repo]) -> None:
        self.path = path
        self.repos = repos


class Report:
    cloned = list()
    updated = list()
    with_uncommitted_changes = list()
    failed = list()


# System
class ConsoleOutput:
    """Formats and present messages"""

    @staticmethod
    def error(message):
        print("{}{}{}".format(COLOR_RED, message, COLOR_DEFAULT))

    @staticmethod
    def info(message):
        print("{}{}{}".format(COLOR_WHITE, message, COLOR_DEFAULT))

    @staticmethod
    def warn(message):
        print("{}{}{}".format(COLOR_PINK, message, COLOR_DEFAULT))

    @staticmethod
    def action(message):
        print("{}{}{}".format(COLOR_BLUE, message, COLOR_DEFAULT))

    @staticmethod
    def debug(message):
        print("{}{}{}".format(COLOR_BLACK, message, COLOR_DEFAULT))


class FileManager:
    """Group file logic"""

    @staticmethod
    def folder_exists(folder_path):
        return os.path.exists(folder_path)

    @staticmethod
    def create_folder(folder_path):
        if not FileManager.folder_exists(folder_path):
            os.makedirs(folder_path)

    @staticmethod
    def delete_folder(folder_name):
        shutil.rmtree(folder_name)

    @staticmethod
    def go_to_folder(folder_path):
        os.chdir(folder_path)


class GitManager:
    """Manages git actions"""

    @staticmethod
    def clone(base_folder, repo: Repo):
        ConsoleOutput.action('Clonning {} ...'.format(repo.url))
        try:
            subprocess.run(['git', 'clone', repo.url, '{}/{}'.format(base_folder, repo.name)],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)

            ConsoleOutput.action('Clone success {}'.format(repo.name))
            Report.cloned.append(repo.name)

        except subprocess.CalledProcessError as e:
            ConsoleOutput.error('Error cloning {}: {}'.format(repo.name, e))
            Report.failed.append(repo.name)

    @staticmethod
    def contains_uncommitted_changes(base_folder, repo_name):
        FileManager.go_to_folder('{}/{}'.format(base_folder, repo_name))
        try:
            result = subprocess.run(['git', 'diff-index', 'HEAD'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    check=True)

            if GIT_DIFF_NO_CHANGES != result.stdout.decode('utf-8'):
                ConsoleOutput.warn('Contains uncommitted changes {}'.format(repo_name))
                Report.with_uncommitted_changes.append(repo_name)
                result = True
            else:
                result = False

        except subprocess.CalledProcessError as e:
            ConsoleOutput.error('Error processing {}: {}'.format(repo_name, e))
            Report.failed.append(repo_name)
            result = True

        FileManager.go_to_folder(SCRIPT_EXECUTION_FOLDER)
        return result

    @staticmethod
    def checkout_master(base_folder, repo: Repo):
        FileManager.go_to_folder('{}/{}'.format(base_folder, repo.name))
        try:
            ConsoleOutput.action('Checking out master for {}'.format(repo.name))
            subprocess.run(['git', 'checkout', 'master'], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, check=True)

            ConsoleOutput.action('Pulling changes for {}'.format(repo.name))
            subprocess.run(['git', 'pull'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           check=True)

            ConsoleOutput.action('Up to date {}'.format(repo.name))
            Report.updated.append(repo.name)

        except subprocess.CalledProcessError as e:
            ConsoleOutput.error('Error processing {}: {}'.format(repo.name, e))
            Report.failed.append('{} : {}'.format(repo.name, e))

        FileManager.go_to_folder(SCRIPT_EXECUTION_FOLDER)


# Mappers
def map_file(raw_data: dict):
    return [Folder(raw_folder['folder'],
                   [Repo(repo_name, raw_folder['base'])
                    for repo_name in raw_folder['repos']])
            for raw_folder in raw_data]


# Execution
def load_dependencies():
    ConsoleOutput.info('Installing dependencies ...')
    ConsoleOutput.info('----------------------------------------------')
    os.system("pip install pyyaml")
    ConsoleOutput.info('----------------------------------------------')


def load_parameters():
    repos_file = sys.argv[1]
    ConsoleOutput.action('Selected file: {file}'.format(file=repos_file))
    return repos_file


def process_folder(folder: Folder, folder_current: int, folder_total: int):
    ConsoleOutput.info('Processing [{current}/{total}] {folder}'.format(folder=folder.path,
                                                                        current=folder_current,
                                                                        total=folder_total))
    repo_current = 1
    repo_total = len(folder.repos)
    for repo in folder.repos:
        process_repo(repo, folder.path, repo_current, repo_total, folder_current, folder_total)
        repo_current += 1


def process_repo(repo: Repo,
                 folder_path: str,
                 repo_current: int,
                 repo_total: int,
                 folder_current: int,
                 folder_total: int):
    ConsoleOutput.info(
        'Processing [{folder_current}/{folder_total}]:({repo_current}/{repo_total}) {repo}'.format(
            repo=repo.name,
            folder_current=folder_current,
            folder_total=folder_total,
            repo_current=repo_current,
            repo_total=repo_total))
    FileManager.create_folder(folder_path)
    # clone
    if not FileManager.folder_exists('{}/{}'.format(folder_path, repo.name)):
        GitManager.clone(folder_path, repo)

    # recreate repo
    elif not FileManager.folder_exists('{}/{}/.git'.format(folder_path, repo.name)):
        FileManager.delete_folder('{}/{}'.format(folder_path, repo.name))
        GitManager.clone(folder_path, repo)

    # checkout master
    elif not GitManager.contains_uncommitted_changes(folder_path, repo.name):
        GitManager.checkout_master(folder_path, repo)


def report_script_result():
    ConsoleOutput.info('----------------------------------------------')
    report_script_result_group('Cloned', Report.cloned, ConsoleOutput.info)
    report_script_result_group('Updated', Report.updated, ConsoleOutput.info)
    report_script_result_group('Dirty', Report.with_uncommitted_changes, ConsoleOutput.warn)
    report_script_result_group('Failed', Report.failed, ConsoleOutput.error)


def report_script_result_group(group_name, repos, logger):
    if repos.__len__() > 0:
        logger('{} repos:'.format(group_name))
        for repo in repos:
            logger('\t{}'.format(repo))


#######################################################
def main():
    ConsoleOutput.info('Repos script 5.0')
    load_dependencies()
    filename = load_parameters()
    with open(filename, 'r') as stream:
        import yaml

        data_loaded = yaml.safe_load(stream)
        folders = map_file(data_loaded)

        current = 1
        total_folders = len(folders)
        for folder in folders:
            process_folder(folder, current, total_folders)
            current += 1

        report_script_result()

if __name__ == '__main__':
    main()