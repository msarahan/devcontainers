#!/usr/bin/env bash

# Usage:
#  rapids-make-pip-env [OPTION]...
#
# Make a combined pip virtual environment for all repos.
#
# Boolean options:
#  -h,--help               Print this text.
#  -f,--force              Delete the existing pip venv and recreate it from scratch.
#  --pre                   Include pre-release and development versions. By default, pip only finds
#                          stable versions.
#  --no-pre                Don't install pre-release and development versions.
# @_include_bool_options rapids-make-pip-dependencies -h | tail -n+2 | head -n-3;
#
# @_include_value_options rapids-make-pip-dependencies -h;

# shellcheck disable=SC1091
. rapids-generate-docstring;

# Function to consolidate constraints for the same package
consolidate_constraints() {
    local -A package_constraints
    local -A package_lower_bounds
    local -A package_upper_bounds
    local -A package_excludes
    local -A package_prerelease_enabled
    
    # Read all constraints and group by package name
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Extract package name and version spec using regex
        # Handle package names with brackets like scikit-build-core[pyproject]
        if [[ "$line" =~ ^([^><=![:space:]]+(\[[^]]*\])?)[[:space:]]*(.*)$ ]]; then
            local package_name="${BASH_REMATCH[1]}"
            local version_spec="${BASH_REMATCH[3]}"
            package_name="${package_name%% }"  # trim trailing space
            version_spec="${version_spec## }"  # trim leading space
            
            # If no version spec, it's a package with no constraints
            if [[ -z "$version_spec" ]]; then
                # Just mark that this package exists
                package_constraints[$package_name]=""
                continue
            fi
            
            # Split by comma to handle multiple constraints in one line
            IFS=',' read -ra constraints <<< "$version_spec"
            for constraint_part in "${constraints[@]}"; do
                constraint_part="${constraint_part## }"  # trim leading space
                constraint_part="${constraint_part%% }"  # trim trailing space
                
                if [[ "$constraint_part" =~ ^([><=!]+)(.*)$ ]]; then
                    local operator="${BASH_REMATCH[1]}"
                    local version="${BASH_REMATCH[2]}"
                    
                    # Special handling for pre-release marker
                    if [[ "$operator" == ">=" && "$version" == "0.0.0a0" ]]; then
                        # This is the pre-release marker - don't combine with other constraints
                        package_prerelease_enabled[$package_name]=1
                        continue
                    fi
                    
                    case "$operator" in
                        ">=")
                            if [[ -z "${package_lower_bounds[$package_name]:-}" ]] || [[ "$version" > "${package_lower_bounds[$package_name]}" ]]; then
                                package_lower_bounds[$package_name]="$version"
                            fi
                            ;;
                        ">")
                            if [[ -z "${package_lower_bounds[$package_name]:-}" ]] || [[ "$version" > "${package_lower_bounds[$package_name]}" ]]; then
                                package_lower_bounds[$package_name]="$version"
                            fi
                            ;;
                        "<=")
                            if [[ -z "${package_upper_bounds[$package_name]:-}" ]] || [[ "$version" < "${package_upper_bounds[$package_name]}" ]]; then
                                package_upper_bounds[$package_name]="$version"
                            fi
                            ;;
                        "<")
                            if [[ -z "${package_upper_bounds[$package_name]:-}" ]] || [[ "$version" < "${package_upper_bounds[$package_name]}" ]]; then
                                package_upper_bounds[$package_name]="$version"
                            fi
                            ;;
                        "==")
                            # Exact version - set both bounds
                            package_lower_bounds[$package_name]="$version"
                            package_upper_bounds[$package_name]="$version"
                            ;;
                        "!=")
                            # Exclude version
                            if [[ -z "${package_excludes[$package_name]:-}" ]]; then
                                package_excludes[$package_name]="$version"
                            else
                                package_excludes[$package_name]="${package_excludes[$package_name]},$version"
                            fi
                            ;;
                    esac
                fi
            done
        fi
    done
    
    # Collect all unique package names
    local -A all_packages
    for package_name in "${!package_lower_bounds[@]}" "${!package_upper_bounds[@]}" "${!package_excludes[@]}" "${!package_constraints[@]}" "${!package_prerelease_enabled[@]}"; do
        all_packages[$package_name]=1
    done
    
    # Output consolidated constraints
    for package_name in "${!all_packages[@]}"; do
        local result=""
        
        # Check if lower and upper bounds are the same
        if [[ -n "${package_lower_bounds[$package_name]:-}" ]] && [[ -n "${package_upper_bounds[$package_name]:-}" ]]; then
            if [[ "${package_lower_bounds[$package_name]}" == "${package_upper_bounds[$package_name]}" ]]; then
                # Same bounds - use exact version
                result="==${package_lower_bounds[$package_name]}"
            else
                # Different bounds - use range
                result=">=${package_lower_bounds[$package_name]},<${package_upper_bounds[$package_name]}"
            fi
        elif [[ -n "${package_lower_bounds[$package_name]:-}" ]]; then
            # Only lower bound
            result=">=${package_lower_bounds[$package_name]}"
        elif [[ -n "${package_upper_bounds[$package_name]:-}" ]]; then
            # Only upper bound
            result="<${package_upper_bounds[$package_name]}"
        fi
        
        if [[ -n "${package_excludes[$package_name]:-}" ]]; then
            IFS=',' read -ra excludes <<< "${package_excludes[$package_name]}"
            for exclude in "${excludes[@]}"; do
                exclude="${exclude## }"  # trim leading space
                if [[ -n "$result" ]]; then
                    result="$result,!=${exclude}"
                else
                    result="!=${exclude}"
                fi
            done
        fi
        
        # Add pre-release marker if present
        if [[ -n "${package_prerelease_enabled[$package_name]:-}" ]]; then
            if [[ -n "$result" ]]; then
                result="$result,>=0.0.0a0"
            else
                result=">=0.0.0a0"
            fi
        fi
        
        if [[ -n "$result" ]]; then
            echo "$package_name$result"
        else
            echo "$package_name"
        fi
    done
}

