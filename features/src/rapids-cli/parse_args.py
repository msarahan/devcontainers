#!/usr/bin/env python3
"""
Simple argument parser to replace args.sh

This script parses common arguments used by the build/CI scripts and
outputs bash variable declarations that can be eval'd by bash scripts.

Part of the rapids-cli package.

Usage in bash:
    eval "$(rapids-parse-args "$@")"
    # or if not installed:
    eval "$(python3 -m parse_args "$@")"

Replaces:
    - args.sh (eliminated)
    - Previously used by generate.sh and generate-all.sh (now deprecated)
"""

import argparse
import sys
import subprocess
from typing import List, Optional


def get_default_platform():
    """Get the default platform architecture."""
    try:
        result = subprocess.run(
            ["dpkg", "--print-architecture"],
            capture_output=True,
            text=True,
            check=True
        )
        arch = result.stdout.strip().split('-')[-1]
        return f"linux/{arch}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "linux/amd64"


def quote_bash_string(s: str) -> str:
    """Quote a string for bash."""
    return "'" + s.replace("'", "'\\''") + "'"


def format_bash_array(name: str, values: List[str]) -> str:
    """Format a bash array declaration."""
    if not values:
        return f"declare -a {name}=()"
    quoted = " ".join(quote_bash_string(v) for v in values)
    return f"declare -a {name}=({quoted})"


def format_bash_var(name: str, value: str) -> str:
    """Format a bash variable declaration."""
    return f"{name}={quote_bash_string(value)}"


