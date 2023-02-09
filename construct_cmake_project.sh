#!/usr/bin/bash

SCRIPT_NAME="$(basename "${0}")"
readonly SCRIPT_NAME
N_THREADS=4
readonly N_THREADS

Usage()
{
	printf 'Bash script to simplify CMake usage for C++ project construction.\n'
	printf 'The script stores the CMake files into a build directory and exports compile commands for the clangd LSP.\n'
	printf '\nUsage:\n'
	printf "\tbash $(tput setaf 2)%s$(tput sgr0) [options]\n" "${SCRIPT_NAME}"
	
	PrintOption()
	{
		printf '\t%s \n\t\t%s\n' "${1}" "${2}"
	}
	
	printf '\nOptions:\n'
	PrintOption '-h|--help' 'Print usage information and exit.'
	PrintOption "-b|--build=<$(tput setaf 2)path/to/build/folder$(tput sgr0)>" 'Choose a different build directory.'
	PrintOption '-c|--compile' "Compile the project by calling $(tput setaf 3)CMake --build --parallel ${N_THREADS}$(tput sgr0)."
	
	printf "\nTo avoid using $(tput setaf 3)%s$(tput sgr0) before every call, make the script executable.\n" "bash"
	printf '\tAdd execution permission:\n'
	printf "\t\t$(tput setaf 3)chmod +x $(tput setaf 2)%s$(tput sgr0)\n" "${SCRIPT_NAME}"
	printf '\tRemove execution permission:\n'
	printf "\t\t$(tput setaf 3)chmod -x $(tput setaf 2)%s$(tput sgr0)\n" "${SCRIPT_NAME}"
}


ProcessOpts()
{
	BUILD_DIR='./build'
	SHOULD_COMPILE=false
	
	local failure=false
	local arg
	for arg in "$@"; do
		case ${arg} in
			-h|--help)
				Usage
				exit 0
				;;
			-b=*|--build-dir=*)
				BUILD_DIR="${arg#*=}"
				if [[ ${BUILD_DIR} = '' ]]; then
					printf "Must provide a directory for "
					failure=true
					break
				fi
				shift # past argument=value
				;;
			-c|--compile)
				SHOULD_COMPILE=true
				shift # past argument
				;;
			
			-b|--build)
				printf "Must provide a directory for "
				failure=true
				break
				;;
			-c=*|--compile=*|-h=*|--help=*)
				printf "Arguments may not be passed for "
				failure=true
				break
				;;
			-*|*)
				printf "Unknown argument: "
				failure=true
				break
				;;
		esac
	done
	
	if [[ ${failure} = true ]]; then
		printf "$(tput setaf 3)%s$(tput sgr0)\n" "${arg}"
		printf "Run '$(tput setaf 2)%s$(tput sgr0) --help' for all supported options.\n" "${SCRIPT_NAME}"
		exit 1
	fi
	
	readonly SHOULD_COMPILE
	readonly BUILD_DIR
}



if [[ ! $(command -v cmake) ]]; then
	echo "Could not locate $(tput setaf 3)CMake$(tput sgr0). Aborting..."
	exit 1
fi

ProcessOpts "${@}"


mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}" || exit 1
cmake ../CMakeLists.txt -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -B./ || exit 1

HAS_COMPDB=$(command -v compdb); readonly HAS_COMPDB
if [[ ${HAS_COMPDB} ]]; then
	TMP_DIR=$(mktemp -d)
	mv "./compile_commands.json" "${TMP_DIR}/compile_commands.json"
	compdb -p "${TMP_DIR}" list > "compile_commands.json"
	rm -r "${TMP_DIR}"
fi

if [[ ${SHOULD_COMPILE} = true ]]; then
	cmake --build ./ --parallel ${N_THREADS} || exit 1
fi


printf '\nBuild files location:\n'
printf ">>> $(tput setaf 2)%s$(tput sgr0)\n" "$(pwd)"

if [[ ! ${HAS_COMPDB} ]]; then
	printf "Note: failed to create $(tput setaf 2)%s$(tput sgr0) - $(tput setaf 3)compdb$(tput sgr0) was not found.\n" 'compile_commands.json'
fi
