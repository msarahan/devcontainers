#!/usr/bin/env python3
"""
RAPIDS Build System - Complete Replacement for Bash Scripts

This completely replaces the bash-based build system with pure Python.
No templates, no generation, no fragile bash parsing.

Usage:
    rapids build [project] [options]
    rapids configure [project] [options]
    rapids clean [project] [options]
    rapids clone [project] [options]
    rapids install [project] [options]
    rapids list [options]
    rapids info [project]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Import our build system
sys.path.insert(0, str(Path(__file__).parent))
try:
    from rapids_build_system import ManifestLoader, BuildOrchestrator, Project
except ImportError:
    # Fall back to importing from same directory
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "rapids_build_system",
        Path(__file__).parent / "rapids-build-system.py"
    )
    rapids_build_system = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rapids_build_system)
    ManifestLoader = rapids_build_system.ManifestLoader
    BuildOrchestrator = rapids_build_system.BuildOrchestrator
    Project = rapids_build_system.Project


def get_manifest_path() -> Path:
    """Get manifest.yaml path"""
    # Check environment variable
    if 'RAPIDS_MANIFEST' in os.environ:
        return Path(os.environ['RAPIDS_MANIFEST'])
    
    # Try common locations
    candidates = [
        Path('/opt/rapids-build-utils/manifest.yaml'),
        Path.home() / '.config/rapids/manifest.yaml',
        Path(__file__).parent.parent / 'submodules/rapidsai/devcontainers-git/features/src/rapids-build-utils/opt/rapids-build-utils/manifest.yaml',
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    raise FileNotFoundError(
        "Could not find manifest.yaml. Set RAPIDS_MANIFEST environment variable."
    )


class RapidsCLI:
    """Main CLI interface"""
    
    def __init__(self):
        self.manifest_path = None
        self.manifest = None
        self.orchestrator = None
        self.projects = []
        self.project_names = []
    
    def _load_manifest(self):
        """Load manifest lazily when needed"""
        if self.manifest is None:
            self.manifest_path = get_manifest_path()
            self.manifest = ManifestLoader(self.manifest_path)
            self.orchestrator = BuildOrchestrator(self.manifest)
            self.projects = self.manifest.get_projects()
            self.project_names = [p.name for p in self.projects]
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser"""
        parser = argparse.ArgumentParser(
            description='RAPIDS Build System - Pure Python Implementation',
            epilog='No more bash. No more templates. Just Python.'
        )
        
        subparsers = parser.add_subparsers(dest='command', required=True)
        
        # Build command
        build_parser = subparsers.add_parser('build', help='Build projects')
        build_parser.add_argument(
            'project',
            nargs='?',
            default='all',
            help='Project to build (or "all", "all-cpp", "all-python")'
        )
        self._add_build_args(build_parser)
        
        # Configure command
        configure_parser = subparsers.add_parser('configure', help='Configure projects with CMake')
        configure_parser.add_argument(
            'project',
            nargs='?',
            default='all',
            help='Project to configure (or "all")'
        )
        self._add_configure_args(configure_parser)
        
        # Clean command
        clean_parser = subparsers.add_parser('clean', help='Clean build artifacts')
        clean_parser.add_argument(
            'project',
            nargs='?',
            default='all',
            help='Project to clean (or "all")'
        )
        self._add_clean_args(clean_parser)
        
        # Clone command
        clone_parser = subparsers.add_parser('clone', help='Clone repositories')
        clone_parser.add_argument(
            'project',
            nargs='?',
            default='all',
            help='Project to clone (or "all" for all projects)'
        )
        self._add_clone_args(clone_parser)
        
        # Install command
        install_parser = subparsers.add_parser('install', help='Install built projects')
        install_parser.add_argument(
            'project',
            nargs='?',
            default='all',
            help='Project to install (or "all")'
        )
        self._add_install_args(install_parser)
        
        # List command
        list_parser = subparsers.add_parser('list', help='List projects and components')
        list_parser.add_argument('--cpp', action='store_true', help='List only C++ libraries')
        list_parser.add_argument('--python', action='store_true', help='List only Python packages')
        list_parser.add_argument('--json', action='store_true', help='Output as JSON')
        list_parser.add_argument('project', nargs='?', help='Filter by project')
        
        # Info command
        info_parser = subparsers.add_parser('info', help='Show project information')
        info_parser.add_argument('project', help='Project name')
        info_parser.add_argument('--json', action='store_true', help='Output as JSON')
        
        return parser
    
    def _add_build_args(self, parser: argparse.ArgumentParser):
        """Add build command arguments"""
        parser.add_argument('-j', '--parallel', type=int, metavar='N', help='Parallel jobs')
        parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
        parser.add_argument('--clean', action='store_true', help='Clean before building')
        parser.add_argument('--tests', action='store_true', help='Build tests')
        parser.add_argument('--benchmarks', action='store_true', help='Build benchmarks')
        parser.add_argument('--cpp-only', action='store_true', help='Build only C++ components')
        parser.add_argument('--python-only', action='store_true', help='Build only Python components')
        parser.add_argument('--install', action='store_true', help='Install after building')
        parser.add_argument('--editable', action='store_true', help='Editable Python install')
        parser.add_argument('-G', '--generator', choices=['Ninja', 'Unix Makefiles'], help='CMake generator')
        parser.add_argument('-D', action='append', dest='defines', metavar='VAR=VALUE', help='CMake definitions')
        parser.add_argument('--keep-going', action='store_true', help='Continue on errors')
    
    def _add_configure_args(self, parser: argparse.ArgumentParser):
        """Add configure command arguments"""
        parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
        parser.add_argument('--clean', action='store_true', help='Clean before configuring')
        parser.add_argument('-G', '--generator', choices=['Ninja', 'Unix Makefiles'], default='Ninja', help='CMake generator')
        parser.add_argument('-D', action='append', dest='defines', metavar='VAR=VALUE', help='CMake definitions')
    
    def _add_clean_args(self, parser: argparse.ArgumentParser):
        """Add clean command arguments"""
        parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    def _add_clone_args(self, parser: argparse.ArgumentParser):
        """Add clone command arguments"""
        parser.add_argument('-j', '--parallel', type=int, metavar='N', 
                          default=1,
                          help='Number of parallel clone jobs (default: 1)')
        parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
        parser.add_argument('-q', '--quiet', action='store_true', help='Quiet output')
        parser.add_argument('--depth', type=int, metavar='N', help='Shallow clone depth')
        parser.add_argument('--single-branch', action='store_true', help='Clone single branch')
        parser.add_argument('--branch', metavar='BRANCH', help='Branch to clone')
        parser.add_argument('--force', action='store_true', help='Force re-clone')
        parser.add_argument('--keep-going', action='store_true', help='Continue on errors')
    
    def _add_install_args(self, parser: argparse.ArgumentParser):
        """Add install command arguments"""
        parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
        parser.add_argument('--prefix', metavar='PATH', help='Install prefix')
    
    def cmd_build(self, args: argparse.Namespace) -> int:
        """Handle build command"""
        self._load_manifest()
        
        build_args = {
            'parallel': args.parallel or int(os.environ.get('RAPIDS_JOBS', os.cpu_count() or 1)),
            'verbose': args.verbose,
            'clean': args.clean,
            'generator': args.generator or 'Ninja',
            'defines': args.defines or [],
            'cpp_only': args.cpp_only,
            'python_only': args.python_only,
            'install': args.install,
            'editable': args.editable,
            'keep_going': args.keep_going,
        }
        
        # Add test/benchmark flags as CMake defines
        if args.tests:
            build_args['defines'].append('BUILD_TESTS=ON')
        if args.benchmarks:
            build_args['defines'].append('BUILD_BENCHMARKS=ON')
        
        if args.project == 'all':
            return self.orchestrator.build_all(build_args)
        elif args.project == 'all-cpp':
            build_args['python_only'] = False
            build_args['cpp_only'] = True
            return self.orchestrator.build_all(build_args)
        elif args.project == 'all-python':
            build_args['cpp_only'] = False
            build_args['python_only'] = True
            return self.orchestrator.build_all(build_args)
        else:
            return self.orchestrator.build_project(args.project, build_args)
    
    def cmd_configure(self, args: argparse.Namespace) -> int:
        """Handle configure command"""
        self._load_manifest()
        
        config_args = {
            'verbose': args.verbose,
            'clean': args.clean,
            'generator': args.generator,
            'defines': args.defines or [],
        }
        
        if args.project == 'all':
            for project in self.projects:
                if project.has_cpp():
                    ret = self.orchestrator.configure_project(project.name, config_args)
                    if ret != 0:
                        return ret
            return 0
        else:
            return self.orchestrator.configure_project(args.project, config_args)
    
    def cmd_clean(self, args: argparse.Namespace) -> int:
        """Handle clean command"""
        self._load_manifest()
        
        clean_args = {'verbose': args.verbose}
        
        if args.project == 'all':
            for project in self.projects:
                ret = self.orchestrator.clean_project(project.name, clean_args)
                if ret != 0:
                    return ret
            return 0
        else:
            return self.orchestrator.clean_project(args.project, clean_args)
    
    def cmd_clone(self, args: argparse.Namespace) -> int:
        """Handle clone command"""
        self._load_manifest()
        
        clone_args = {
            'parallel': args.parallel,
            'verbose': args.verbose,
            'quiet': args.quiet,
            'depth': args.depth,
            'single_branch': args.single_branch,
            'branch': args.branch,
            'force': args.force,
            'keep_going': args.keep_going,
        }
        
        if args.project == 'all':
            return self.orchestrator.clone_all(clone_args)
        else:
            return self.orchestrator.clone_project(args.project, clone_args)
    
    def cmd_install(self, args: argparse.Namespace) -> int:
        """Handle install command"""
        self._load_manifest()
        
        # For now, just call build with --install
        build_args = argparse.Namespace(
            project=args.project,
            parallel=int(os.environ.get('RAPIDS_JOBS', os.cpu_count() or 1)),
            verbose=args.verbose,
            clean=False,
            tests=False,
            benchmarks=False,
            cpp_only=False,
            python_only=False,
            install=True,
            editable=False,
            generator='Ninja',
            defines=[],
            keep_going=False,
        )
        return self.cmd_build(build_args)
    
    def cmd_list(self, args: argparse.Namespace) -> int:
        """Handle list command"""
        self._load_manifest()
        
        if args.json:
            data = {
                'projects': [],
                'cpp_libs': [],
                'python_libs': []
            }
            
            for project in self.projects:
                if args.project and project.name != args.project:
                    continue
                
                data['projects'].append(project.name)
                data['cpp_libs'].extend([lib['name'] for lib in project.cpp_libs])
                data['python_libs'].extend([lib['name'] for lib in project.python_libs])
            
            print(json.dumps(data, indent=2))
        else:
            if not (args.cpp or args.python):
                print("RAPIDS Projects:")
                for project in self.projects:
                    if args.project and project.name != args.project:
                        continue
                    print(f"  • {project.name}")
            else:
                if args.cpp:
                    print("C++ Libraries:")
                    for project in self.projects:
                        if args.project and project.name != args.project:
                            continue
                        for lib in project.cpp_libs:
                            print(f"  • {lib['name']}")
                
                if args.python:
                    print("Python Packages:")
                    for project in self.projects:
                        if args.project and project.name != args.project:
                            continue
                        for lib in project.python_libs:
                            print(f"  • {lib['name']}")
        
        return 0
    
    def cmd_info(self, args: argparse.Namespace) -> int:
        """Handle info command"""
        self._load_manifest()
        
        project = self.manifest.get_project(args.project)
        if not project:
            print(f"Error: Unknown project: {args.project}", file=sys.stderr)
            return 1
        
        if args.json:
            data = {
                'name': project.name,
                'path': str(project.path),
                'source_dir': str(project.source_dir),
                'git': project.git,
                'cpp_libs': project.cpp_libs,
                'python_libs': project.python_libs,
            }
            print(json.dumps(data, indent=2))
        else:
            print(f"Project: {project.name}")
            print(f"Path: {project.path}")
            print(f"Source: {project.source_dir}")
            print(f"Git: {project.git}")
            
            if project.cpp_libs:
                print("\nC++ Libraries:")
                for lib in project.cpp_libs:
                    print(f"  • {lib['name']}")
                    if lib.get('sub_dir'):
                        print(f"    Sub-directory: {lib['sub_dir']}")
                    if lib.get('depends'):
                        print(f"    Depends: {', '.join(lib['depends'])}")
            
            if project.python_libs:
                print("\nPython Packages:")
                for lib in project.python_libs:
                    print(f"  • {lib['name']}")
                    if lib.get('sub_dir'):
                        print(f"    Sub-directory: {lib['sub_dir']}")
                    if lib.get('depends'):
                        print(f"    Depends: {', '.join(lib['depends'])}")
        
        return 0
    
    def run(self) -> int:
        """Main entry point"""
        try:
            parser = self.create_parser()
            args = parser.parse_args()
            
            # Dispatch to command handler
            if args.command == 'build':
                return self.cmd_build(args)
            elif args.command == 'configure':
                return self.cmd_configure(args)
            elif args.command == 'clean':
                return self.cmd_clean(args)
            elif args.command == 'clone':
                return self.cmd_clone(args)
            elif args.command == 'install':
                return self.cmd_install(args)
            elif args.command == 'list':
                return self.cmd_list(args)
            elif args.command == 'info':
                return self.cmd_info(args)
            else:
                print(f"Unknown command: {args.command}", file=sys.stderr)
                return 1
        
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            print("\nSet RAPIDS_MANIFEST environment variable to manifest.yaml location", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\nInterrupted", file=sys.stderr)
            return 130
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1


def main():
    cli = RapidsCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main())