def main():
    parser = argparse.ArgumentParser(
        description="Parse arguments for DLFW build scripts",
        add_help=False  # We'll handle help ourselves
    )
    
    # Boolean options
    parser.add_argument("-h", "--help", action="store_true",
                        help="Print help text")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Quiet output")
    parser.add_argument("--push", action="store_true",
                        help="Push the container after building")
    parser.add_argument("--no-cache", action="store_true",
                        help="Build with --no-cache")
    parser.add_argument("--clean", action="store_true",
                        help="Clean before building")
    parser.add_argument("--clean-bin", action="store_true",
                        help="Clean bin directory")
    parser.add_argument("--clean-src", action="store_true",
                        help="Clean source directory")
    parser.add_argument("--clean-env", action="store_true",
                        help="Clean environment")
    parser.add_argument("--clean-out", action="store_true",
                        help="Clean output directory")
    parser.add_argument("--vscode", action="store_true",
                        help="Launch in VSCode")
    parser.add_argument("--skip-dev-container-init-scripts", action="store_true",
                        help="Skip dev container init scripts")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Force operation")
    
    # Options with values
    parser.add_argument("--arrow", action="append", default=[],
                        help="Arrow version")
    parser.add_argument("--cuda", action="append", default=[],
                        help="CUDA version")
    parser.add_argument("--cupy", action="append", default=[],
                        help="CuPY version")
    parser.add_argument("--rapids", action="append", default=[],
                        help="RAPIDS version")
    parser.add_argument("--ubuntu", action="append", default=[],
                        help="Ubuntu version (default: 24.04)")
    parser.add_argument("--arch", action="append", default=[],
                        help="Architecture (amd64 or arm64)")
    parser.add_argument("--platform", action="append", default=[],
                        help="Platform (linux/amd64 or linux/arm64)")
    parser.add_argument("--branch_suffix", action="append", default=[],
                        help="Branch suffix (e.g., pb4)")
    parser.add_argument("--registry", action="append", default=[],
                        help="Container registry URL")
    parser.add_argument("--registry_path", action="append", default=[],
                        help="Container registry path")
    parser.add_argument("--slug", action="append", default=[],
                        help="Slug for container tag")
    parser.add_argument("--slug-out", action="append", default=[],
                        help="Output slug for container tag")
    parser.add_argument("--cache-from-slug", action="append", default=[],
                        help="Cache-from slug")
    parser.add_argument("--target", action="append", default=[],
                        help="Build target (dev|libs|runtime|test)")
    parser.add_argument("--remote-env", action="append", default=[],
                        help="Remote environment variables")
    parser.add_argument("--docker_mounts", action="append", default=[],
                        help="Docker mounts type (bind|volume)")
    parser.add_argument("--clone-parallel", action="append", default=[],
                        help="Number of parallel clone operations")
    parser.add_argument("--docker-path", action="append", default=[],
                        help="Path to docker executable")
    parser.add_argument("--update-remote-user-uid-default", action="append", default=[],
                        help="Update remote user UID default")
    
    # Catch remaining arguments
    parser.add_argument("REST", nargs="*", help="Remaining arguments")
    
    # Parse arguments
    args, unknown = parser.parse_known_args()
    
    # Handle help
    if args.help:
        print("exit 0")
        return 0
    
    # Set defaults
    if not args.ubuntu:
        args.ubuntu = ["24.04"]
    if not args.target:
        args.target = ["dev"]
    if not args.registry:
        args.registry = ["gitlab-master.nvidia.com:5005"]
    if not args.registry_path:
        args.registry_path = ["rapids/dlfw/rapids-dlfw"]
    if not args.platform:
        args.platform = [get_default_platform()]
    if not args.branch_suffix:
        args.branch_suffix = [""]
    if not args.docker_mounts:
        args.docker_mounts = ["bind"]
    if not args.clone_parallel:
        args.clone_parallel = ["1"]
    
    # Build output - bash variable declarations
    output = []
    
    # Simple string variables (boolean flags)
    if args.verbose:
        output.append(format_bash_var("verbose", "1"))
    if args.quiet:
        output.append(format_bash_var("quiet", "1"))
    if args.push:
        output.append(format_bash_var("push", "1"))
    if args.no_cache:
        output.append(format_bash_var("no_cache", "--no-cache"))
    if args.clean:
        output.append(format_bash_var("clean", "1"))
    if args.clean_bin:
        output.append(format_bash_var("clean_bin", "1"))
    if args.clean_src:
        output.append(format_bash_var("clean_src", "1"))
    if args.clean_env:
        output.append(format_bash_var("clean_env", "1"))
    if args.clean_out:
        output.append(format_bash_var("clean_out", "1"))
    if args.vscode:
        output.append(format_bash_var("vscode", "1"))
    if args.skip_dev_container_init_scripts:
        output.append(format_bash_var("skip_dev_container_init_scripts", "1"))
    if args.force:
        output.append(format_bash_var("force", "1"))
    
    # Array variables
    output.append(format_bash_array("arrow", args.arrow))
    output.append(format_bash_array("cuda", args.cuda))
    output.append(format_bash_array("cupy", args.cupy))
    output.append(format_bash_array("rapids", args.rapids))
    output.append(format_bash_array("ubuntu", args.ubuntu))
    output.append(format_bash_array("arch", args.arch))
    output.append(format_bash_array("platform", args.platform))
    output.append(format_bash_array("branch_suffix", args.branch_suffix))
    output.append(format_bash_array("registry", args.registry))
    output.append(format_bash_array("registry_path", args.registry_path))
    output.append(format_bash_array("slug", args.slug))
    output.append(format_bash_array("slug_out", args.slug_out))
    output.append(format_bash_array("cache_from_slug", args.cache_from_slug))
    output.append(format_bash_array("target", args.target))
    output.append(format_bash_array("remote_env", args.remote_env))
    output.append(format_bash_array("docker_mounts", args.docker_mounts))
    output.append(format_bash_array("clone_parallel", args.clone_parallel))
    output.append(format_bash_array("docker_path", args.docker_path))
    output.append(format_bash_array("update_remote_user_uid_default", args.update_remote_user_uid_default))
    
    # Handle REST and unknown args
    all_rest = args.REST + unknown
    output.append(format_bash_array("REST", all_rest))
    
    # Also export single values from arrays (for convenience)
    # Always set these even if empty to avoid "unbound variable" errors with set -u
    output.append(format_bash_var("cuda", args.cuda[0] if args.cuda else ""))
    output.append(format_bash_var("rapids", args.rapids[0] if args.rapids else ""))
    output.append(format_bash_var("ubuntu", args.ubuntu[0] if args.ubuntu else ""))
    output.append(format_bash_var("platform", args.platform[0] if args.platform else ""))
    output.append(format_bash_var("target", args.target[0] if args.target else ""))
    output.append(format_bash_var("registry", args.registry[0] if args.registry else ""))
    output.append(format_bash_var("registry_path", args.registry_path[0] if args.registry_path else ""))
    output.append(format_bash_var("branch_suffix", args.branch_suffix[0] if args.branch_suffix else ""))
    output.append(format_bash_var("docker_mounts", args.docker_mounts[0] if args.docker_mounts else ""))
    output.append(format_bash_var("clone_parallel", args.clone_parallel[0] if args.clone_parallel else ""))
    
    # Build OPTS array (for passing to other commands)
    opts = []
    if args.no_cache:
        opts.append("--no-cache")
    if args.push:
        opts.append("--push")
    output.append(format_bash_array("OPTS", opts))
    
    # Print all declarations
    print("\n".join(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())

