#!/usr/bin/env bash
# Bash completion for the rapids command
#
# Installation:
#   source this file, or copy to /etc/bash_completion.d/rapids
#
# Usage:
#   rapids build <TAB>     # Shows project names
#   rapids conf<TAB>       # Completes to "configure"
#   rapids build rmm -<TAB> # Shows build options

_rapids_get_projects() {
    # Get project list from rapids command
    rapids list 2>/dev/null | grep '^  •' | sed 's/^  • //'
}

_rapids_get_cpp_libs() {
    rapids list --cpp 2>/dev/null | grep '^  •' | sed 's/^  • //'
}

_rapids_get_python_libs() {
    rapids list --python 2>/dev/null | grep '^  •' | sed 's/^  • //'
}

_rapids() {
    local cur prev words cword
    _init_completion || return
    
    local subcommands="build configure clean clone install list help"
    local common_opts="-h --help -v --verbose"
    
    # If we're at the first argument after 'rapids'
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=($(compgen -W "${subcommands}" -- "${cur}"))
        return 0
    fi
    
    local subcommand="${words[1]}"
    
    case "${subcommand}" in
        build)
            # If we're choosing the project
            if [[ $cword -eq 2 ]]; then
                local projects=$(_rapids_get_projects)
                COMPREPLY=($(compgen -W "${projects} all all-cpp all-python" -- "${cur}"))
                return 0
            fi
            
            # Options for build command
            case "${prev}" in
                -j|--parallel)
                    COMPREPLY=($(compgen -W "$(nproc)" -- "${cur}"))
                    return 0
                    ;;
                -G|--generator)
                    COMPREPLY=($(compgen -W "Ninja 'Unix Makefiles'" -- "${cur}"))
                    return 0
                    ;;
                -D)
                    # Common CMake definitions
                    local cmake_defs="BUILD_TESTS= BUILD_BENCHMARKS= BUILD_SHARED_LIBS= CMAKE_BUILD_TYPE="
                    COMPREPLY=($(compgen -W "${cmake_defs}" -- "${cur}"))
                    return 0
                    ;;
            esac
            
            local build_opts="-j --parallel -v --verbose --tests --benchmarks --clean -G --generator -D -h --help"
            COMPREPLY=($(compgen -W "${build_opts}" -- "${cur}"))
            return 0
            ;;
            
        configure)
            if [[ $cword -eq 2 ]]; then
                local projects=$(_rapids_get_projects)
                COMPREPLY=($(compgen -W "${projects} all" -- "${cur}"))
                return 0
            fi
            
            case "${prev}" in
                -G|--generator)
                    COMPREPLY=($(compgen -W "Ninja 'Unix Makefiles'" -- "${cur}"))
                    return 0
                    ;;
                -D)
                    local cmake_defs="BUILD_TESTS= BUILD_BENCHMARKS= BUILD_SHARED_LIBS= CMAKE_BUILD_TYPE="
                    COMPREPLY=($(compgen -W "${cmake_defs}" -- "${cur}"))
                    return 0
                    ;;
            esac
            
            local configure_opts="-G --generator -D --clean -v --verbose -h --help"
            COMPREPLY=($(compgen -W "${configure_opts}" -- "${cur}"))
            return 0
            ;;
            
        clean)
            if [[ $cword -eq 2 ]]; then
                local projects=$(_rapids_get_projects)
                COMPREPLY=($(compgen -W "${projects} all" -- "${cur}"))
                return 0
            fi
            
            case "${prev}" in
                -j|--parallel)
                    COMPREPLY=($(compgen -W "$(nproc)" -- "${cur}"))
                    return 0
                    ;;
            esac
            
            local clean_opts="-j --parallel -v --verbose -h --help"
            COMPREPLY=($(compgen -W "${clean_opts}" -- "${cur}"))
            return 0
            ;;
            
        clone)
            if [[ $cword -eq 2 ]]; then
                local projects=$(_rapids_get_projects)
                COMPREPLY=($(compgen -W "${projects} all" -- "${cur}"))
                return 0
            fi
            
            case "${prev}" in
                -j|--parallel)
                    COMPREPLY=($(compgen -W "$(nproc)" -- "${cur}"))
                    return 0
                    ;;
                --depth)
                    COMPREPLY=($(compgen -W "1 10 50" -- "${cur}"))
                    return 0
                    ;;
            esac
            
            local clone_opts="-j --parallel -q --quiet --depth -h --help"
            COMPREPLY=($(compgen -W "${clone_opts}" -- "${cur}"))
            return 0
            ;;
            
        list)
            local list_opts="--cpp --python --json -h --help"
            if [[ $cword -eq 2 ]] && [[ ${cur} != -* ]]; then
                local projects=$(_rapids_get_projects)
                COMPREPLY=($(compgen -W "${projects}" -- "${cur}"))
                return 0
            fi
            COMPREPLY=($(compgen -W "${list_opts}" -- "${cur}"))
            return 0
            ;;
            
        *)
            COMPREPLY=()
            return 0
            ;;
    esac
}

# Register the completion function
complete -F _rapids rapids

# Also provide completions if the script is called via python3
complete -F _rapids python3 -m rapids

