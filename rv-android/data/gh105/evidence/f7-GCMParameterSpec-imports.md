# Tarefa 10.7 — o arquivo que compilava por empréstimo, e o que o monitor gerado mostra

**Data**: 2026-08-25 · **Grupo**: 10.A (não muda o que é acusado)
**Arquivo**: `rvsec-mop/src/main/resources/jca_android/GCMParameterSpecSpec.mop`

## O defeito

O `GCMParameterSpecSpec.mop:22` declara a lista de valor da regra:

```java
List<Integer> validLengths = Arrays.asList(96, 104, 112, 120, 128);
```

e o arquivo não importava nem `java.util.List` nem `java.util.Arrays`. Isso nunca quebrou porque
o javamop funde as 23 especificações num monitor só e o bloco de imports do arquivo gerado é a
união dos blocos de todos: o `IvChainJunction.mop:8-9` importa os dois, e o `GCMParameterSpecSpec`
compilava com os imports que o vizinho contribuía.

A fragilidade é de dependência, não de sintaxe: quem editar, mover ou remover o outro arquivo
derruba este, e o erro aparece a quilômetros de distância -- no monitor fundido, não na
especificação que faltava o import. É a mesma classe que quebrou a 11.9 duas vezes e a razão de
existir da regra de imports por arquivo do `README.md`.

## O reparo

Dois imports no estilo uniforme do conjunto -- bloco JDK primeiro, `java.*` antes de `javax.*`,
linha em branco antes do bloco `br.unb.cic.mop` -- exatamente como o `IvChainJunction.mop` e o
`MessageDigestSpec.mop` já escrevem:

```java
package mop;

import java.util.Arrays;
import java.util.List;
import javax.crypto.spec.GCMParameterSpec;

import br.unb.cic.mop.eh.*;
```

## O que o monitor gerado diz

Geração completa do conjunto pelo pipeline real, antes e depois, e diff byte a byte dos dois
artefatos:

```
$ diff <antes>/MultiSpec_1RuntimeMonitor.java <depois>/MultiSpec_1RuntimeMonitor.java
19a20,21
> import java.util.Arrays;
> import java.util.List;
23,24d24
< import java.util.Arrays;
< import java.util.List;
```

O `MultiSpec_1MonitorAspect.aj` traz o mesmo diff, linha por linha. **Não é sequer uma adição**: os
dois imports já estavam no monitor, contribuídos pelo `IvChainJunction`, e o que muda é a posição
deles no bloco -- sobem porque o `GCMParameterSpecSpec` é processado antes. Fora dessas duas
linhas, os 17 mil e tantos do monitor são idênticos: nenhuma transição, nenhum corpo de evento,
nenhum sítio de report se move. O conjunto acusa exatamente os mesmos programas que acusava.

## Registro

`divergence_record.csv`, hunk `f4cae18baba1`, espécie `allow-list` -- o precedente são as linhas
74, 91 e 134, que arquivam sob a mesma espécie o import do `ConscryptAliasTable` porque ele existe
para servir a lista de valor. Aqui é a mesma relação: `Arrays` e `List` existem para a lista de
comprimentos de tag que transcreve a cláusula CONSTRAINTS da regra.

## O que o reparo moveu além dos imports

Nada no monitor, e sete linhas no `codes.csv`. Dois imports acima de todo o corpo do arquivo
deslocam cada sítio de report em duas linhas, e o `code-anchor` da tarefa 7.2 -- que compara o
`file_line` de cada linha da tabela com a linha de onde o código é realmente emitido -- acusou os
sete de uma vez: `GCMPARAMETERSPEC-CONSTR-00/01/02/03`, `-NOBS-00/01` e `-ORDER-00`. As âncoras
foram reancoradas (+2) e o portão de mensagem fecha em `{}`. É exatamente o serviço que a 7.2
descreve: as duas vezes em que um lote reancorou arquivo por script, moveu âncora que ninguém tinha
notado.
