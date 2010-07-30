# fedpkg bash completion

have fedpkg &&
_fedpkg()
{
    local cur prev commands options command

    COMPREPLY=()
    _get_comp_words_by_ref cur prev

    commands='help build chain-build clean clog clone co commit compile diff \
    gimmespec import install lint local mockbuild new new-sources patch prep \
    push scratch-build sources srpm switch-branch tag-request unused-patches \
    specfile update upload verrel'

    if [[ $COMP_CWORD -eq 1 ]] ; then
        if [[ "$cur" == -* ]]; then
            COMPREPLY=( $( compgen -W '-h --help -u --user --path -v -q' \
            -- "$cur" ) )
        else
            COMPREPLY=( $( compgen -W "$commands" -- "$cur" ) )
        fi
    else
        case $prev in
            --path|--file|-F|--outdir)
                _filedir
                return 0;
                ;;
            --arch|--arches)
                COMPREPLY=( $( compgen -W 'i386 x86_64' -- "$cur" ) )
                return 0;
                ;;
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
            # possible options for the command
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
                commit)
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
                clog|gimmespec|lint|mockbuild|new|push|tag-request|\
                unused-patches|update|verrel)
                    options='-h'
                    ;;
            esac
            options="$options --help -h"

            COMPREPLY=( $( compgen -W "$options" -- "$cur" ) )
        else
            case $command in
                upload)
                    _filedir
                    ;;
                import)
                    COMPREPLY=( ${COMPREPLY[@]:-} \
                        $( compgen -W '$( command ls *.src.rpm 2>/dev/null )' \
                        -- "$cur" ) )
                    ;;
                # no further args required
                help|build|clean|clog|compile|gimmespec|install|lint|local|\
                mockbuild|new|patch|prep|push|scratch-build|sources|srpm|\
                switch-branch|tag-request|unused-patches|update|verrel)
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
