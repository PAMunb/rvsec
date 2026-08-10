#!/usr/bin/env python3
"""Judge batch A: build juiz_claims_resolvidos_batchA.csv from the three agent CSVs
plus the judge's resolution map. Original columns preserved; four columns appended."""
import csv, pathlib

BATCH = pathlib.Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/audit/20260808_validacao_jca_android/batchA")
OUT = BATCH / "juiz_claims_resolvidos_batchA.csv"

# id -> (resolucao_juiz, classificacao_final, severidade_final, justificativa_curta)
R = {
 # ---- ALFA ----
 "ALFA-DHG-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","confirmada pelo walk do juiz (juiz_walk.py J1) sobre a tabela do artefato; indexacao MapOfMonitor por objeto verificada"),
 "ALFA-DHG-02": ("FAIL","INCORRETA (constraint extra-oraculo; supressao silenciosa sem carrier; sem registro)","critica","juiz executou J2 (3 reps): cadeia FP fim-a-fim confirmada; criterio pre-registro par.4 (FP em trace realizavel)"),
 "ALFA-DHG-03": ("FAIL","INCORRETA (ENSURES perdido gera FP inter-spec realizavel)","critica","J2 executado: PREPARED_DH negado e KPG emite UnsatisfiedConstraint para construcao oracle-legal; elo final nao e mais INFERIDO"),
 "ALFA-DHG-04": ("PASS","FIDELIDADE_DEMONSTRADA","minor","MapOfMonitor por objeto e identitySet verificados pelo juiz no artefato e no fonte"),
 "ALFA-DHG-05": ("FAIL","INCORRETA (acusacao deslocada e enganosa no leitor)","major","J2: mensagem emitida nega fato verdadeiro (construcao monitorada ocorreu); causa raiz inatribuivel"),
 "ALFA-DHG-06": ("FAIL","INCORRETA (registro descreve regra inexistente)","minor","conformance_record.csv:5 verificado pelo juiz: reason cita implicacao que a regra api30 nao contem"),
 "ALFA-HMC-01": ("FAIL","INCORRETA (inclusao L(CrySL) em alfa(L(MOP)) falha no artefato efetivo: monitor global)","critica","REVERTIDO de PASS: J3 executado pelo juiz (3 reps) da o trace separador - 2 construcoes legais -> InvalidSequenceOfMethodCalls; premissa 1-evento-por-instancia e falsa para HMC (Tuple2 estatico verificado); D-piloto-3 exige o automato efetivo incluindo indexacao"),
 "ALFA-HMC-02": ("FAIL","LIMITACAO_INEVITAVEL_DOCUMENTADA (spec vacua na plataforma; anomalia do oraculo derivado registrada)","major","0 entradas javax/xml/crypto no jar congelado verificado pelo juiz; vies do oraculo registrado (pre_registro par.1); nao excusa BETA-HMC-03"),
 "ALFA-HMC-03": ("PASS","FIDELIDADE_DEMONSTRADA","minor","outputLength sem clausula dependente na regra api30 (verificado); projecao anonima fiel"),
 "ALFA-HMC-04": ("PASS","FIDELIDADE_DEMONSTRADA","minor","constante/objeto do edge corretos (edges.csv:21 verificado); a negacao por-processo do 2o objeto e do fenomeno FEN-HMC-monitor-global (BETA-HMC-03), nao do shape do edge"),
 "ALFA-HMC-05": ("FAIL","INCORRETA (ciclo de vida por processo, nao por objeto)","critica","REVERTIDO de PASS: indexacao NAO e pelo objeto retornado - Tuple2 estatico unico (monitor :212-243 verificado pelo juiz); J3 executado; contraexemplo reproduzivel nao se descarta"),
 "ALFA-PBE-01": ("PASS","DIVERGENCIA_EQUIVALENTE_COMPROVADA (prefixo Kleene c3* registrado)","minor","walk do juiz confirma; divergence_record hunk 49b892006688 verificado"),
 "ALFA-PBE-02": ("PASS","FIDELIDADE_DEMONSTRADA","minor","transcricao 10000 + validate(RANDOMIZED,salt) verificada no .mop e .rvm pelo juiz"),
 "ALFA-PBE-03": ("FAIL","INCORRETA (misuse 3-args sem carrier: FN terminal silencioso; sem registro)","critica","aspecto verificado pelo juiz (advice 3-args chama so c2Event); Beta executou PBE-c (0 eventos 0 erros); registros varridos sem cobertura da lacuna"),
 "ALFA-PBE-04": ("FAIL","INCORRETA (mensagem contradiz o limiar implementado 10x)","minor","mop:50 vs :46 verificado; deteccao inalterada, remediacao enganada; atribuivel (spec+LOC)"),
 "ALFA-PBE-05": ("FAIL","INCORRETA (categoria UnsafeAlgorithm inconsistente com irmas)","minor","verificado mop:49 vs IVP/SKS UnsatisfiedConstraint; quebra estratificacao por categoria"),
 "ALFA-PBE-06": ("PASS","FIDELIDADE_DEMONSTRADA (write-no-read registrado espelha o oraculo)","minor","predicate_omissions.csv linha PREPARED_PBE verificada pelo juiz; nenhum consumidor api30"),
 "ALFA-PBE-07": ("PASS","FIDELIDADE_DEMONSTRADA","minor","mesma estrutura parametrica verificada (MapOfMonitor)"),
 "ALFA-IVP-01": ("PASS","DIVERGENCIA_EQUIVALENTE_COMPROVADA (prefixo Kleene registrado)","minor","walk do juiz confirma; hunk f4fe01f5b82c verificado"),
 "ALFA-IVP-02": ("PASS","DIVERGENCIA_EQUIVALENTE_COMPROVADA (conjuntos vacuos no join point after-returning)","minor","harness T1 MEDIDO + Beta IVP-e (inclui overflow) convergem; ameaca ART nomeada e mantida"),
 "ALFA-IVP-03": ("PASS","FIDELIDADE_DEMONSTRADA","minor","constantes/objetos verificados nas duas pontas; dupla acusacao espelha CrySL"),
 "ALFA-IVP-04": ("PASS","FIDELIDADE_DEMONSTRADA","minor","identidade e isolamento verificados"),
 "ALFA-SKS-01": ("PASS","DIVERGENCIA_EQUIVALENTE_COMPROVADA (prefixo Kleene registrado)","minor","walk do juiz confirma; hunk f0ffa75b48bc verificado"),
 "ALFA-SKS-02": ("FAIL","INCORRETA (whitelist extra-oraculo; FP realizavel; registrado nao e aprovado)","critica","regra api30 sem constraint de alg verificada pelo juiz; Beta executou SKS-b (UnsatisfiedConstraint emitido); sem reducao formal de escopo"),
 "ALFA-SKS-03": ("FAIL","INCORRETA (surrogate RANDOMIZED nao equivalente: produtores divergem do oraculo)","critica","edges.csv:66 present-surrogate sem prova de equivalencia; produtores do oraculo sao getEncoded (SecretKey/Key.cryptsl); FN e FP direcionais realizaveis; vies do oraculo registrado"),
 "ALFA-SKS-04": ("FAIL","INCORRETA (REQUIRES nao lido no caminho 4-args; FN realizavel; sem registro)","critica","c2/c4 sem validate(RANDOMIZED) verificado pelo juiz no .mop/.rvm/artefato; Beta executou SKS-c (GENERATED_KEY concedido, 0 erros)"),
 "ALFA-SKS-05": ("FAIL","OMITIDA (2a casa alg descartada na escrita; sem registro)","critica","setProperty binario verificado (ExecutionContext.java:102-120); leitores unarios; edges.csv:68 sem nota de casa; FEN-SET-generatedkey-2a-casa (= piloto ALFA-CIP-07 lado escritor)"),
 "ALFA-SKS-06": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA (segue bloqueando aderencia total)","minor","registro duplo verificado (omissions SPECCED_KEY; hunk 644c9b978750)"),
 "ALFA-SKS-07": ("PASS","FIDELIDADE_DEMONSTRADA","minor","transcricao exata em c2; harness T2 prova envelope da API; componente ausente nao avaliavel em c1"),
 "ALFA-SKS-08": ("PASS","FIDELIDADE_DEMONSTRADA","minor","identitySet vs equals-por-valor do SecretKeySpec verificado - caso de risco maximo correto"),
 "ALFA-SET-01": ("FAIL","INCORRETA (defeito de mecanismo do gerador; benigno no lote por idempotencia)","major","padrao verificado pelo juiz no dispatch (SKS :414-419); Beta exercitou ao vivo; precedente piloto: major como padrao set-wide"),
 "ALFA-SET-02": ("FAIL","INCORRETA (parser fail-open a parentese desbalanceado; exit 0)","major","balance -1 no fonte congelado + artefatos integros verificados; familia GAMA-GCM-01 do piloto (major como padrao)"),
 "ALFA-SET-03": ("FAIL","INCORRETA (oraculo derivado emite regra de classe ausente da API 30)","major","0 entradas no jar verificado pelo juiz; vies registrado, nao corrigido (pre_registro par.1)"),
 "ALFA-SET-04": ("FAIL","INCORRETA (propriedade set-wide refutada: HMC emite InvalidSequenceOfMethodCalls espurio)","critica","REVERTIDO de PASS: J3 executado pelo juiz - monitor global do HMC dispara @fail em trace legal; a propriedade vale apenas para as 4 specs parametrizadas"),
 # ---- BETA ----
 "BETA-DHG-01": ("PASS","FIDELIDADE_DEMONSTRADA (medicao da cadeia)","-","medicao limpa; artefatos byte-identicos verificados pelo juiz"),
 "BETA-DHG-02": ("PASS","FIDELIDADE_DEMONSTRADA","-","matcher de producao, particao exata, vizinhos livres"),
 "BETA-DHG-03": ("PASS","FIDELIDADE_DEMONSTRADA (artefato fiel ao .mop)","-","tabela verificada pelo juiz (J1); compoe com ALFA-DHG-01 sem conflito"),
 "BETA-DHG-04": ("FAIL","INCORRETA (canal @fail morto - higiene)","minor","AJUSTADO major->minor: sob o oraculo DHG nao existe trace violador por objeto (ORDER c1 unico) - o canal morto nada perde; difere do GCM piloto (la havia violacoes suprimidas sem canal vivo)"),
 "BETA-DHG-05": ("FAIL","INCORRETA (constraint extra-oraculo via supressao silenciosa)","critica","AJUSTADO major->critica: a ressalva de Beta (elo final nao executado) foi fechada pelo J2 do juiz (FP fim-a-fim, 3 reps); criterio pre-registrado par.4"),
 "BETA-HMC-01": ("PASS","FIDELIDADE_DEMONSTRADA (medicao da cadeia)","-","medicao limpa"),
 "BETA-HMC-02": ("FAIL","INCORRETA (regra api30 modela classe inexistente na plataforma declarada)","major","0 entradas verificado pelo juiz; convencao D-piloto-4 item 4 (medicao FAIL -> INCORRETA do oraculo/toolchain); complementar a ALFA-HMC-02 (unidade spec)"),
 "BETA-HMC-03": ("FAIL","INCORRETA (monitor global; FP em trace legal)","critica","re-executado pelo juiz (J3, 3 reps) sobre o artefato da rodada: errors=1 InvalidSequenceOfMethodCalls; 2o objeto sem PREPARED_HMAC; realizavel onde a classe existir"),
 "BETA-HMC-04": ("PASS","FIDELIDADE_DEMONSTRADA (tabela fiel ao ere; escopo do monitor no claim irmao)","-","escopo declarado tabela-vs-ere mantido (precedente piloto BETA-CIP-09); cross-ref obrigatorio a BETA-HMC-03"),
 "BETA-PBE-01": ("PASS","FIDELIDADE_DEMONSTRADA (medicao da cadeia)","-","medicao limpa"),
 "BETA-PBE-02": ("PASS","FIDELIDADE_DEMONSTRADA","-","particao exata; complementaridade das conditions provada em execucao"),
 "BETA-PBE-03": ("PASS","FIDELIDADE_DEMONSTRADA (artefato fiel ao .mop)","-","tabelas verificadas pelo juiz (J1)"),
 "BETA-PBE-04": ("FAIL","INCORRETA (FN terminal realizavel: violacao 3-args invisivel ponta a ponta)","critica","executado (PBE-c); advice 3-args com so c2Event verificado pelo juiz no aspecto; PREPARED_PBE sem leitor confirmado"),
 "BETA-PBE-05": ("FAIL","INCORRETA (canal @fail morto - higiene)","minor","AJUSTADO major->minor: PBE tem canal vivo proprio (c3) para as violacoes reais; ORDER por objeto nao viola; difere do GCM piloto"),
 "BETA-PBE-06": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA (write-no-read D-S14 registrado)","minor","registro verificado (omissions linha PREPARED_PBE); bloqueia aderencia total"),
 "BETA-PBE-07": ("FAIL","INCORRETA (mensagem contradiz o limiar)","minor","verificado no .mop/.rvm/artefato"),
 "BETA-IVP-01": ("PASS","FIDELIDADE_DEMONSTRADA (medicao da cadeia)","-","medicao limpa"),
 "BETA-IVP-02": ("PASS","FIDELIDADE_DEMONSTRADA","-","particao exata; overloads exaustivos"),
 "BETA-IVP-03": ("PASS","FIDELIDADE_DEMONSTRADA (artefato fiel ao .mop)","-","tabelas verificadas pelo juiz (J1)"),
 "BETA-IVP-04": ("PASS","DIVERGENCIA_EQUIVALENTE_COMPROVADA (lacuna inalcancavel via after-returning)","minor","executado (IVP-e, inclui overflow); converge com harness T1 de Alfa; ameaca ART nomeada"),
 "BETA-IVP-05": ("FAIL","INCORRETA (canal @fail morto - higiene)","minor","AJUSTADO major->minor: IVP tem canal vivo (c3/c4); mesma razao de BETA-PBE-05"),
 "BETA-IVP-06": ("PASS","FIDELIDADE_DEMONSTRADA (cadeia consistente apesar da dupla origem de nomes)","minor","nenhum consumidor chaveia no nome do arquivo; benigno e registrado"),
 "BETA-SKS-01": ("PASS","FIDELIDADE_DEMONSTRADA (medicao da cadeia)","-","medicao limpa"),
 "BETA-SKS-02": ("PASS","FIDELIDADE_DEMONSTRADA","-","particao exata; armadilha de nome simples coberta com imports de producao"),
 "BETA-SKS-03": ("PASS","FIDELIDADE_DEMONSTRADA (artefato fiel ao .mop)","-","tabelas verificadas pelo juiz (J1)"),
 "BETA-SKS-04": ("PASS","FIDELIDADE_DEMONSTRADA (condicao efetiva integra apesar da anomalia textual)","minor",".rvm:13 verificado pelo juiz: condicao pretendida integra; defeito do parser fica no claim de conjunto"),
 "BETA-SKS-05": ("FAIL","INCORRETA (REQUIRES abandonado no overload 4-args; FN realizavel)","critica","executado (SKS-c); ausencia de validate(RANDOMIZED) verificada pelo juiz"),
 "BETA-SKS-06": ("FAIL","INCORRETA (canal @fail morto - higiene)","minor","AJUSTADO major->minor: SKS tem canal vivo (c3/c4); mesma razao de BETA-PBE-05"),
 "BETA-SKS-07": ("FAIL","INCORRETA (whitelist extra-oraculo; FP realizavel vs oraculo cru)","critica","executado (SKS-b); registrado nao e aprovado (precedente piloto)"),
 "BETA-SKS-08": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA (write-no-read D-S14 registrado)","minor","registro verificado; a alegada contradicao do registro cai (ver BETA-SET-07)"),
 "BETA-SET-01": ("PASS","FIDELIDADE_DEMONSTRADA","-","20/20 byte-identicos re-verificados pelo juiz por hash; determinismo (nao replicacao) declarado"),
 "BETA-SET-02": ("FAIL","INCORRETA (gerador aceita spec com parametro nao ligado sem warning -> monitor global)","major","fato verificado pelo juiz (Tuple2 no artefato; exit 0 limpo no manifesto); FP do exemplar e critico e esta em BETA-HMC-03"),
 "BETA-SET-03": ("FAIL","INCORRETA (exit 0 com MOPException e zero artefatos)","minor","AJUSTADO major->minor: pipeline de producao compensa - stderr nao-vazio vira CommandException (rv_android_core/util/utils.py:41-52, verificado pelo juiz; precedente piloto BETA-SET-04); residual: chamadores com skip_stderr nao auditados"),
 "BETA-SET-04": ("FAIL","INCORRETA (fail-open de simbolo indefinido no ERE)","major","reproducao primaria do fenomeno GAMA-GCM-01 do piloto (la: minor na instancia, major como padrao); aqui reivindicado como padrao -> major"),
 "BETA-SET-05": ("FAIL","INCORRETA (parse tolerante a ')' excedente sem diagnostico)","major","AJUSTADO minor->major: harmonizado com ALFA-SET-02 (mesmo fenomeno FEN-SET-failopen-parser, reivindicado como padrao de conjunto); instancia SKS segue benigna (BETA-SKS-04 PASS)"),
 "BETA-SET-06": ("FAIL","INCORRETA (flags obsoletas re-executam handler; exercitado a cada construcao)","major","prova executavel (PBE-a-stale/SKS-a-stale) + padrao verificado pelo juiz no dispatch; benigno no lote (idempotencia)"),
 "BETA-SET-07": ("PASS","FIDELIDADE_DEMONSTRADA (registro coerente sob a semantica declarada de baseline)","minor","REVERTIDO de FAIL: README.md:17-18 declara predicate_edges como baseline pre-reparo 'kept as authored' (verificado pelo juiz); as 'contradicoes' sao a semantica declarada; mesma rota que levou Gama a retirar a suspeita (GAMA-SKS-05); residual: atrito de leitura, nao defeito"),
 "BETA-SET-08": ("PASS","FIDELIDADE_DEMONSTRADA (matching insensivel a anomalia de resolucao do jar p/ este lote)","minor","ctor sets identicos 30/36/37.0; pendencia do android-36 do container mantida aberta"),
 "BETA-SET-09": ("INCONCLUSIVE","INCONCLUSIVA (exige weave+device; fase G6/G10)","-","pendencia nomeada; fora do denominador; nada convertido em PASS"),
 # ---- GAMA ----
 "GAMA-DHG-01": ("FAIL","INCORRETA (supressao de trace oracle-conforme; FP deslocado no leitor KPG)","critica","pendencia G10-DHG-1 fechada pelo juiz: J2 executado (3 reps) - FP fim-a-fim com a mensagem prevista; viola par.13 (trace aceito pelo oraculo rejeitado pelo conjunto)"),
 "GAMA-DHG-02": ("FAIL","OMITIDA (divergencia critica sem registro em nenhum artefato gh101)","major","varredura re-executada pelo juiz: divergence_record sem linha DHG; conformance_record:5 descreve a ancora 1.5.2 sem declara-lo"),
 "GAMA-DHG-03": ("PASS","FIDELIDADE_DEMONSTRADA (nenhum unknown emissivel; sem cascata __RESET)","minor","DHG e parametrizado (verificado) - a prova por-objeto vale; contraste com HMC onde a mesma premissa falhou"),
 "GAMA-HMC-01": ("FAIL","INCORRETA (spec vacua na plataforma; leitor MacSpec vira acusacao garantida)","major","0 entradas verificado pelo juiz; ausencia de registro confirmada; vies do oraculo registrado"),
 "GAMA-HMC-02": ("FAIL","INCORRETA (@fail NAO e morto no HMC: monitor global dispara espurio com expecting=unknown em trace legal)","major","REVERTIDO de PASS: premissa 'indexado pelo objeto' e falsa para HMC (Tuple2 verificado); J3 do juiz emite InvalidSequenceOfMethodCalls expecting=unknown; criticidade do fenomeno em BETA-HMC-03"),
 "GAMA-PBE-01": ("FAIL","OMITIDA (construtor 3-args sem ramo violador: silencio total)","critica","executado por Beta (PBE-c); aspecto verificado pelo juiz; pendencia de atribuicao de dimensao (captura vs bindings) registrada por D-piloto-4 item 1 - mantida como criada"),
 "GAMA-PBE-02": ("FAIL","INCORRETA (mensagem falsa 10x + categoria trocada + clausulas confladas)","major","literais verificados pelo juiz no .mop e artefato; agregado das tres deficiencias sustenta major no gate G9"),
 "GAMA-PBE-03": ("PASS","FIDELIDADE_DEMONSTRADA (reparo layer-2 efetivo)","minor","walk do juiz: c3 {0,2,2}, report antes de handleEvent, flags false"),
 "GAMA-PBE-04": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA (registro exato)","minor","omissions linha PREPARED_PBE verificada"),
 "GAMA-PBE-05": ("FAIL","OMITIDA (lacuna 3-args sem classificacao em registro)","major","varredura confirmada pelo juiz (hunk 49b892006688 cobre so o reparo c3)"),
 "GAMA-IVP-01": ("PASS","FIDELIDADE_DEMONSTRADA (reparo layer-2 efetivo)","minor","walk do juiz confirma"),
 "GAMA-IVP-02": ("FAIL","INCORRETA (expecting=unknown no unico canal de report)","major","verificado pelo juiz: mop:48/55 3-args; ErrorDescription.java:34-36; artefato :222/:239; gate G9 pre-registrado 'sem unknown' violado em caminho realizavel"),
 "GAMA-IVP-03": ("PASS","DIVERGENCIA_EQUIVALENTE_COMPROVADA (zona de supressao inalcancavel via after-returning)","minor","RESOLVIDO de INCONCLUSIVE: a realizabilidade foi respondida por dois harnesses executados na rodada (Alfa T1a-T1d; Beta IVP-e inclusive overflow) - todas as formas lancam; ameaca ART nomeada e mantida (mesmo status de ALFA-IVP-02)"),
 "GAMA-IVP-04": ("FAIL","OMITIDA (conjuntos extras sem classificacao em registro)","major","varredura confirmada (so hunk f4fe01f5b82c); criterio pre-registrado par.4 'divergencia sem classificacao' e precedente REF-05 do piloto mantem major mesmo com impacto provado nulo"),
 "GAMA-SKS-01": ("FAIL","INCORRETA (REQUIRES ausente do caminho 4-args; FN + lavagem de predicado)","critica","executado por Beta (SKS-c); artefato verificado pelo juiz; leitores GENERATED_KEY conferidos"),
 "GAMA-SKS-02": ("FAIL","INCORRETA (mensagens confladas/garbled; atribuicao por clausula impossivel)","minor","literais verificados; atribuivel a spec+sitio (mitigante)"),
 "GAMA-SKS-03": ("FAIL","INCORRETA (parser fail-open; instancia sem dano)","minor","balance -1 verificado; semantica preservada no .rvm:13; padrao de conjunto em ALFA-SET-02/BETA-SET-05"),
 "GAMA-SKS-04": ("PASS","FIDELIDADE_DEMONSTRADA (reparo layer-2 efetivo)","minor","walk do juiz confirma"),
 "GAMA-SKS-05": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA (registros coerentes sob baseline declarado)","minor","README.md:17-18 verificado pelo juiz; resolucao espelhada em BETA-SET-07 (revertido)"),
 "GAMA-SET-08": ("FAIL","INCORRETA (flags obsoletas re-executam @match apos monitorCall suprimido)","major","AJUSTADO minor->major: harmonizado ao fenomeno FEN-SET-flags-obsoletas (piloto: major como padrao set-wide; Beta provou disparo em TODA construcao valida); benigno no lote"),
 "GAMA-SET-09": ("FAIL","INCORRETA (caminho estatico cego a eventos de construtor)","major","verificado pelo juiz: DumpVisitor.java:600 imprime 'new'; TargetResolver.java:53 equals com '<init>' do Soot; nenhuma normalizacao no client (grep); extractor executado: 8/8 alvos name=new; G12 inatingivel para o lote"),
 "GAMA-SET-10": ("PASS","FIDELIDADE_DEMONSTRADA (nenhum conteudo do app chega ao logger pelas 5 specs)","minor","todos os addError alcancaveis conferidos pelo juiz nos artefatos: literais ou 3-args; residual __LOC/SourceFile nomeado"),
 "GAMA-SET-11": ("INCONCLUSIVE","INCONCLUSIVA (zero historico nao atribuivel sem replay)","major","juiz re-verificou: 0 tokens no errors.csv congelado (hash conferido); hipoteses e 3 testes discriminantes nomeados ficam abertos"),
}

rows = []
for name in ["alfa_claims.csv", "beta_claims.csv", "gama_claims.csv"]:
    with open(BATCH / name, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        header = rd.fieldnames
        for row in rd:
            rid = row["id"]
            res = R[rid]
            row["resolucao_juiz"], row["classificacao_final"], row["severidade_final"], row["justificativa_curta"] = res
            rows.append(row)

out_header = header + ["resolucao_juiz", "classificacao_final", "severidade_final", "justificativa_curta"]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out_header, quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    w.writerows(rows)
print(f"wrote {OUT} with {len(rows)} claims")
assert len(rows) == 96, len(rows)
