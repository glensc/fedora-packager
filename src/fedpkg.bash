# fedpkg bash completion

have fedpkg &&
_fedpkg()
{
    local cur prev commands options command

    COMPREPLY=()
    _get_comp_words_by_ref cur prev

    # define all available commands to complete
    commands='help build chain-build clean clog clone co commit ci compile \
    diff gimmespec giturl import install lint local mockbuild new new-sources \
    patch prep push scratch-build sources srpm switch-branch tag-request \
    unused-patches update upload verrel'

    if [[ $COMP_CWORD -eq 1 ]] ; then
        if [[ "$cur" == -* ]]; then
            # show available options when no subcommand is provided
            COMPREPLY=( $( compgen -W '-h --help -u --user --path -v -q' \
            -- "$cur" ) )
        else
            COMPREPLY=( $( compgen -W "$commands" -- "$cur" ) )
        fi
    else
        # these completions are available to all commands and are executed
        # when a specific parameter is given
        case $prev in
            # list all files in current directory
            --path|--file|-F|--outdir)
                _filedir
                return 0;
                ;;
            # list available architectures when provided with these parameters
            --arch|--arches)
                COMPREPLY=( $( compgen -W 'i386 i586 i686 x86_64' -- "$cur" ) )
                return 0;
                ;;
             # list all source RPMs in current directory
             --srpm)
                 COMPREPLY=( ${COMPREPLY[@]:-} \
                 $( compgen -W '$( command ls *.src.rpm 2>/dev/null )' \
                 -- "$cur" ) )
                 return 0;
                ;;
             -*)
                return 0;
                ;;
        esac

        command=${COMP_WORDS[1]}

        if [[ "$cur" == -* ]]; then
            # list possible options for the command
            case $command in
                build)
                    options='--nowait --background --skip-tag --scratch --test'
                    ;;
                chain-build)
                    options='--nowait --background'
                    ;;
                clean)
                    options='--dy-run -n -x'
                    ;;
                clone|co)
                    options='--branches -B --branch -b --anonymous -a'
                    ;;
                commit|ci)
                    options='-m --message -F --file -p --push'
                    ;;
                compile)
                    options='--arch --short-circuit'
                    ;;
                import)
                    options='--branch -b --create -c'
                    ;;
                install)
                    options='--arch --short-circuit'
                    ;;
                local)
                    options='--arch --md5'
                    ;;
                patch)
                    options='--suffix --rediff'
                    ;;
                prep)
                    options='--arch'
                    ;;
                scratch-build)
                    options='--nowait --background --arches --srpm'
                    ;;
                sources)
                    options='--outdir'
                    ;;
                srpm)
                    options='--md5'
                    ;;
                switch-branch)
                    options='-l'
                    ;;
                # don't complete by listing files in current directory for
                # these commands, just provide the help option
                clog|gimmespec|lint|mockbuild|new|giturl|push|tag-request|\
                unused-patches|update|verrel)
                    options='-h --help'
                    ;;
            esac
            # these options are available to all commands
            options="$options --help -h"

            COMPREPLY=( $( compgen -W "$options" -- "$cur" ) )
        else
            # different completion for these commands
            case $command in
                upload)
                    _filedir
                    ;;
                import)
                    # complete by listing all source rpms
                    COMPREPLY=( ${COMPREPLY[@]:-} \
                        $( compgen -W '$( command ls *.src.rpm 2>/dev/null )' \
                        -- "$cur" ) )
                    ;;
                # no further arguments are required for these commands
                help|build|clean|clog|compile|gimmespec|giturl|install|lint|\
                local|mockbuild|new|patch|prep|push|scratch-build|sources|\
                srpm|switch-branch|tag-request|unused-patches|update|verrel)
                    ;;
                *)
                    _filedir
                    ;;
            esac
        fi
    fi

    return 0
} &&
complete -F _fedpkg -o filenames fedpkg

# Local variables:
# mode: shell-script
# sh-basic-offset: 4
# sh-indent-comment: t
# indent-tabs-mode: nil
# End:
# ex: ts=4 sw=4 et filetype=sh
