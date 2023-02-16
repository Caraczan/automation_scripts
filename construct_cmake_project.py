#!/usr/bin/python3

"""
# !================================================================================================!
# This is a "fork" of a Python script rewritten from a Bash script I have shared on the
# "Sublime Text" discord server. The original Python version is by 'https://gitlab.com/caraczan'.
#
# Script functions:
# - Generating a CMake project using an existing CMakeLists.txt in the current directory.
# - Generating a clangd LSP database.
# - Compiling the codebase.
# !================================================================================================!
"""

import sys, os, tempfile
import argparse as ap, subprocess as sp
from colorama import Fore

class DefaultValue:
	THREADS: int = 4
	BUILD: str = './build'

COMPILATION_DATABASE: str = 'compile_commands.json'
SCRIPT_VERSION: str = '1.1.3'


def main() -> int:
	# Getting cli arguments/options and parsing them
	args: ap.Namespace = create_option_parser().parse_args()
	
	# Ensuring the required tools exist before further processing
	res: None | str = find_required_tools(args)
	if res is not None:
		print(res)
		return 1
	
	try:
		try_construct_cmake_files(args.build)
	except sp.CalledProcessError:
		return 1
	
	if not args.not_update_clangd_db:
		try:
			compile_database()
		except (OSError, sp.CalledProcessError):
			return 1
	
	if args.compile:
		try:
			compile_cmake_project(args.threads)
		except (OSError, sp.CalledProcessError):
			return 1
	
	print('\nBuild files location:')
	print(f'>>> {Fore.GREEN}{os.getcwd()}{Fore.RESET}')
	return 0

def run_cmd(args: sp._CMD) -> sp.CompletedProcess:
	""" Equivalent to `subprocess.run(args, shell=True).check_returncode()`.
	"""
	res: sp.CompletedProcess = sp.run(args, shell=True)
	res.check_returncode()
	return res

def terminal_program_exists(programName: str) -> bool:
	""" Check if a terminal program exists.
	"""
	try:
		sp.check_output(f'command -v {programName}', shell=True)
	except sp.CalledProcessError:
		return False
	return True

def create_option_parser() -> ap.ArgumentParser:
	""" Process cli arguments using the argparse library.
	Adding options to `argparse` and returning an `ArgumentParser`.
	"""
	SCRIPT_NAME: str = sys.argv[0]
	
	PROGRAM_DESCRIPTION: str = (
f'''Python script to simplify {Fore.YELLOW}CMake{Fore.RESET} usage for C/C++ project construction.
The script stores the {Fore.YELLOW}CMake{Fore.RESET} files into a build directory and exports \
compilation commands for the clangd LSP.'''
	)
	
	PROGRAM_EPILOG: str = (
f'''To avoid using {Fore.YELLOW}python3{Fore.RESET} before every call, make the script executable.
        Add execution permission:
                {Fore.YELLOW}chmod +x {Fore.GREEN}{SCRIPT_NAME}{Fore.RESET}
        Remove execution permission:
                {Fore.YELLOW}chmod -x {Fore.GREEN}{SCRIPT_NAME}{Fore.RESET}'''
        )
	
	parser: ap.ArgumentParser = ap.ArgumentParser(
		prog=SCRIPT_NAME,
		description=PROGRAM_DESCRIPTION,
		epilog=PROGRAM_EPILOG,
		add_help=True,
		formatter_class=lambda prog: ap.RawTextHelpFormatter(prog, 8, 16, 100)
	)
	
	parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {SCRIPT_VERSION}')
	
	parser.add_argument('-b', '--build',
		type=str,
		default=DefaultValue.BUILD,
		required=False,
		help=(
			f'Choose a different build directory. '
			f'Default: {Fore.GREEN}\'{DefaultValue.BUILD}\'{Fore.RESET}'
		)
	)
	
	parser.add_argument('-c', '--compile',
		required=False,
		action='store_true',
		help=(
			f'Compile the project by calling '
			f'{Fore.YELLOW}cmake --build --parallel 4{Fore.RESET}'
		)
	)
	
	parser.add_argument('-t', '--threads',
		type=int,
		default=DefaultValue.THREADS,
		required=False,
		help=(
			f'Specify the number of threads to compile with when the '
			f'"-c" flag is specified. Default: {DefaultValue.THREADS}'
		)
	)
	
	parser.add_argument('--not_update_clangd_db',
		action='store_false',
		default=False,
		required=False,
		help=(
			f'{Fore.YELLOW}compdb{Fore.RESET} will not be used, and no '
			f'{Fore.GREEN}{COMPILATION_DATABASE}{Fore.RESET} will be generated.'
		)
	)
	
	return parser

def find_required_tools(args: ap.Namespace) -> None | str:
	"""Find the tools required for further processing.
	If not all required tools are found, an appropriate message for the user is returned.
	"""
	
	if not terminal_program_exists('cmake'):
		return 'Could not locate `cmake`. Aborting...'
	
	# Checking if `compdb` exists only if we need it
	if not args.not_update_clangd_db and not terminal_program_exists('compdb'):
		return (
			f'Could not locate {Fore.YELLOW}compdb{Fore.RESET}.\n'
			f'{Fore.YELLOW}compdb{Fore.RESET} is used to create a compilation '
			f'database for the purpose of providing better diagnostics'
		)

def try_construct_cmake_files(buildDirectory: str) -> None:
	"""Create target directory for build files and export compile commands for Clangd.
	Throws `subprocess.CalledProcessError` or `OSError` on failure.
	"""
	
	# Create a build directory and enter it
	run_cmd(f'mkdir -p {buildDirectory}')
	os.chdir(buildDirectory)
	
	# Generating project using a CMakeLists.txt file
	run_cmd('cmake ../CMakeLists.txt -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B./')

def compile_database() -> None:
	"""Use compdb to upgrade the `COMPILATION_DATABASE` file created by CMake.
	"""
	with tempfile.TemporaryDirectory() as tmp_dir:
		run_cmd(f'mv ./{COMPILATION_DATABASE} {tmp_dir}/{COMPILATION_DATABASE}')
		run_cmd(f'compdb -p {tmp_dir} list > "{COMPILATION_DATABASE}"')
		run_cmd(f'ls {tmp_dir}')
		run_cmd(f'rm -r {tmp_dir}')

def compile_cmake_project(threadCount: int) -> None:
	"""Compile a CMake project in parallel with `threadCount` threads.
	Throws `subprocess.CalledProcessError` on failure.
	"""
	run_cmd(f'cmake --build ./ --parallel {threadCount}')


if __name__ == "__main__":
	exit(main())
