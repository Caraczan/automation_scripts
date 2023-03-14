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


def main() -> int:
	# Getting cli arguments/options and parsing them
	args: ap.Namespace = create_option_parser().parse_args()
	
	# Ensuring the required tools exist before further processing
	res: None | str = find_required_tools(args)
	if res is not None:
		print(res)
		return 1
	
	try:
		try_construct_cmake_files(args.build, args.build_type)
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
	print(f'>>> {Fore.GREEN}{os.getcwd()}')
	return 0


def create_option_parser() -> ap.ArgumentParser:
	""" Process cli arguments using the argparse library

	Adding options to `argparse` and returning an `ArgumentParser`
	"""
	SCRIPT_NAME: str = sys.argv[0]

	PROGRAM_DESCRIPTION: str = '''
		Python script to simplify CMake usage for C++ project construction.
		The script stores the CMake files into a build directory and exports
		compile commands for the clangd LSP.
	'''

	PROGRAM_EPILOG: str = f'''
		Example usage: `python3 {SCRIPT_NAME} -c`.
		The command will run CMake, compile the codebase and generate a database
		('compile_commands.json' file) for the clangd LSP.
		The created build files are made relative to where you run the script from.
	'''

	parser: ap.ArgumentParser = ap.ArgumentParser(
		prog=SCRIPT_NAME,
		description=PROGRAM_DESCRIPTION,
		epilog=PROGRAM_EPILOG,
		add_help=True,
		formatter_class=lambda prog: ap.HelpFormatter(prog, 8, 16)
	)

	#parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.0.0')

	parser.add_argument('-b', '--build',
		type=str,
		default=DefaultValue.BUILD,
		required=False,
		help=f'Choose a different build directory. Default: \'{DefaultValue.BUILD}\'',
	)

	parser.add_argument('-c', '--compile',
		required=False,
		action='store_true',
		help='Compile the project by calling CMake --build --parallel 4'
	)

	parser.add_argument('-t', '--threads',
		type=int,
		default=DefaultValue.THREADS,
		required=False,
		help=f'''
			Specify the number of threads to compile with when the '-c' flag
			is specified. Default: {DefaultValue.THREADS}
		'''
	)

	parser.add_argument('--not_update_clangd_db',
		action='store_false',
		default=False,
		required=False,
		help='Disable use of `compdb` to upgrade the clangd database. Default: False'
	)

	parser.add_argument('--build_type',
		action='store',
		default='debug',
		required=False,
		choices=['debug', 'release'],
		help='Compile project with <debug|release> flag, Default: debug'
	)

	return parser

def terminal_program_exist(programName: str) -> bool:
	try:
		sp.check_output(f'command -v {programName}', shell=True)
	except sp.CalledProcessError:
		return False
	return True

def find_required_tools(args: ap.Namespace) -> None | str:
	"""Find the tools required for further processing.
	If not all required tools are found, an appropriate message for the user is returned.
	"""

	# Checking if `cmake` exists with program `command`
	if not terminal_program_exist('cmake'):
		return 'Could not locate `cmake`. Aborting...'

	# Checking if `compdb` exists with program `command`
	if not args.not_update_clangd_db and not terminal_program_exist('compdb'):
		return '''\
			Could not locate `compdb`.
			`compdb` is (in this case) used to update clangd-lsp
			database for the purpose of bringing better diagnostics \
		'''

def try_construct_cmake_files(buildDirectory: str, buildType: str) -> None:
	"""Create target directory for build files and export compile commands for Clangd.
	Throws `subprocess.CalledProcessError` or `OSError` on failure.
	"""

	# Create a build directory and enter it
	sp.run(f'mkdir -p {buildDirectory}', shell=True).check_returncode()
	os.chdir(buildDirectory)

	# Generating project using a CMakeLists.txt file
	sp.run(f'cmake ../CMakeLists.txt -DCMAKE_BUILD_TYPE={buildType.capitalize()} -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B./',
			   shell=True
		   ).check_returncode()

def compile_database() -> None:
	"""Use `compdb` to upgrade the `compile_commands.json` file created by CMake.
	"""
	with tempfile.TemporaryDirectory() as tmp_dir:
		sp.run(f'mv ./compile_commands.json {tmp_dir}/compile_commands.json',
			shell=True
		).check_returncode()
		
		sp.run(f'compdb -p {tmp_dir} list > "compile_commands.json"',
			shell=True
		).check_returncode()
		
		sp.run(f'ls {tmp_dir}', shell=True).check_returncode()
		sp.run(f'rm -r {tmp_dir}', shell=True).check_returncode()

def compile_cmake_project(threadCount: int) -> None:
	"""Compile a CMake project in parallel with `threadCount` threads.
	Throws `subprocess.CalledProcessError` on failure.
	"""
	sp.run(f'cmake --build ./ --parallel ${threadCount}',
		shell=True
	).check_returncode()


if __name__ == "__main__":
	exit(main())
