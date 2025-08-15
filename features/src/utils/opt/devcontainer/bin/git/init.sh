#! /usr/bin/env bash

init_git_cli_config() {
    local -;
    set -euo pipefail;

    if ! test -f ~/.gitconfig; then
        if test -f ~/.gitconfig.default; then
            cp -a ~/.gitconfig{.default,};
        fi
    fi

    if test -n "${SSH_AUTH_SOCK:+x}" && command -V ssh-add >/dev/null 2>&1; then
        mkdir -p ~/.config/git;
        git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers;
        awk 'BEGIN {FS=" "; OFS=" "} {print $3, $1, $2}' <(ssh-add -L) > ~/.config/git/allowed_signers;
    fi

    if [ -z "$(git config --get pull.rebase)" ]; then
        git config --global pull.rebase false >/dev/null 2>&1 || true;
    fi

    if [ -z "$(git config --get codespaces-theme.hide-status)" ]; then
        git config --global codespaces-theme.hide-status    "${CODESPACES_THEME_HIDE_STATUS:-1}" >/dev/null 2>&1 || true;
    fi

    if [ -z "$(git config --get devcontainers-theme.show-dirty)" ]; then
        git config --global devcontainers-theme.show-dirty  "${DEVCONTAINERS_THEME_SHOW_DIRTY:-0}" >/dev/null 2>&1 || true;
    fi

    if [ -z "$(git config --get devcontainers-theme.hide-status)" ]; then
        git config --global devcontainers-theme.hide-status "${DEVCONTAINERS_THEME_HIDE_STATUS:-1}" >/dev/null 2>&1 || true;
    fi

    git config credential.https://${GITHUB_HOST:-github.com}.helper '!f() { sleep 1; echo "username=${GITHUB_USER:-oauth2}"; echo "password=${GITHUB_TOKEN:-}"; }; f'
    git config credential.https://${GITLAB_HOST:-gitlab.com}.helper '!f() { sleep 1; echo "username=${GITLAB_USER:-oauth2}"; echo "password=${GITLAB_TOKEN:-}"; }; f'
}

init_git_cli_config "$@";