make_pip_env() {
    local -;
    set -euo pipefail;

    eval "$(_parse_args --take '-f,--force --pre --no-pre' "${@:2}" <&0)";

    # shellcheck disable=SC1091
    . devcontainer-utils-debug-output 'rapids_build_utils_debug' 'make-pip-env';

    test ${#pre[@]} -eq 0 && pre=(--pre);

    if test -n "${no_pre:+x}"; then
        pre=();
    fi

    local env_name="${1}"; shift;
    local env_file_name="${env_name}.requirements.txt";

    # Remove the current virtual env if called with `-f,--force`
    if test -n "${f:+x}"; then
        rm -rf "${HOME}/.local/share/venvs/${env_name}" \
               "${HOME}/.local/share/venvs/${env_file_name}";
    fi

    local -r new_env_path="$(realpath -m "/tmp/${env_file_name}")";
    local -r old_env_path="$(realpath -m "${HOME}/.local/share/venvs/${env_file_name}")";

    # Create the python env without ninja.
    # ninja -$(ulimit -n) fails with `ninja: FATAL: pipe: Too many open files`.
    # This appears to have been fixed 13 years ago (https://github.com/ninja-build/ninja/issues/233),
    # so that fix needs to be integrated into the kitware pip ninja builds.
    rapids-make-pip-dependencies --exclude <(echo ninja) "${OPTS[@]}" | consolidate_constraints > "${new_env_path}";

    if test -f "${new_env_path}"; then

        # If the venv doesn't exist, make one
        if [ ! -d "${HOME}/.local/share/venvs/${env_name}" ]; then
            echo -e "Creating '${env_name}' virtual environment\n" 1>&2;
            echo -e "Requirements (${env_file_name}):\n" 1>&2;
            cat "${new_env_path}";
            echo "";

            python -m venv "${HOME}/.local/share/venvs/${env_name}";
            # shellcheck disable=SC1090
            . "${HOME}/.local/share/venvs/${env_name}/bin/activate";
            python -m pip install -U pip;
            python -m pip install "${pre[@]}" -U -r "${new_env_path}";
            python -m pip uninstall -y ninja >/dev/null 2>&1;
        # If the venv does exist but it's different from the generated one,
        # print the diff between the envs and update it
        elif ! diff -BNqw "${old_env_path}" "${new_env_path}" >/dev/null 2>&1; then
            echo -e "Updating '${env_name}' virtual environment\n" 1>&2;
            echo -e "Requirements (${env_file_name}):\n" 1>&2;

            # Print the diff to the console for debugging
            [ ! -f "${old_env_path}" ]                         \
             && cat "${new_env_path}"                          \
             || diff -BNyw "${old_env_path}" "${new_env_path}" \
             || true                                           \
             && echo "";

            # Update the current venv
            # shellcheck disable=SC1090
            . "${HOME}/.local/share/venvs/${env_name}/bin/activate";
            python -m pip install -U pip;
            python -m pip install "${pre[@]}" -U -r "${new_env_path}";
            python -m pip uninstall -y ninja >/dev/null 2>&1;
        fi

        cp -a "${new_env_path}" "${old_env_path}";
    fi
}

make_pip_env "${DEFAULT_VIRTUAL_ENV:-rapids}" "$@" <&0;

if test -f "${HOME}/.local/share/venvs/${DEFAULT_VIRTUAL_ENV:-rapids}/bin/activate"; then
    # shellcheck disable=SC1090
    . "${HOME}/.local/share/venvs/${DEFAULT_VIRTUAL_ENV:-rapids}/bin/activate";
fi
