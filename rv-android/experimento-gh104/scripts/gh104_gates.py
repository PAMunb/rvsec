#!/usr/bin/env python3
"""Os portões de aceitação da gh104, aplicados a uma campanha já gravada.

    uv run python experimento-gh104/scripts/gh104_gates.py \
        --results-glob 'experimento-comp162/results/comp162_*/comp162_*' \
        --label baseline-comp162

## A pergunta

A gh104 promete que uma violação passa a **dizer o que aconteceu**: um envelope
versionado no lugar do literal `unknown`, o evento do autômato que disparou, o valor
observado e o esperado. Depois que uma campanha roda, alguém precisa decidir se a
promessa saiu no artefato ou se ficou no documento. Este script decide, offline, sobre
os arquivos gravados. Não toca emulador, não roda experimento, não escreve nada em
`experimento-comp162/` nem em qualquer diretório de campanha.

## Por que duas fontes

O `errors.csv` é o que toda análise a jusante lê, mas ele é o **fim** de um transporte
de dez etapas: uma mensagem pode ter sido reescrita, truncada ou perdida entre o monitor
e ele. O `.logcat` cru é o que o monitor de fato escreveu. Os portões são avaliados nas
duas populações e reportam as duas contagens, porque uma divergência entre elas é ela
mesma um defeito — e é um defeito que só aparece se as duas forem medidas.

O payload do logcat tem **sete campos separados por vírgula e o sétimo contém vírgulas**
(`spec,class,simpleClass,method,location,violationType,message`). Uma mensagem real lê
`expecting one of TLSv1.2,TLSv1.3 but found TLS.`, então dividir em toda vírgula corta a
mensagem ao meio. O split é limitado em seis e o resto é a mensagem, verbatim.

## Autocontido de propósito

Nada aqui importa de `aperv_tool.analysis.violations`, embora aquele módulo leia os
mesmos dois formatos. O leitor compartilhado valida o cabeçalho contra uma constante que
a própria gh104 muda de 11 para 13 colunas — depois dessa mudança ele levanta `ValueError`
em todo arquivo pré-gh104, que é exatamente o corpus contra o qual este script precisa
rodar para provar que os portões acusam. Um verificador que não roda contra o corpus
reprovado não verifica nada. Só a stdlib, então.

## O que cada portão decide

| portão | reprova quando |
|---|---|
| G1 | alguma mensagem é o literal `unknown` (baseline comp162: 79,91 %) |
| G2 | alguma mensagem termina em `but found .` — valor observado vazio (baseline: 98) |
| G3 | o cabeçalho do `errors.csv` não é o de 13 colunas da gh104 |
| G4 | algum `unique_msg` não tem sete partes `:::` |
| G5 | alguma mensagem não casa o envelope v1, ou traz código fora do `codes.csv` |
| G6 | a macro `__EVENTNAME` aparece sem expandir |
| G7 | há `\n` literal, `:::` ou envelope truncado dentro do envelope |
| G8 | as colunas `code`/`event` estão vazias em vez de `UNSPECIFIED` |
| G9 | nunca — imprime a distribuição para leitura humana |
| G10 | o `instrument_results.json` existe e não traz os dois contadores da tecelagem |

Saída: um bloco por portão, `N PASS / M FAIL / K SKIP` no fim, código de saída 1 se
houver qualquer FAIL. Com `--json`, o mesmo resultado estruturado em arquivo.

Uma linha de formato inesperado é **mantida e contada**, nunca descartada e nunca causa
exceção: a contagem de violações é o que os portões leem, e um leitor que jogasse fora a
linha que não entendeu encolheria a própria quantidade sob medição.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Contratos de formato
# ---------------------------------------------------------------------------

#: O cabeçalho que a gh104 promete. `code` e `event` entram depois de `source`.
ERRORS_CSV_HEADER = (
    "apk",
    "rep",
    "timeout",
    "tool",
    "time",
    "spec",
    "class",
    "method",
    "source",
    "code",
    "event",
    "message",
    "unique_msg",
)

#: O cabeçalho de 11 colunas que precede a mudança. Declarado para que o portão possa
#: dizer *qual* corpus está lendo em vez de só dizer que o cabeçalho está errado.
ERRORS_CSV_HEADER_LEGACY = (
    "apk",
    "rep",
    "timeout",
    "tool",
    "time",
    "spec",
    "class",
    "method",
    "source",
    "message",
    "unique_msg",
)

PRE_GH104_VERDICT = "corpus da era pré-gh104"

ERRORS_CSV_NAME = "errors.csv"
INSTRUMENT_RESULTS_NAME = "instrument_results.json"
LOGCAT_SUFFIX = ".logcat"

#: `mute` na definição congelada da E0: a mensagem é o literal, sem espaços em volta.
MUTE_MESSAGE = "unknown"

#: O que sobra quando o sítio interpola um valor observado vazio na sentença.
EMPTY_OBSERVED_SUFFIX = "but found ."

UNIQUE_SEPARATOR = ":::"
UNIQUE_PARTS = 7
#: Índice do tipo de erro dentro de `unique_msg`. É 3 nas duas eras — cinco partes
#: (`class:::method:::spec:::error_type:::message`) e sete (com `code` e `event` depois
#: de `error_type`) — então a distribuição de G9 lê o mesmo campo nos dois corpora.
UNIQUE_ERROR_TYPE_INDEX = 3

#: O sentinela que substitui um valor que o produtor não forneceu. Nunca célula vazia:
#: um leitor precisa distinguir "sem envelope" de "envelope com valor vazio".
SENTINEL = "UNSPECIFIED"

#: A macro que o gerador de monitores expande. Se ela chega ao logcat, não expandiu.
EVENTNAME_MACRO = "__EVENTNAME"

ENVELOPE_PREFIX = "v=1 "

#: O vocabulário de KIND do design D-3, usado **só quando não há `codes.csv`**.
#:
#: `REQ` (`RequiredPredicate`) foi descartado como grafia — nenhum sítio do `jca_android`
#: o emite —, mas as leituras de predicado continuam existindo: a gh105 as ligou à família
#: `NOBS` (*not observed*), o terceiro valor de uma leitura de predicado. `NOBS` precisa de
#: família própria porque o `error_type` não separa — um código `NOBS` e um código `CONSTR`
#: carregam ambos `UnsatisfiedConstraint`, e só o código distingue "violou" de "não
#: observou".
#:
#: Esta lista já envelheceu uma vez: nasceu sem `NOBS`, e o `codes.csv` do conjunto tem
#: **30 códigos `NOBS` de 114** (medido em `6192b57a`: `CONSTR` 41, `NOBS` 30, `ORDER` 21,
#: `ALG` 17, `FORB` 2, `KEYSIZE` 1, `KSTYPE` 1, `PROTO` 1) — o G5 teria reprovado uma
#: campanha correta. Por isso ela é só a rede de segurança de quem roda sem `--codes-csv`
#: (tipicamente contra um corpus pré-gh104, que não tem envelope nenhum): congelar de novo
#: o vocabulário é repetir o defeito.
ENVELOPE_KINDS_FALLBACK = frozenset(
    {"ORDER", "ALG", "CONSTR", "KEYSIZE", "KSTYPE", "PROTO", "FORB", "NOBS"}
)

#: A coluna do `codes.csv` (`spec,code,error_type,site_kind,event,file_line`) de onde o
#: vocabulário é lido. O KIND é derivado do próprio código e não da coluna `site_kind`,
#: que é redundante com ele: assim um `codes.csv` internamente inconsistente aparece como
#: código desconhecido em vez de passar pela porta lateral.
CODES_CSV_CODE_COLUMN = "code"

#: Proibidos dentro de um valor do envelope: `\n` porque o logcat quebra a linha nele,
#: `:::` porque é o separador de `unique_msg`.
FORBIDDEN_NEWLINE = "\\n"
FORBIDDEN_SEPARATOR = UNIQUE_SEPARATOR

#: Um valor entre aspas simples: qualquer coisa que não seja aspa, ou uma aspa escapada.
_QUOTED_VALUE = r"(?:\\'|[^'])*"

ENVELOPE_RE = re.compile(
    r"^v=1 code=(?P<code>\S+) ev=(?P<ev>\S+) obj=(?P<obj>\S+) "
    rf"val='(?P<val>{_QUOTED_VALUE})' "
    rf"exp='(?P<exp>{_QUOTED_VALUE})' "
    rf"msg='(?P<msg>{_QUOTED_VALUE})'$"
)

CODE_RE = re.compile(r"^(?P<spec>[A-Z0-9]+)-(?P<kind>[A-Z]+)-(?P<nn>\d{2})$")


@dataclass(frozen=True)
class CodeVocabulary:
    """Contra o que o G5 julga o `code=` de um envelope.

    Com `--codes-csv`, `codes` é o catálogo do conjunto sob medição e o portão sabe
    responder duas perguntas diferentes: *o código é bem-formado?* (o KIND existe) e *o
    código existe?* (está no catálogo). Sem o arquivo só a primeira é respondível, e a
    segunda vira silêncio declarado — nunca um PASS por omissão.
    """

    kinds: frozenset
    codes: frozenset = frozenset()
    source: str = "lista congelada no script (sem --codes-csv)"

    @property
    def authoritative(self) -> bool:
        """Há catálogo para dizer se um código bem-formado de fato existe."""
        return bool(self.codes)


def load_code_vocabulary(path: Path | None) -> CodeVocabulary:
    """Lê o vocabulário do `codes.csv` do conjunto sob medição.

    Levanta `SystemExit` quando o arquivo foi pedido e não serve: um portão que caísse de
    volta na lista congelada em silêncio mediria outra coisa que não a que lhe pediram.
    """
    if path is None:
        return CodeVocabulary(kinds=ENVELOPE_KINDS_FALLBACK)
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            codes = {
                (row.get(CODES_CSV_CODE_COLUMN) or "").strip()
                for row in csv.DictReader(handle)
            }
    except OSError as error:
        raise SystemExit(f"FALHA: --codes-csv {path}: {error}") from error
    codes.discard("")
    if not codes:
        raise SystemExit(
            f"FALHA: {path} não traz nenhum código na coluna '{CODES_CSV_CODE_COLUMN}'"
        )
    kinds = {
        match.group("kind")
        for match in (CODE_RE.match(code) for code in codes)
        if match is not None
    }
    return CodeVocabulary(frozenset(kinds), frozenset(codes), str(path))


VIOLATION_TAG = "RVSEC"

#: O split do payload é limitado em seis: tudo depois da sexta vírgula é a mensagem.
VIOLATION_FIELDS = 6

#: `RVSEC   : ` e `RVSEC-COV: ` compartilham o prefixo; o que separa as duas tags é o
#: byte imediatamente seguinte. Rejeitar por ele evita decodificar o fluxo de cobertura,
#: que é uma ordem de grandeza maior que o de violações.
_TAG_BYTES = VIOLATION_TAG.encode()
_TAG_TERMINATORS = (b" ", b":")
_EVENTNAME_BYTES = EVENTNAME_MACRO.encode()

LOGCAT_LINE_RE = re.compile(
    r"^\d\d-\d\d \d\d:\d\d:\d\d\.\d\d\d\s+\d+\s+\d+\s+[VDIWEF] "
    rf"{VIOLATION_TAG}\s*:\s*(?P<payload>.*)$"
)

#: Os dois contadores que a variante dexlib2 publica no JSON de instrumentação.
WEAVE_COUNT_KEYS = ("advicesExcludedByArity", "wrappersGenerated")

#: Quantas linhas ofensoras cada portão mostra. O suficiente para reconhecer a forma do
#: defeito; a contagem é que dimensiona.
SAMPLE_LIMIT = 5

#: Os números medidos na comp162 (E0). Impressos ao lado do que este run mediu, para que
#: uma regressão apareça como distância de um valor conhecido e não como número solto.
BASELINE_LABEL = "baseline comp162"
BASELINE_MUTE_PCT = 79.91
BASELINE_MUTE_ROWS = 15714
BASELINE_EMPTY_OBSERVED = 98

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


# ---------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------


@dataclass
class Samples:
    """Até `limit` exemplos de linhas ofensoras, com a origem de cada uma."""

    limit: int = SAMPLE_LIMIT
    items: list[str] = field(default_factory=list)

    def add(self, where: str, text: str) -> None:
        if len(self.items) < self.limit:
            self.items.append(f"{where}: {text[:300]}")


@dataclass
class EnvelopeVerdict:
    """O que uma mensagem é, do ponto de vista da gramática do envelope v1.

    `claims` separa "não é envelope" (uma mensagem legada, `unknown`) de "diz ser
    envelope e não é" (um envelope malformado). Os dois reprovam G5, mas por motivos
    diferentes e com reparos diferentes.
    """

    claims: bool = False
    matched: bool = False
    sentinel: bool = False
    truncated: bool = False
    macro_event: bool = False
    #: Bem-formado, mas fora do catálogo do conjunto — só decidível com `--codes-csv`.
    #: É deriva de proveniência: o APK carrega monitores de um `codes.csv` que não é este.
    unknown_code: bool = False
    forbidden: tuple[str, ...] = ()
    code: str = ""
    event: str = ""


def _count_unescaped_quotes(text: str) -> int:
    """Aspas simples que abrem ou fecham um valor, ignorando as escapadas como `\\'`."""
    total = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "'":
            total += 1
        index += 1
    return total


def inspect_envelope(message: str, vocab: CodeVocabulary) -> EnvelopeVerdict:
    """Julga uma mensagem contra a gramática `v=1 code=… ev=… obj=… val='…' exp='…' msg='…'`.

    Nunca levanta: uma mensagem de qualquer forma recebe um veredito, porque a linha
    conta mesmo quando não é compreendida.
    """
    text = (message or "").strip()
    if not text.startswith(ENVELOPE_PREFIX):
        return EnvelopeVerdict(claims=False)

    forbidden = []
    if FORBIDDEN_NEWLINE in text:
        forbidden.append(FORBIDDEN_NEWLINE)
    if FORBIDDEN_SEPARATOR in text:
        forbidden.append(FORBIDDEN_SEPARATOR)

    # Uma aspa final não fechada é a única evidência que o leitor tem de que o logcat
    # cortou o registro: o corte acontece em LOGGER_ENTRY_MAX_PAYLOAD sem marcador.
    truncated = _count_unescaped_quotes(text) % 2 == 1

    match = ENVELOPE_RE.match(text)
    if match is None:
        return EnvelopeVerdict(
            claims=True,
            truncated=truncated,
            forbidden=tuple(forbidden),
        )

    code = match.group("code")
    event = match.group("ev")
    code_match = CODE_RE.match(code)
    sentinel = code == SENTINEL or event == SENTINEL
    well_formed = code_match is not None and code_match.group("kind") in vocab.kinds
    return EnvelopeVerdict(
        claims=True,
        matched=well_formed and not sentinel,
        sentinel=sentinel,
        truncated=truncated,
        macro_event=event == EVENTNAME_MACRO,
        unknown_code=(
            well_formed
            and not sentinel
            and vocab.authoritative
            and code not in vocab.codes
        ),
        forbidden=tuple(forbidden),
        code=code,
        event=event,
    )


def split_payload(payload: str) -> tuple[list[str], bool]:
    """Decompõe um payload `RVSEC` nos sete campos do logger.

    Devolve `(campos, shape_ok)`. Um payload com menos de sete campos volta inteiro em
    `campos[-1]` com `shape_ok` False — a linha continua sendo uma violação e continua
    contando.
    """
    fields = payload.split(",", VIOLATION_FIELDS)
    if len(fields) <= VIOLATION_FIELDS:
        return fields, False
    return fields, True


@dataclass
class CsvReading:
    """Tudo que a leitura dos `errors.csv` de uma campanha encontrou."""

    files: int = 0
    rows: int = 0
    headers: Counter = field(default_factory=Counter)
    header_files: dict = field(default_factory=dict)
    unreadable: list = field(default_factory=list)
    shape_mismatch: int = 0

    mute: int = 0
    mute_samples: Samples = field(default_factory=Samples)
    empty_observed: int = 0
    empty_observed_samples: Samples = field(default_factory=Samples)

    unique_parts: Counter = field(default_factory=Counter)
    unique_unparsed: int = 0
    unique_samples: Samples = field(default_factory=Samples)

    envelope_matched: int = 0
    envelope_sentinel: int = 0
    envelope_absent: int = 0
    envelope_malformed: int = 0
    envelope_samples: Samples = field(default_factory=Samples)
    unknown_code: int = 0
    unknown_code_samples: Samples = field(default_factory=Samples)
    truncated: int = 0
    truncated_samples: Samples = field(default_factory=Samples)
    forbidden: Counter = field(default_factory=Counter)
    forbidden_samples: Samples = field(default_factory=Samples)
    macro_event: int = 0
    macro_samples: Samples = field(default_factory=Samples)

    code_column_present: bool = False
    event_column_present: bool = False
    empty_code: int = 0
    empty_event: int = 0
    empty_code_samples: Samples = field(default_factory=Samples)

    spec_error_type: Counter = field(default_factory=Counter)
    codes: Counter = field(default_factory=Counter)


def read_errors_csv(path: Path, reading: CsvReading, vocab: CodeVocabulary) -> None:
    """Acumula um `errors.csv` no acumulador, sem levantar por formato inesperado."""
    try:
        handle = path.open("r", encoding="utf-8", errors="replace", newline="")
    except OSError as error:
        reading.unreadable.append(f"{path}: {error}")
        return

    with handle:
        rows = csv.reader(handle)
        try:
            header = next(rows)
        except StopIteration:
            reading.unreadable.append(f"{path}: arquivo vazio")
            return
        except csv.Error as error:
            reading.unreadable.append(f"{path}: {error}")
            return

        reading.files += 1
        header_key = tuple(header)
        reading.headers[header_key] += 1
        reading.header_files.setdefault(header_key, str(path))
        reading.code_column_present |= "code" in header_key
        reading.event_column_present |= "event" in header_key

        width = len(header)
        for number, values in enumerate(rows, start=2):
            reading.rows += 1
            if len(values) != width:
                # Mantida e contada: a linha é uma violação mesmo com a forma errada.
                reading.shape_mismatch += 1
            row = dict(zip(header, values))
            _accumulate_row(row, f"{path}:{number}", reading, vocab)


def _accumulate_row(
    row: dict, where: str, reading: CsvReading, vocab: CodeVocabulary
) -> None:
    message = (row.get("message") or "").strip()

    if message == MUTE_MESSAGE:
        reading.mute += 1
        reading.mute_samples.add(where, message)
    if message.endswith(EMPTY_OBSERVED_SUFFIX):
        reading.empty_observed += 1
        reading.empty_observed_samples.add(where, message)

    unique = row.get("unique_msg") or ""
    parts = unique.split(UNIQUE_SEPARATOR)
    reading.unique_parts[len(parts)] += 1
    if len(parts) != UNIQUE_PARTS:
        reading.unique_unparsed += 1
        reading.unique_samples.add(where, unique)

    verdict = inspect_envelope(message, vocab)
    if verdict.matched:
        reading.envelope_matched += 1
        if verdict.unknown_code:
            reading.unknown_code += 1
            reading.unknown_code_samples.add(where, message)
    elif verdict.sentinel:
        reading.envelope_sentinel += 1
    elif verdict.claims:
        reading.envelope_malformed += 1
        reading.envelope_samples.add(where, message)
    else:
        reading.envelope_absent += 1
        reading.envelope_samples.add(where, message)
    if verdict.truncated:
        reading.truncated += 1
        reading.truncated_samples.add(where, message)
    for token in verdict.forbidden:
        reading.forbidden[token] += 1
        reading.forbidden_samples.add(where, message)
    if verdict.macro_event:
        reading.macro_event += 1
        reading.macro_samples.add(where, message)

    if reading.code_column_present:
        code = (row.get("code") or "").strip()
        if not code:
            reading.empty_code += 1
            reading.empty_code_samples.add(where, unique or message)
        reading.codes[code or "<vazio>"] += 1
    if reading.event_column_present:
        if not (row.get("event") or "").strip():
            reading.empty_event += 1

    spec = (row.get("spec") or "").strip() or "<vazio>"
    if len(parts) > UNIQUE_ERROR_TYPE_INDEX:
        error_type = parts[UNIQUE_ERROR_TYPE_INDEX] or "<vazio>"
    else:
        error_type = "<unique_msg não decomposto>"
    reading.spec_error_type[(spec, error_type)] += 1


@dataclass
class LogcatReading:
    """Tudo que a leitura dos `.logcat` crus encontrou.

    O logcat é a fonte da verdade das mensagens: é o que o monitor escreveu, antes de
    qualquer etapa do transporte poder reescrevê-lo.
    """

    files: int = 0
    unreadable: list = field(default_factory=list)
    violation_lines: int = 0
    shape_bad: int = 0
    shape_samples: Samples = field(default_factory=Samples)

    mute: int = 0
    mute_samples: Samples = field(default_factory=Samples)
    empty_observed: int = 0
    empty_observed_samples: Samples = field(default_factory=Samples)

    envelope_matched: int = 0
    envelope_sentinel: int = 0
    envelope_absent: int = 0
    envelope_malformed: int = 0
    envelope_samples: Samples = field(default_factory=Samples)
    unknown_code: int = 0
    unknown_code_samples: Samples = field(default_factory=Samples)
    truncated: int = 0
    truncated_samples: Samples = field(default_factory=Samples)
    forbidden: Counter = field(default_factory=Counter)
    forbidden_samples: Samples = field(default_factory=Samples)

    macro_event: int = 0
    macro_anywhere: int = 0
    macro_samples: Samples = field(default_factory=Samples)

    codes: Counter = field(default_factory=Counter)


def read_logcat(path: Path, reading: LogcatReading, vocab: CodeVocabulary) -> None:
    """Acumula um `.logcat` no acumulador.

    Lido em bytes: os testes baratos vêm primeiro porque o fluxo de cobertura
    (`RVSEC-COV`) domina o arquivo, e decodificar cada uma de suas linhas só para
    rejeitá-la custaria mais que toda a leitura.
    """
    try:
        handle = path.open("rb")
    except OSError as error:
        reading.unreadable.append(f"{path}: {error}")
        return

    reading.files += 1
    with handle:
        for number, raw in enumerate(handle, start=1):
            has_macro = _EVENTNAME_BYTES in raw
            if has_macro:
                reading.macro_anywhere += 1
                if len(reading.macro_samples.items) < reading.macro_samples.limit:
                    reading.macro_samples.add(
                        f"{path}:{number}", raw.decode("utf-8", "replace").rstrip("\n")
                    )

            start = raw.find(_TAG_BYTES)
            if start < 0:
                continue
            after = start + len(_TAG_BYTES)
            if raw[after : after + 1] not in _TAG_TERMINATORS:
                continue
            match = LOGCAT_LINE_RE.match(raw.decode("utf-8", "replace").rstrip("\n"))
            if match is None:
                continue
            reading.violation_lines += 1
            _accumulate_violation(
                match.group("payload"), f"{path}:{number}", has_macro, reading, vocab
            )


def _accumulate_violation(
    payload: str,
    where: str,
    has_macro: bool,
    reading: LogcatReading,
    vocab: CodeVocabulary,
) -> None:
    fields, shape_ok = split_payload(payload)
    if not shape_ok:
        reading.shape_bad += 1
        reading.shape_samples.add(where, payload)
        message = payload
    else:
        message = fields[VIOLATION_FIELDS]

    stripped = message.strip()
    if stripped == MUTE_MESSAGE:
        reading.mute += 1
        reading.mute_samples.add(where, stripped)
    if stripped.endswith(EMPTY_OBSERVED_SUFFIX):
        reading.empty_observed += 1
        reading.empty_observed_samples.add(where, stripped)

    verdict = inspect_envelope(message, vocab)
    if verdict.matched:
        reading.envelope_matched += 1
        reading.codes[verdict.code] += 1
        if verdict.unknown_code:
            reading.unknown_code += 1
            reading.unknown_code_samples.add(where, message)
    elif verdict.sentinel:
        reading.envelope_sentinel += 1
        reading.codes[verdict.code or SENTINEL] += 1
    elif verdict.claims:
        reading.envelope_malformed += 1
        reading.envelope_samples.add(where, message)
    else:
        reading.envelope_absent += 1
        reading.envelope_samples.add(where, message)
    if verdict.truncated:
        reading.truncated += 1
        reading.truncated_samples.add(where, message)
    for token in verdict.forbidden:
        reading.forbidden[token] += 1
        reading.forbidden_samples.add(where, message)
    if verdict.macro_event or (has_macro and "ev=" + EVENTNAME_MACRO in message):
        reading.macro_event += 1


@dataclass
class InstrumentReading:
    """O que os `instrument_results.json` da campanha trazem sobre a tecelagem."""

    files: list = field(default_factory=list)
    missing_keys: list = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)
    unreadable: list = field(default_factory=list)


def read_instrument_results(path: Path, reading: InstrumentReading) -> None:
    try:
        document = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError) as error:
        reading.unreadable.append(f"{path}: {error}")
        return

    reading.files.append(str(path))
    entries = document.get("results") if isinstance(document, dict) else None
    if not isinstance(entries, list):
        reading.missing_keys.append(f"{path}: sem lista `results`")
        return
    for entry in entries:
        counts = entry.get("weaveCounts") if isinstance(entry, dict) else None
        if not isinstance(counts, dict):
            reading.missing_keys.append(f"{path}: entrada sem `weaveCounts`")
            continue
        for key in WEAVE_COUNT_KEYS:
            if key in counts:
                reading.counts[key] += 1
            else:
                reading.missing_keys.append(f"{path}: `{key}` ausente")


# ---------------------------------------------------------------------------
# Descoberta dos containers
# ---------------------------------------------------------------------------


def containers_under(path: Path) -> list[Path]:
    """Os diretórios que contêm um `errors.csv`, a partir de um caminho qualquer.

    Aceita tanto o container em si (`results/<name>_NN/<name>_NN/`) quanto um diretório
    de campanha um ou dois níveis acima dele. Um caminho sem nenhum `errors.csv` volta
    como container assim mesmo, para que os seus logcats ainda sejam lidos e a ausência
    do CSV seja reportada em vez de silenciada.
    """
    if (path / ERRORS_CSV_NAME).is_file():
        return [path]
    for depth in ("*", "*/*"):
        found = sorted({found.parent for found in path.glob(f"{depth}/{ERRORS_CSV_NAME}")})
        if found:
            return found
    return [path]


def resolve_containers(patterns: list[str]) -> list[Path]:
    containers: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for hit in sorted(glob.glob(pattern)):
            path = Path(hit)
            if path.is_file() and path.name == ERRORS_CSV_NAME:
                path = path.parent
            if not path.is_dir():
                continue
            for container in containers_under(path):
                resolved = container.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    containers.append(container)
    return containers


# ---------------------------------------------------------------------------
# Portões
# ---------------------------------------------------------------------------


@dataclass
class Gate:
    gate_id: str
    title: str
    status: str
    detail: dict = field(default_factory=dict)
    lines: list = field(default_factory=list)
    samples: list = field(default_factory=list)


def _pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def gate_g1(csv_data: CsvReading, log_data: LogcatReading) -> Gate:
    csv_pct = _pct(csv_data.mute, csv_data.rows)
    log_pct = _pct(log_data.mute, log_data.violation_lines)
    status = PASS if csv_data.mute == 0 and log_data.mute == 0 else FAIL
    return Gate(
        "G1",
        f"mensagem == '{MUTE_MESSAGE}' deve ser 0",
        status,
        detail={
            "csv_mute": csv_data.mute,
            "csv_rows": csv_data.rows,
            "csv_pct": csv_pct,
            "logcat_mute": log_data.mute,
            "logcat_lines": log_data.violation_lines,
            "logcat_pct": log_pct,
            "baseline_pct": BASELINE_MUTE_PCT,
            "baseline_rows": BASELINE_MUTE_ROWS,
        },
        lines=[
            f"errors.csv : {csv_data.mute} de {csv_data.rows} linhas ({csv_pct} %)",
            f"logcat     : {log_data.mute} de {log_data.violation_lines} linhas ({log_pct} %)",
            f"{BASELINE_LABEL}: {BASELINE_MUTE_ROWS} linhas ({BASELINE_MUTE_PCT} %)",
        ],
        samples=csv_data.mute_samples.items or log_data.mute_samples.items,
    )


def gate_g2(csv_data: CsvReading, log_data: LogcatReading) -> Gate:
    status = PASS if csv_data.empty_observed == 0 and log_data.empty_observed == 0 else FAIL
    return Gate(
        "G2",
        f"mensagens terminando em '{EMPTY_OBSERVED_SUFFIX}' devem ser 0",
        status,
        detail={
            "csv": csv_data.empty_observed,
            "logcat": log_data.empty_observed,
            "baseline": BASELINE_EMPTY_OBSERVED,
        },
        lines=[
            f"errors.csv : {csv_data.empty_observed}",
            f"logcat     : {log_data.empty_observed}",
            f"{BASELINE_LABEL}: {BASELINE_EMPTY_OBSERVED}",
        ],
        samples=csv_data.empty_observed_samples.items
        or log_data.empty_observed_samples.items,
    )


def gate_g3(csv_data: CsvReading) -> Gate:
    if csv_data.files == 0:
        return Gate(
            "G3",
            "cabeçalho do errors.csv com as 13 colunas da gh104",
            SKIP,
            lines=["nenhum errors.csv encontrado nos containers"],
        )

    lines = []
    samples = []
    status = PASS
    for header, count in csv_data.headers.most_common():
        where = csv_data.header_files[header]
        if header == ERRORS_CSV_HEADER:
            lines.append(f"{count} arquivo(s) com as 13 colunas esperadas")
            continue
        status = FAIL
        if header == ERRORS_CSV_HEADER_LEGACY:
            lines.append(
                f"{count} arquivo(s) com {len(header)} colunas — {PRE_GH104_VERDICT}"
            )
        else:
            lines.append(
                f"{count} arquivo(s) com {len(header)} colunas fora do contrato"
            )
        samples.append(f"{where}: {','.join(header)}")
    if csv_data.shape_mismatch:
        lines.append(
            f"{csv_data.shape_mismatch} linha(s) com número de campos diferente do cabeçalho "
            "(mantidas e contadas)"
        )
    for problem in csv_data.unreadable[:SAMPLE_LIMIT]:
        lines.append(f"ilegível: {problem}")
    return Gate(
        "G3",
        "cabeçalho do errors.csv com as 13 colunas da gh104",
        status,
        detail={
            "expected": list(ERRORS_CSV_HEADER),
            "observed": {",".join(h): c for h, c in csv_data.headers.items()},
            "shape_mismatch_rows": csv_data.shape_mismatch,
            "verdict": PRE_GH104_VERDICT
            if ERRORS_CSV_HEADER_LEGACY in csv_data.headers
            else "",
        },
        lines=lines,
        samples=samples,
    )


def gate_g4(csv_data: CsvReading) -> Gate:
    if csv_data.rows == 0:
        return Gate(
            "G4",
            f"unique_msg com {UNIQUE_PARTS} partes '{UNIQUE_SEPARATOR}'",
            SKIP,
            lines=["nenhuma linha de errors.csv para julgar"],
        )
    status = PASS if csv_data.unique_unparsed == 0 else FAIL
    lines = [
        f"não decompostos: {csv_data.unique_unparsed} de {csv_data.rows} "
        f"({_pct(csv_data.unique_unparsed, csv_data.rows)} %)",
        "distribuição de partes: "
        + ", ".join(
            f"{parts}→{count}" for parts, count in sorted(csv_data.unique_parts.items())
        ),
        "uma contagem != 7 conta como não decomposto e não é reinterpretada",
    ]
    return Gate(
        "G4",
        f"unique_msg com {UNIQUE_PARTS} partes '{UNIQUE_SEPARATOR}'",
        status,
        detail={
            "unparsed": csv_data.unique_unparsed,
            "rows": csv_data.rows,
            "parts_histogram": {str(k): v for k, v in sorted(csv_data.unique_parts.items())},
        },
        lines=lines,
        samples=csv_data.unique_samples.items,
    )


def gate_g5(
    csv_data: CsvReading, log_data: LogcatReading, vocab: CodeVocabulary
) -> Gate:
    """Envelope bem-formado — e, com catálogo, código que de fato existe.

    O código desconhecido reprova junto porque ele é deriva de proveniência: um envelope
    perfeito cujo código não está no `codes.csv` do conjunto sob medição significa que o
    APK carrega monitores de outro conjunto, e toda leitura a jusante estaria atribuindo
    a acusação à spec errada. Sem `--codes-csv` a pergunta não é respondível e o portão
    diz isso na linha, em vez de passar por omissão.
    """
    csv_unmatched = csv_data.envelope_absent + csv_data.envelope_malformed
    log_unmatched = log_data.envelope_absent + log_data.envelope_malformed
    unknown = csv_data.unknown_code + log_data.unknown_code
    status = (
        PASS if csv_unmatched == 0 and log_unmatched == 0 and unknown == 0 else FAIL
    )
    catalogo = (
        f"catálogo: {len(vocab.codes)} códigos de {vocab.source}"
        if vocab.authoritative
        else f"catálogo: ausente ({vocab.source}) — existência do código NÃO verificada"
    )
    return Gate(
        "G5",
        "toda mensagem casa o envelope v1",
        status,
        detail={
            "csv_matched": csv_data.envelope_matched,
            "csv_sentinel": csv_data.envelope_sentinel,
            "csv_absent": csv_data.envelope_absent,
            "csv_malformed": csv_data.envelope_malformed,
            "csv_unknown_code": csv_data.unknown_code,
            "logcat_matched": log_data.envelope_matched,
            "logcat_sentinel": log_data.envelope_sentinel,
            "logcat_absent": log_data.envelope_absent,
            "logcat_malformed": log_data.envelope_malformed,
            "logcat_unknown_code": log_data.unknown_code,
            "kinds": sorted(vocab.kinds),
            "codes_source": vocab.source,
            "codes_known": len(vocab.codes),
        },
        lines=[
            f"errors.csv : casam {csv_data.envelope_matched} · sentinela "
            f"{csv_data.envelope_sentinel} · sem envelope {csv_data.envelope_absent} · "
            f"malformados {csv_data.envelope_malformed} · código fora do catálogo "
            f"{csv_data.unknown_code}",
            f"logcat     : casam {log_data.envelope_matched} · sentinela "
            f"{log_data.envelope_sentinel} · sem envelope {log_data.envelope_absent} · "
            f"malformados {log_data.envelope_malformed} · código fora do catálogo "
            f"{log_data.unknown_code}",
            "KIND admitidos: " + ", ".join(sorted(vocab.kinds)),
            catalogo,
        ],
        samples=(
            csv_data.envelope_samples.items
            or log_data.envelope_samples.items
            or csv_data.unknown_code_samples.items
            or log_data.unknown_code_samples.items
        ),
    )


def gate_g6(csv_data: CsvReading, log_data: LogcatReading) -> Gate:
    total = csv_data.macro_event + log_data.macro_event + log_data.macro_anywhere
    status = PASS if total == 0 else FAIL
    return Gate(
        "G6",
        f"a macro {EVENTNAME_MACRO} nunca chega ao artefato",
        status,
        detail={
            "csv_ev_macro": csv_data.macro_event,
            "logcat_ev_macro": log_data.macro_event,
            "logcat_anywhere": log_data.macro_anywhere,
        },
        lines=[
            f"errors.csv com ev={EVENTNAME_MACRO}: {csv_data.macro_event}",
            f"logcat com ev={EVENTNAME_MACRO}: {log_data.macro_event}",
            f"logcat com {EVENTNAME_MACRO} em qualquer posição: {log_data.macro_anywhere}",
        ],
        samples=log_data.macro_samples.items or csv_data.macro_samples.items,
    )


def gate_g7(csv_data: CsvReading, log_data: LogcatReading) -> Gate:
    forbidden = Counter(csv_data.forbidden) + Counter(log_data.forbidden)
    truncated = csv_data.truncated + log_data.truncated
    status = PASS if not forbidden and truncated == 0 else FAIL
    return Gate(
        "G7",
        "caracteres proibidos e envelopes truncados",
        status,
        detail={
            "forbidden": dict(forbidden),
            "csv_truncated": csv_data.truncated,
            "logcat_truncated": log_data.truncated,
        },
        lines=[
            f"'{FORBIDDEN_NEWLINE}' literal: {forbidden.get(FORBIDDEN_NEWLINE, 0)}",
            f"'{FORBIDDEN_SEPARATOR}': {forbidden.get(FORBIDDEN_SEPARATOR, 0)}",
            f"envelopes truncados (aspa final não fechada): {truncated} "
            f"(csv {csv_data.truncated} · logcat {log_data.truncated})",
        ],
        samples=(
            csv_data.forbidden_samples.items
            or log_data.forbidden_samples.items
            or csv_data.truncated_samples.items
            or log_data.truncated_samples.items
        ),
    )


def gate_g8(csv_data: CsvReading) -> Gate:
    if csv_data.files == 0:
        return Gate("G8", "colunas code e event nunca vazias", SKIP,
                    lines=["nenhum errors.csv encontrado"])
    if not (csv_data.code_column_present and csv_data.event_column_present):
        return Gate(
            "G8",
            "colunas code e event nunca vazias",
            FAIL,
            detail={"code_column": csv_data.code_column_present,
                    "event_column": csv_data.event_column_present},
            lines=[
                "as colunas `code`/`event` não existem no cabeçalho — "
                f"{PRE_GH104_VERDICT}",
                "sem as colunas não há o que preencher com "
                f"`{SENTINEL}`, e a atribuição por evento é impossível",
            ],
        )
    status = PASS if csv_data.empty_code == 0 and csv_data.empty_event == 0 else FAIL
    return Gate(
        "G8",
        "colunas code e event nunca vazias",
        status,
        detail={"empty_code": csv_data.empty_code, "empty_event": csv_data.empty_event},
        lines=[
            f"`code` vazio: {csv_data.empty_code}",
            f"`event` vazio: {csv_data.empty_event}",
            f"ausência deve ser escrita como `{SENTINEL}`, nunca como célula vazia",
        ],
        samples=csv_data.empty_code_samples.items,
    )


def gate_g9(csv_data: CsvReading, log_data: LogcatReading) -> Gate:
    """Informativo por construção: a distribuição é para leitura humana, não veredito."""
    lines = ["spec × error_type × contagem:"]
    for (spec, error_type), count in csv_data.spec_error_type.most_common():
        lines.append(f"  {count:>8}  {spec} / {error_type}")
    codes = csv_data.codes or log_data.codes
    lines.append("code × contagem:")
    if codes:
        for code, count in codes.most_common():
            lines.append(f"  {count:>8}  {code}")
    else:
        lines.append("  (nenhum `code` no corpus)")
    return Gate(
        "G9",
        "distribuição para inspeção humana",
        PASS,
        detail={
            "spec_error_type": {
                f"{spec}/{error_type}": count
                for (spec, error_type), count in csv_data.spec_error_type.most_common()
            },
            "codes": dict(codes.most_common()),
        },
        lines=lines,
    )


def gate_g10(instrument: InstrumentReading) -> Gate:
    if not instrument.files:
        return Gate(
            "G10",
            f"{', '.join(WEAVE_COUNT_KEYS)} no {INSTRUMENT_RESULTS_NAME}",
            SKIP,
            lines=[
                f"nenhum {INSTRUMENT_RESULTS_NAME} nos containers — "
                "os contadores da tecelagem só existem na variante dexlib2",
            ],
        )
    status = PASS if not instrument.missing_keys else FAIL
    lines = [f"{len(instrument.files)} arquivo(s) lido(s)"]
    for key in WEAVE_COUNT_KEYS:
        lines.append(f"`{key}` presente em {instrument.counts[key]} entrada(s)")
    return Gate(
        "G10",
        f"{', '.join(WEAVE_COUNT_KEYS)} no {INSTRUMENT_RESULTS_NAME}",
        status,
        detail={"files": instrument.files, "present": dict(instrument.counts)},
        lines=lines,
        samples=instrument.missing_keys[:SAMPLE_LIMIT] + instrument.unreadable[:SAMPLE_LIMIT],
    )


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------


def report(gates: list[Gate], label: str, containers: list[Path],
           csv_data: CsvReading, log_data: LogcatReading) -> None:
    print("=" * 78)
    print(f"gh104 — portões de mensagens de violação · rótulo: {label}")
    print("=" * 78)
    print(f"containers   : {len(containers)}")
    for container in containers[:SAMPLE_LIMIT]:
        print(f"  {container}")
    if len(containers) > SAMPLE_LIMIT:
        print(f"  … mais {len(containers) - SAMPLE_LIMIT}")
    print(f"errors.csv   : {csv_data.files} arquivo(s), {csv_data.rows} linha(s)")
    print(
        f"logcat       : {log_data.files} arquivo(s), "
        f"{log_data.violation_lines} linha(s) RVSEC "
        f"({log_data.shape_bad} de forma inesperada, mantidas)"
    )
    for problem in (csv_data.unreadable + log_data.unreadable)[:SAMPLE_LIMIT]:
        print(f"  ilegível: {problem}")

    for gate in gates:
        print()
        print(f"[{gate.status}] {gate.gate_id} — {gate.title}")
        for line in gate.lines:
            print(f"    {line}")
        for sample in gate.samples[:SAMPLE_LIMIT]:
            print(f"    · {sample}")

    counts = Counter(gate.status for gate in gates)
    print()
    print("-" * 78)
    print(f"{counts[PASS]} PASS / {counts[FAIL]} FAIL / {counts[SKIP]} SKIP")
    print("-" * 78)


def build_document(gates: list[Gate], label: str, patterns: list[str],
                   containers: list[Path], csv_data: CsvReading,
                   log_data: LogcatReading) -> dict:
    counts = Counter(gate.status for gate in gates)
    return {
        "label": label,
        "results_glob": patterns,
        "containers": [str(container) for container in containers],
        "corpus": {
            "errors_csv_files": csv_data.files,
            "errors_csv_rows": csv_data.rows,
            "logcat_files": log_data.files,
            "logcat_violation_lines": log_data.violation_lines,
            "logcat_unexpected_shape": log_data.shape_bad,
            "unreadable": csv_data.unreadable + log_data.unreadable,
        },
        "summary": {"pass": counts[PASS], "fail": counts[FAIL], "skip": counts[SKIP]},
        "gates": [
            {
                "id": gate.gate_id,
                "title": gate.title,
                "status": gate.status,
                "detail": gate.detail,
                "lines": gate.lines,
                "samples": gate.samples[:SAMPLE_LIMIT],
            }
            for gate in gates
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verifica offline se as mensagens de violação da gh104 saíram "
        "como prometido numa campanha já gravada.",
    )
    parser.add_argument(
        "--results-glob",
        action="append",
        required=True,
        help="glob de diretórios de container (ou de campanha); pode repetir",
    )
    parser.add_argument("--label", default="sem-rótulo", help="nome deste run no relatório")
    parser.add_argument("--json", dest="json_path", help="grava o resultado estruturado")
    parser.add_argument(
        "--skip-logcat",
        action="store_true",
        help="lê só os errors.csv; G5/G6/G7 perdem a fonte da verdade das mensagens",
    )
    parser.add_argument(
        "--codes-csv",
        type=Path,
        help="codes.csv do conjunto sob medição (ex.: "
        "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv). "
        "Sem ele o G5 julga o KIND contra a lista congelada e não verifica se o "
        "código existe — que foi o defeito que fez este portão envelhecer",
    )
    args = parser.parse_args(argv)

    vocab = load_code_vocabulary(args.codes_csv)

    containers = resolve_containers(args.results_glob)
    if not containers:
        print(f"FALHA: nenhum container casou {args.results_glob}", file=sys.stderr)
        return 1

    csv_data = CsvReading()
    log_data = LogcatReading()
    instrument = InstrumentReading()

    for container in containers:
        errors_csv = container / ERRORS_CSV_NAME
        if errors_csv.is_file():
            read_errors_csv(errors_csv, csv_data, vocab)
        else:
            csv_data.unreadable.append(f"{errors_csv}: ausente")

        instrument_json = container / INSTRUMENT_RESULTS_NAME
        if instrument_json.is_file():
            read_instrument_results(instrument_json, instrument)

        if not args.skip_logcat:
            for logcat in sorted(container.rglob(f"*{LOGCAT_SUFFIX}")):
                read_logcat(logcat, log_data, vocab)

    gates = [
        gate_g1(csv_data, log_data),
        gate_g2(csv_data, log_data),
        gate_g3(csv_data),
        gate_g4(csv_data),
        gate_g5(csv_data, log_data, vocab),
        gate_g6(csv_data, log_data),
        gate_g7(csv_data, log_data),
        gate_g8(csv_data),
        gate_g9(csv_data, log_data),
        gate_g10(instrument),
    ]

    report(gates, args.label, containers, csv_data, log_data)

    if args.json_path:
        document = build_document(
            gates, args.label, args.results_glob, containers, csv_data, log_data
        )
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"json: {out}")

    return 1 if any(gate.status == FAIL for gate in gates) else 0


if __name__ == "__main__":
    sys.exit(main())
