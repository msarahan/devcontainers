#!/usr/bin/env python3
"""
RAPIDS Build System - Complete Python Implementation

This completely replaces:
- submodules/rapidsai/devcontainers-git/src/rapids-build-utils  
- submodules/rapidsai/devcontainers-git/src/utils

No more bash argument parsing. No more template generation.
Just clean Python that works.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class Project:
    """Represents a project from manifest.yaml"""
    name: str
    path: str
    git: Dict[str, Any]
    cpp_libs: List[Dict[str, Any]] = field(default_factory=list)
    python_libs: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def source_dir(self) -> Path:
        return Path.home() / self.path
    
    def has_cpp(self) -> bool:
        return len(self.cpp_libs) > 0
    
    def has_python(self) -> bool:
        return len(self.python_libs) > 0


class ManifestLoader:
    """Loads and parses manifest.yaml"""
    
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        with open(manifest_path) as f:
            self.data = yaml.safe_load(f)
    
    def get_projects(self) -> List[Project]:
        """Get all projects from manifest"""
        projects = []
        for repo in self.data.get('repos', []):
            project = Project(
                name=repo['name'],
                path=repo['path'],
                git=repo.get('git', {}),
                cpp_libs=repo.get('cpp', []),
                python_libs=repo.get('python', [])
            )
            projects.append(project)
        return projects
    
    def get_project(self, name: str) -> Optional[Project]:
        """Get a specific project by name"""
        for project in self.get_projects():
            if project.name == name:
                return project
        return None


class CMakeBuilder:
    """Handles CMake configuration and building"""
    
    def __init__(self, project: Project, cpp_lib: Dict[str, Any]):
        self.project = project
        self.cpp_lib = cpp_lib
        self.lib_name = cpp_lib['name']
        self.sub_dir = cpp_lib.get('sub_dir', '')
        self.source_dir = project.source_dir / self.sub_dir if self.sub_dir else project.source_dir
        self.build_dir = self.source_dir / 'build'
    
    def configure(self, args: Dict[str, Any]) -> int:
        """Configure with CMake"""
        cmd = [
            'cmake',
            '-B', str(self.build_dir),
            '-S', str(self.source_dir),
        ]
        
        # Add generator
        if args.get('generator'):
            cmd.extend(['-G', args['generator']])
        
        # Add CMake definitions
        if args.get('defines'):
            for define in args['defines']:
                cmd.append(f'-D{define}')
        
        # Add library-specific cmake args
        lib_cmake_args = self.cpp_lib.get('args', {}).get('cmake', '')
        if lib_cmake_args:
            cmd.extend(lib_cmake_args.split())
        
        print(f"Configuring {self.lib_name}...")
        if args.get('verbose'):
            print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd)
        return result.returncode
    
    def build(self, args: Dict[str, Any]) -> int:
        """Build with CMake"""
        cmd = ['cmake', '--build', str(self.build_dir)]
        
        # Add parallel jobs
        if args.get('parallel'):
            cmd.extend(['-j', str(args['parallel'])])
        
        # Add verbose flag
        if args.get('verbose'):
            cmd.append('--verbose')
        
        # Add target
        if args.get('target'):
            cmd.extend(['--target', args['target']])
        
        print(f"Building {self.lib_name}...")
        if args.get('verbose'):
            print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd)
        return result.returncode
    
    def install(self, args: Dict[str, Any]) -> int:
        """Install with CMake"""
        cmd = ['cmake', '--install', str(self.build_dir)]
        
        if args.get('prefix'):
            cmd.extend(['--prefix', args['prefix']])
        
        print(f"Installing {self.lib_name}...")
        if args.get('verbose'):
            print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd)
        return result.returncode
    
    def clean(self, args: Dict[str, Any]) -> int:
        """Clean build directory"""
        if self.build_dir.exists():
            print(f"Cleaning {self.lib_name}...")
            import shutil
            shutil.rmtree(self.build_dir)
        return 0


class PythonBuilder:
    """Handles Python package building"""
    
    def __init__(self, project: Project, py_lib: Dict[str, Any]):
        self.project = project
        self.py_lib = py_lib
        self.lib_name = py_lib['name']
        self.sub_dir = py_lib.get('sub_dir', '')
        self.source_dir = project.source_dir / self.sub_dir if self.sub_dir else project.source_dir
    
    def build(self, args: Dict[str, Any]) -> int:
        """Build Python package"""
        cmd = ['python', '-m', 'pip', 'install']
        
        # Editable install
        if args.get('editable'):
            cmd.append('-e')
        
        # Add build args from manifest
        install_args = self.py_lib.get('args', {}).get('install', '')
        if install_args:
            cmd.extend(install_args.split())
        
        # Add the source directory
        cmd.append(str(self.source_dir))
        
        print(f"Building Python package {self.lib_name}...")
        if args.get('verbose'):
            print(f"Command: {' '.join(cmd)}")
            cmd.append('-v')
        
        result = subprocess.run(cmd)
        return result.returncode
    
    def wheel(self, args: Dict[str, Any]) -> int:
        """Build wheel"""
        cmd = ['python', '-m', 'pip', 'wheel']
        
        # Output directory
        if args.get('wheel_dir'):
            cmd.extend(['-w', args['wheel_dir']])
        
        cmd.append(str(self.source_dir))
        
        print(f"Building wheel for {self.lib_name}...")
        if args.get('verbose'):
            print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd)
        return result.returncode
    
    def clean(self, args: Dict[str, Any]) -> int:
        """Clean Python build artifacts"""
        import shutil
        patterns = ['build', 'dist', '*.egg-info', '__pycache__']
        
        for pattern in patterns:
            for path in self.source_dir.rglob(pattern):
                if path.is_dir():
                    print(f"Removing {path}")
                    shutil.rmtree(path)
        
        return 0


class GitOperations:
    """Handles git operations"""
    
    def __init__(self, project: Project):
        self.project = project
    
    def clone(self, args: Dict[str, Any]) -> int:
        """Clone repository"""
        if self.project.source_dir.exists():
            if not args.get('force'):
                print(f"{self.project.name} already cloned")
                return 0
        
        # Build clone URL
        git_info = self.project.git
        host = git_info.get('host', 'github')
        upstream = git_info.get('upstream', 'rapidsai')
        repo = git_info.get('repo', self.project.name)
        
        if host == 'github':
            url = f"https://github.com/{upstream}/{repo}.git"
        else:
            url = f"https://{host}/{upstream}/{repo}.git"
        
        cmd = ['git', 'clone']
        
        # Add options
        if args.get('depth'):
            cmd.extend(['--depth', str(args['depth'])])
        if args.get('single_branch'):
            cmd.append('--single-branch')
        if args.get('branch'):
            cmd.extend(['-b', args['branch']])
        elif git_info.get('tag'):
            cmd.extend(['-b', git_info['tag']])
        
        cmd.extend([url, str(self.project.source_dir)])
        
        print(f"Cloning {self.project.name}...")
        if args.get('verbose'):
            print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd)
        return result.returncode


class BuildOrchestrator:
    """Orchestrates build operations across projects"""
    
    def __init__(self, manifest: ManifestLoader):
        self.manifest = manifest
    
    def build_project(self, project_name: str, args: Dict[str, Any]) -> int:
        """Build a single project (C++ and Python)"""
        project = self.manifest.get_project(project_name)
        if not project:
            print(f"Error: Unknown project: {project_name}", file=sys.stderr)
            return 1
        
        # Build C++ libraries first
        if project.has_cpp() and not args.get('python_only'):
            for cpp_lib in project.cpp_libs:
                builder = CMakeBuilder(project, cpp_lib)
                
                # Configure if needed
                if not builder.build_dir.exists() or args.get('clean'):
                    if args.get('clean'):
                        builder.clean(args)
                    ret = builder.configure(args)
                    if ret != 0:
                        return ret
                
                # Build
                ret = builder.build(args)
                if ret != 0:
                    return ret
                
                # Install if requested
                if args.get('install'):
                    ret = builder.install(args)
                    if ret != 0:
                        return ret
        
        # Build Python packages
        if project.has_python() and not args.get('cpp_only'):
            for py_lib in project.python_libs:
                builder = PythonBuilder(project, py_lib)
                ret = builder.build(args)
                if ret != 0:
                    return ret
        
        return 0
    
    def build_all(self, args: Dict[str, Any]) -> int:
        """Build all projects"""
        projects = self.manifest.get_projects()
        
        for project in projects:
            print(f"\n{'='*60}")
            print(f"Building {project.name}")
            print(f"{'='*60}\n")
            
            ret = self.build_project(project.name, args)
            if ret != 0 and not args.get('keep_going'):
                return ret
        
        return 0
    
    def configure_project(self, project_name: str, args: Dict[str, Any]) -> int:
        """Configure a project"""
        project = self.manifest.get_project(project_name)
        if not project:
            print(f"Error: Unknown project: {project_name}", file=sys.stderr)
            return 1
        
        if not project.has_cpp():
            print(f"{project_name} has no C++ components")
            return 0
        
        for cpp_lib in project.cpp_libs:
            builder = CMakeBuilder(project, cpp_lib)
            if args.get('clean'):
                builder.clean(args)
            ret = builder.configure(args)
            if ret != 0:
                return ret
        
        return 0
    
    def clean_project(self, project_name: str, args: Dict[str, Any]) -> int:
        """Clean a project"""
        project = self.manifest.get_project(project_name)
        if not project:
            print(f"Error: Unknown project: {project_name}", file=sys.stderr)
            return 1
        
        # Clean C++
        if project.has_cpp():
            for cpp_lib in project.cpp_libs:
                builder = CMakeBuilder(project, cpp_lib)
                builder.clean(args)
        
        # Clean Python
        if project.has_python():
            for py_lib in project.python_libs:
                builder = PythonBuilder(project, py_lib)
                builder.clean(args)
        
        return 0
    
    def clone_project(self, project_name: str, args: Dict[str, Any]) -> int:
        """Clone a project"""
        project = self.manifest.get_project(project_name)
        if not project:
            print(f"Error: Unknown project: {project_name}", file=sys.stderr)
            return 1
        
        git_ops = GitOperations(project)
        return git_ops.clone(args)
    
    def clone_all(self, args: Dict[str, Any]) -> int:
        """Clone all projects"""
        projects = self.manifest.get_projects()
        
        for project in projects:
            print(f"\nCloning {project.name}...")
            git_ops = GitOperations(project)
            ret = git_ops.clone(args)
            if ret != 0 and not args.get('keep_going'):
                return ret
        
        return 0


def main():
    """Main entry point"""
    # This is the core implementation
    # The `rapids` CLI wraps this with argparse
    pass


if __name__ == '__main__':
    print("This is the core build system library.")
    print("Use 'rapids' command for the CLI interface.")
    sys.exit(1)

