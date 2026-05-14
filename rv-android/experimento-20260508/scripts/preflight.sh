#!/bin/bash
# preflight.sh — patches aplicados ao container ANTES de delegar pro docker-entrypoint.sh.
#
# Hot-patch androguard 3.4.0a1: aapt2 moderno (Android 13+, targetSdk >= 33) escreve
# ARSCResTypeSpec.res1 != 0 no resources.arsc. O parser do androguard 3.4.0a1 (pinado
# por droidbot 1.0.2b4) levanta ResParserError. Versão 4.x corrigiu mas mudou import
# path (`androguard.core.apk` em vez de `androguard.core.bytecodes.apk`), quebrando
# o droidbot. 1-line sed é a solução de menor escopo até gerarmos imagem nova.
#
# Validado em 190/190 APKs do dataset (ch.famoser.mensa_60.apk e demais).

set -e

PARSER=/usr/local/lib/python3.12/site-packages/androguard/core/bytecodes/axml/__init__.py
if [ -f "$PARSER" ]; then
    if grep -q 'raise ResParserError("res1 must be zero!")' "$PARSER"; then
        # Linha original:
        #             raise ResParserError("res1 must be zero!")
        # (12 espaços de indent — dentro do `if self.res1 != 0:`)
        sed -i 's|raise ResParserError("res1 must be zero!")|pass  # rv-android: aapt2 modern emits res1 != 0; ignored.|' "$PARSER"
        echo "preflight: androguard res1 patch APPLIED"
    else
        echo "preflight: androguard res1 patch already present"
    fi
else
    echo "preflight: WARNING $PARSER not found, skipping"
fi

exec /opt/docker-entrypoint.sh "$@"
