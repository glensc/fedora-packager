# fedpkg bash completion

have fedpkg &&
_fedpkg()
{
    COMPREPLY=()

    in_array()
    {
        local i
        for i in $2; do
            [[ $i = $1 ]] && return 0
        done
        return 1
    }

    _filedir_exclude_paths()
    {
        _filedir "$@"
        for ((i=0; i<=${#COMPREPLY[@]}; i++)); do
            [[ ${COMPREPLY[$i]} =~ /?\.git/? ]] && unset COMPREPLY[$i]
        done
    }

    local cur prev
    # _get_comp_words_by_ref is in bash-completion >= 1.2, which EL-5 lacks.
    if type _get_comp_words_by_ref &>/dev/null; then
        _get_comp_words_by_ref cur prev
    else
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
    fi
    
    # global options

    local options="-h --help -v -q"
    local options_value="-u --user --path"
    local commands="build chain-build ci clean clog clone co commit compile diff gimmespec giturl help \
    import install lint local mockbuild new new-sources patch prep push scratch-build sources srpm \
    switch-branch tag-request unused-patches update upload verrel"

    # parse main options and get command

    local command=
    local command_first=
    local path=

    local i w
    for (( i = 0; i < ${#COMP_WORDS[*]} - 1; i++ )); do
        w="${COMP_WORDS[$i]}"
        # option
        if [[ ${w:0:1} = - ]]; then
            if in_array "$w" "$options_value"; then
                ((i++))
                [[ "$w" = --path ]] && path="${COMP_WORDS[$i]}"
            fi
        # command
        elif in_array "$w" "$commands"; then
            command="$w"
            command_first=$((i+1))
            break
        fi
    done

    # complete base options

    if [[ -z $command ]]; then
        case "$prev" in
            --user|-u)
                ;;
            --path)
                _filedir_exclude_paths
                ;;
            *)
                COMPREPLY=( $(compgen -W "$options $options_value $commands" -- "$cur") )
                ;;
        esac

        return 0
    fi

    # parse command specific options

    local options=
    local options_target= options_arches= options_branch= options_string= options_file= options_srpm=
    local after= after_more=

    case $command in
        help|clog|gimmespec|giturl|lint|mockbuild|new|push|tag-request|unused-patches|update|verrel)
            ;;
        build)
            options="--nowait --background --skip-tag --scratch"
            options_target="--target"
            ;;
        chain-build)
            options="--nowait --background"
            options_target="--target"
            after="package"
            after_more=true
            ;;
        clean)
            options="--dry-run -n -x"
            ;;
        clone|co)
            options="--branches -B --anonymous -a"
            options_branch="-b"
            after="package"
            ;;
        commit|ci)
            options="--push -p"
            options_string="--message -m"
            options_file="--file -F"
            after="file"
            after_more=true
            ;;
        compile|install)
            options="--short-circuit"
            options_arch="--arch"
            ;;
        diff)
            options="--cached"
            after="file"
            after_more=true
            ;;
        import)
            options="--create -c"
            options_branch="--branch -b"
            after="srpm"
            ;;
        local)
            options="--md5"
            options_arch="--arch"
            ;;
        patch)
            options="--rediff"
            options_string="--suffix"
            ;;
        prep)
            options_arch="--arch"
            ;;
        scratch-build)
            options="--nowait --background --srpm"
            options_target="--target"
            options_arches="--arches"
            options_srpm="--srpm"
            ;;
        sources)
            options_dir="--outdir"
            ;;
        srpm)
            options="--md5"
            ;;
        switch-branch)
            options="--list -l"
            after="branch"
            ;;
        upload|new-sources)
            after="file"
            after_more=true
            ;;
    esac

    local all_options="-h --help $options"
    local all_options_value="$options_target $options_arches $options_branch $options_string $options_file $options_dir"

    # count non-option parametrs

    local i w
    local last_option=
    local after_counter=0
    for (( i = $command_first; i < ${#COMP_WORDS[*]} - 1; i++)); do
        w="${COMP_WORDS[$i]}"
        if [[ ${w:0:1} = - ]]; then
            if in_array "$w" "$all_options"; then
                last_option="$w"
                continue
            elif in_array "$w" "$all_options_value"; then
                last_option="$w"
                ((i++))
                continue
            fi
        fi
        in_array "$last_option" "$options_arches" || ((after_counter++))
    done

    # completion

    if [[ -n $options_target ]] && in_array "$prev" "$options_target"; then
        COMPREPLY=( $(compgen -W "$(_fedpkg_target)" -- "$cur") )

    elif [[ -n $options_arches ]] && in_array "$last_option" "$options_arches"; then
        COMPREPLY=( $(compgen -W "$(_fedpkg_arch) $all_options" -- "$cur") )

    elif [[ -n $options_srpm ]] && in_array "$prev" "$options_srpm"; then
        _filedir_exclude_paths "*.src.rpm"

    elif [[ -n $options_branch ]] && in_array "$prev" "$options_branch"; then
        COMPREPLY=( $(compgen -W "$(_fedpkg_branch "$path")" -- "$cur") )

    elif [[ -n $options_file ]] && in_array "$prev" "$options_file"; then
        _filedir_exclude_paths

    elif [[ -n $options_dir ]] && in_array "$prev" "$options_dir"; then
        _filedir_exclude_paths -d

    elif [[ -n $options_string ]] && in_array "$prev" "$options_string"; then
        COMPREPLY=( )

    else
        local compgen_extra=
        local after_options=

        if [[ $after_counter -eq 0 ]] || [[ $after_more = true ]]; then
            case $after in
                file)    _filedir_exclude_paths; compgen_extra=${COMPREPLY[@]} ;;
                srpm)    _filedir_exclude_paths "*.src.rpm"; compgen_extra=${COMPREPLY[@]} ;;
                branch)  after_options="$(_fedpkg_branch "$path")" ;;
                package) after_options="$(_fedpkg_package "$cur")";;
            esac
        fi

        COMPREPLY=( $(compgen -W "$all_options $all_options_value $after_options $compgen_extra" -- "$cur" ) )
    fi

    return 0
} &&
complete -F _fedpkg fedpkg

have _fedpkg &&
_fedpkg_target()
{
    koji list-targets --quiet 2>/dev/null | cut -d" " -f1
}

have _fedpkg &&
_fedpkg_arch()
{
    echo "i386 x86_64 ppc ppc64 s390 s390x sparc sparc64"
}

have _fedpkg &&
_fedpkg_branch()
{
    local git_options= format="--format %(refname:short)"
    [[ -n $1 ]] && git_options="--git-dir=$1/.git"

    git $git_options for-each-ref $format 'refs/remotes/origin/*/master' \
        | sed 's,origin/\(.*\)/master,\1,'
    git $git_options for-each-ref $format 'refs/heads'
}

have _fedpkg &&
_fedpkg_package()
{
    repoquery -C --qf=%{sourcerpm} "$1*" 2>/dev/null | sort -u | sed -r 's/(-[^-]*){2}\.src\.rpm$//'
}

# Local variables:
# mode: shell-script
# sh-basic-offset: 4
# sh-indent-comment: t
# indent-tabs-mode: nil
# End:
# ex: ts=4 sw=4 et filetype=sh
