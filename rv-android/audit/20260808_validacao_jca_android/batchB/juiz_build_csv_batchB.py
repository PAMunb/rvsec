#!/usr/bin/env python3
"""JUDGE batch B — builds juiz_claims_resolvidos_batchB.csv.

Reads the three agent CSVs (alfa 45, beta 52, gama 36 = 133 claims), preserves
every original column, and appends the judge's five columns:
resolucao_juiz, classificacao_final, severidade_final, justificativa_curta,
fenomeno_id_final.

rev. 2 (REF-C-02 remediation): `fenomeno_id_final` is a JUDGE column carrying
the phenomenon linkage for the machine-readable record (D-piloto-4 item 3):
the agent's own fenomeno_id where the agent filed one (original cells stay
untouched), and the judge's assignment for the 7 FAIL rows the agents left
blank (assignments below in FEN_BACKFILL, matching synthesis §1/§2).

Every resolution below is grounded in the judge's own evidence of this session
(J1-B walk, J2-B drive 3 reps, source/register verifications) — see
juiz_sintese_batchB.md §0/§2.
"""
import csv, os, sys

AUD = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/audit/20260808_validacao_jca_android/batchB"

# id -> (resolucao, classificacao_final, severidade_final, justificativa_curta)
R = {
 # ---------------- ALFA ----------------
 "ALFA-CIS-01": ("FAIL","INCORRETA","critica","Confirmado; juiz J2a: 2o stream legal -> 3 InvalidSeq espurios (3 reps identicas); monitor estatico global verificado (RuntimeMonitor:275)"),
 "ALFA-CIS-02": ("FAIL","INCORRETA","critica","Confirmado; juiz J2b executou o FP; generatedCipher em 0/33 regras api30 (grep do juiz); divergence_record:2 afirma um REQUIRES que a regra api30 nao tem; registrado != aprovado"),
 "ALFA-CIS-03": ("FAIL","OMITIDA","major","Confirmado; evento c1(is) da regra sem pointcut; ctor protected verificado em bytes extraidos pelo juiz; omissao de clausula sem registro = major (pre_registro par.4)"),
 "ALFA-CIS-04": ("FAIL","OMITIDA","major","Confirmado; len>off sem contraparte (corpo r2 vazio verificado); 0 hits em registros (grep do juiz); vies do oraculo anotado"),
 "ALFA-CIS-05": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA","minor","Confirmado; predicate_omissions:19 lido pelo juiz; sem consumidor no oraculo; segue bloqueando aderencia total"),
 "ALFA-CIS-06": ("FAIL","INCORRETA","major","Confirmado; J2a: todos os registros da cascata com expecting=unknown; criterio G9 'nenhum unknown'"),
 "ALFA-CIS-07": ("FAIL","OMITIDA","minor","Confirmado; sem canal de fim-de-trace; nao e clausula da regra -> minor mantido; padrao anotado para registro"),
 "ALFA-CIS-08": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado no plano da linguagem; a perda do 2o disjunto no dexlib2 e unidade toolchain separada (BETA-CIS-04) - claims compoem"),
 "ALFA-COS-01": ("FAIL","INCORRETA","critica","Confirmado; juiz J2c executou a cascata COS diretamente (3 espurios no 2o ciclo legal)"),
 "ALFA-COS-02": ("FAIL","INCORRETA","critica","Confirmado; juiz J2c executou as DUAS direcoes: ciclo sem write aceito (FN) e flush-after-close acusado (FP)"),
 "ALFA-COS-03": ("FAIL","INCORRETA","critica","Confirmado; mecanismo identico ao CIS-02 (verificado em .mop/artefato); FP executado no gemeo CIS (J2b)"),
 "ALFA-COS-04": ("FAIL","OMITIDA","major","Confirmado; como CIS-03"),
 "ALFA-COS-05": ("FAIL","OMITIDA","major","Confirmado; como CIS-04"),
 "ALFA-COS-06": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA","minor","Confirmado; predicate_omissions:20 lido pelo juiz"),
 "ALFA-COS-07": ("FAIL","INCORRETA","major","Confirmado; J2c: registros unknown"),
 "ALFA-COS-08": ("FAIL","OMITIDA","minor","Confirmado; como CIS-07"),
 "ALFA-KPR-01": ("FAIL","INCORRETA","critica","Confirmado; juiz J2d: primeiro getPublic de par gerado -> InvalidSeq espurio; co? verificado na regra (:27); sem registro (grep do juiz)"),
 "ALFA-KPR-02": ("FAIL","INCORRETA","critica","Confirmado; juiz J2e: 2a construcao legal falha + contaminacao; despacho fatia-vazia verificado (:306-355); AbstractSynchronizedMonitor (:127)"),
 "ALFA-KPR-03": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; constantes/objetos verificados; J2f mensagens especificas por clausula; colapso de dedupe adjudicado em GAMA-KPR-04"),
 "ALFA-KPR-04": ("FAIL","INCORRETA","minor","Confirmado por leitura (guards null .mop:32/:36); FN realizavel; ressalva da semantica CrySL sobre null mantida"),
 "ALFA-KPR-05": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; walk do juiz: getters intercalados legais; leitura A (D-piloto-1)"),
 "ALFA-KPR-06": ("FAIL","INCORRETA","critica","Confirmado; J2e: getPublic de kp2 falha apos seu proprio c1 legal (broadcast+reset)"),
 "ALFA-KPR-07": ("FAIL","INCORRETA","major","Confirmado; unknown executado; @match marca null executado pelo juiz (mecanismo preciso = local sombreado, GAMA-KPR-03; efeito liquido igual ao alegado)"),
 "ALFA-KPR-08": ("FAIL","OMITIDA","major","Confirmado; nenhuma linha KeyPairSpec.c1 em registro algum (greps do juiz); assinatura do censo presente no artefato (design.md:190 verificado)"),
 "ALFA-SKY-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; walk do juiz: estados aceitantes {0,1} = ge* d? incl. epsilon"),
 "ALFA-SKY-02": ("FAIL","INCORRETA","critica","Confirmado; J2g: RANDOMIZED negado a chave legal do oraculo; regra sem REQUIRES (verificado); sem registro"),
 "ALFA-SKY-03": ("FAIL","OMITIDA","critica","Confirmado; J2g: duas violacoes realizaveis do ORDER -> 0 registros; carve-out do dead-@fail do batch A inaplicavel (ha traces violadores e nenhum canal)"),
 "ALFA-SKY-04": ("FAIL","INCORRETA","critica","Confirmado; edges:64 present-surrogate sem prova de equivalencia (verificado); lado escritor do FEN-SKS-SURROGATE; severidade do batch A mantida"),
 "ALFA-SKY-05": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; MapOfMonitor por objeto (:225) e remove por instancia verificados"),
 "ALFA-SKY-06": ("FAIL","OMITIDA","minor","Confirmado; linha 83 lida pelo juiz: afirma um 'fails' inobservavel (sem @fail) e nao anota a inalcancabilidade via gate"),
 "ALFA-SKY-07": ("INCONCLUSIVE","INCONCLUSIVA","minor","Mantido; matching ajc de interface nao medido (sem ajc no host); metade dexlib2 medida por Beta (inerte em todos os owners); pendencia G6"),
 "ALFA-PBK-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; walk c1,c2 -> match"),
 "ALFA-PBK-02": ("FAIL","INCORRETA","critica","Confirmado; J2h: caso canonico de senha digitada acusado + SPECCED_KEY negado; regra exige randomized[salt] apenas (verificado); sem registro"),
 "ALFA-PBK-03": ("FAIL","INCORRETA","critica","Confirmado; J2h: clearPassword legal apos construcao acusada -> InvalidSeq espurio (residuo adiado, classe D-S10)"),
 "ALFA-PBK-04": ("FAIL","INCORRETA","major","Confirmado; walk f1,c2 -> fail; continuacao FORBIDDEN=>c1 nao honrada; metade deteccao escopada em BETA-PBK-08"),
 "ALFA-PBK-05": ("FAIL","OMITIDA","major","Confirmado; escrita unaria verificada; edges:55 cego ao slot; sem leitor vivo (registro row 10) mantem latente/major"),
 "ALFA-PBK-06": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA","minor","Confirmado; registro README verificado pelo juiz (incl. a propria nota de enumeracao faltante)"),
 "ALFA-PBK-07": ("FAIL","INCORRETA","major","Confirmado; mensagem '>= 1000' vs guard 10000 medida (J2i); FORBIDDEN miscategorizado; unknown no @fail"),
 "ALFA-PBK-08": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; particao de guards exata (complemento verificado); por-objeto"),
 "ALFA-PBK-09": ("FAIL","OMITIDA","minor","Confirmado; como CIS-07"),
 "ALFA-PBK-10": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; constante/objeto/escopo verificados; J2h sem err3 com salt marcado"),
 "ALFA-SET-05": ("FAIL","INCORRETA","major","Confirmado; geracao exit-0 registrada + defeitos no artefato verificados; familia aceitacao-silenciosa"),
 "ALFA-SET-06": ("FAIL","INCORRETA","major","Confirmado; generatedCipher em nenhuma regra api30 (grep do juiz); registros afirmam o oraculo errado; sem reducao de escopo em arquivo"),
 "ALFA-SET-07": ("FAIL","INCORRETA","major","Confirmado; censo chaveado em AbstractSynchronizedMonitor (design.md:190 verificado); CIS/COS AtomicMonitor global invisivel ao censo; KPR sem registro"),
 "ALFA-SET-08": ("FAIL","INCORRETA","major","Confirmado; J2 executou unknown nos 4 canais @fail vivos; SKY sem canal"),
 # ---------------- BETA ----------------
 "BETA-CIS-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; medicao G2 limpa; regeneracao byte-identica"),
 "BETA-CIS-02": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado como claim ESCOPADO tabela-vs-ere (precedente BETA-CIP-09); comparacao com CrySL em BETA-CIS-03"),
 "BETA-CIS-03": ("FAIL","INCORRETA","critica","Confirmado; juiz J2a re-executou a cascata"),
 "BETA-CIS-04": ("FAIL","INCORRETA","critica","Confirmado; juiz verificou findFirstCall (WrapperEmitter:517-524) + INV-INS-66 (DexWeaver:501-514) na fonte; medicao cis_readB UNTOUCHED conferida"),
 "BETA-CIS-05": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; weave de producao exato nos demais pointcuts; vizinhos livres"),
 "BETA-CIS-06": ("FAIL","OMITIDA","major","Confirmado; severidade harmonizada minor->major: clausula (evento c1 da regra) OMITIDA sem registro = major (pre_registro par.4); nota de raridade mantida"),
 "BETA-CIS-07": ("FAIL","OMITIDA","major","Confirmado; drive CIS-e + leitura do juiz (corpo vazio)"),
 "BETA-CIS-08": ("FAIL","INCORRETA","critica","REVERTIDO PASS->FAIL: a premissa 'REQUIRES da regra' e falsa para o oraculo api30 congelado (sem secao REQUIRES; generatedCipher 0/33 - verificado pelo juiz); leitor mecanicamente correto de clausula extra-oraculo = INCORRETA (precedente DHG batch A); FP executado (J2b)"),
 "BETA-CIS-09": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA","minor","Confirmado; registro verificado"),
 "BETA-COS-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado"),
 "BETA-COS-02": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado (escopado tabela-vs-ere)"),
 "BETA-COS-03": ("FAIL","INCORRETA","critica","Confirmado; severidade harmonizada major->critica: FN executado (tambem pelo juiz, J2c); par.4 nao tem carve-out de raridade"),
 "BETA-COS-04": ("FAIL","INCORRETA","critica","Confirmado; J2c cascata executada pelo juiz"),
 "BETA-COS-05": ("FAIL","INCORRETA","critica","Confirmado; mesmo mecanismo firstcall verificado na fonte; cos_writeB UNTOUCHED conferido"),
 "BETA-COS-06": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado"),
 "BETA-COS-07": ("FAIL","OMITIDA","major","Confirmado"),
 "BETA-COS-08": ("PASS","LIMITACAO_INEVITAVEL_DOCUMENTADA","minor","Confirmado"),
 "BETA-COS-09": ("FAIL","INCORRETA","critica","REVERTIDO PASS->FAIL: como BETA-CIS-08 (mesma premissa falsa sobre o oraculo api30)"),
 "BETA-COS-10": ("FAIL","OMITIDA","major","Confirmado; harmonizado minor->major como BETA-CIS-06"),
 "BETA-KPR-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado"),
 "BETA-KPR-02": ("FAIL","INCORRETA","critica","Confirmado; J2d re-executado pelo juiz"),
 "BETA-KPR-03": ("FAIL","INCORRETA","critica","Confirmado; J2e re-executado pelo juiz"),
 "BETA-KPR-04": ("FAIL","INCORRETA","major","Confirmado como claim de MECANISMO do gerador (padrao latente); instancia inerte = GAMA-KPR-03 minor; probe null executado pelo juiz"),
 "BETA-KPR-05": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; weave exato"),
 "BETA-KPR-06": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; arestas executadas; write-no-read registrado (row 3 verificado)"),
 "BETA-KPR-07": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado (escopado tabela-vs-ere)"),
 "BETA-SKY-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado"),
 "BETA-SKY-02": ("FAIL","INCORRETA","critica","Confirmado; juiz verificou os 3 mecanismos na fonte (methods() declared-only; literalFallback so-estatico; INV-INS-66) + fato de plataforma (interface sem metodos declarados, javap do juiz) + medicao 0 wrappers/7 owners UNTOUCHED conferida; informa G5 (metade dexlib2); ajc/ART pendencias nomeadas"),
 "BETA-SKY-03": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; walk do juiz + sonda p6 discriminante"),
 "BETA-SKY-04": ("FAIL","INCORRETA","critica","Confirmado; J2g re-executado pelo juiz"),
 "BETA-SKY-05": ("FAIL","INCORRETA","critica","Confirmado; harmonizado major->critica: FN executado das duas violacoes do ORDER sem canal algum (J2g); par.4"),
 "BETA-SKY-06": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; NEGATES por objeto executado"),
 "BETA-SKY-07": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; negativa de colisao/double-fire fechada nas 3 frentes (checagem explicita da rodada)"),
 "BETA-PBK-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado"),
 "BETA-PBK-02": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; captura exaustiva na API 30"),
 "BETA-PBK-03": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado (escopado); por-objeto verificado"),
 "BETA-PBK-04": ("FAIL","INCORRETA","critica","Confirmado; J2h re-executado pelo juiz"),
 "BETA-PBK-05": ("FAIL","INCORRETA","major","Confirmado; harmonizado minor->major: FEN-PBE-MSG-1000, severidade do fenomeno no batch A; mensagem falsa 10x medida pelo juiz (J2i)"),
 "BETA-PBK-06": ("FAIL","INCORRETA","critica","Confirmado; harmonizado major->critica: J2h mostra o residuo disparando tambem em trace conforme ao oraculo; o registro afirma violacao de sequencia que nao ocorreu; par.4"),
 "BETA-PBK-07": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado escopado (arestas executadas); correcao: o descarte do slot NAO esta registrado (edges:55 cego ao slot) - so a ausencia de leitor esta (row 10); omissao do slot adjudicada em ALFA-PBK-05"),
 "BETA-PBK-08": ("PASS","DIVERGENCIA_EQUIVALENTE_COMPROVADA","minor","Confirmado ESCOPADO a metade deteccao (1 report por ctor proibido); a continuacao =>c1 nao honrada e adjudicada em ALFA-PBK-04/BETA-PBK-06"),
 "BETA-SET-01": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; 20/20 byte-identicos re-verificados pelo juiz contra o manifesto"),
 "BETA-SET-02": ("FAIL","INCORRETA","critica","Confirmado; findFirstCall verificado na fonte pelo juiz; consequencia medida em CIS/COS"),
 "BETA-SET-03": ("FAIL","INCORRETA","critica","Confirmado; 3 mecanismos verificados na fonte pelo juiz; efeito integral medido no SKY"),
 "BETA-SET-04": ("FAIL","INCORRETA","major","Confirmado; keying por owner exato + expansao so-APK verificados na fonte (DexWeaver:207-231); reducao de escopo sem registro"),
 "BETA-SET-05": ("FAIL","INCORRETA","major","Confirmado; aceitacao silenciosa de spec sem parametro; FP provado (J2a/J2c)"),
 "BETA-SET-06": ("FAIL","INCORRETA","major","Confirmado; aceitacao silenciosa de binding parcial; dano provado (J2e)"),
 "BETA-SET-07": ("FAIL","INCORRETA","major","Confirmado; ErrorSummary sem expecting + equals/hashCode verificados na fonte pelo juiz; colapso executado (J2f/J2i)"),
 "BETA-SET-08": ("FAIL","INCORRETA","minor","Confirmado como observacao estatica com realizabilidade medida (destroy lanca); ART pendente; minor mantido"),
 "BETA-SET-09": ("FAIL","INCORRETA","major","Confirmado; sondas medidas; p3 (orfao all-fail) e p6 (epsilon muda aceitacao) sao formas NOVAS alem do repertorio batch A"),
 "BETA-SET-10": ("PASS","FIDELIDADE_DEMONSTRADA","minor","REVERTIDO FAIL->PASS pelo precedente batch A BETA-SET-07: README:17-18 (re-verificado pelo juiz) declara predicate_edges.csv baseline pre-reparo 'kept as authored'; as 7 linhas citadas sao essa semantica declarada, nao registros obsoletos; atrito residual anotado"),
 "BETA-SET-11": ("INCONCLUSIVE","INCONCLUSIVA","minor","Mantido; weave ajc + execucao ART/device = fase G6/G10; pendencias nomeadas"),
 # ---------------- GAMA ----------------
 "GAMA-CIS-01": ("FAIL","INCORRETA","critica","Confirmado; juiz J2a re-executou a cascata (3 espurios, locs distintos)"),
 "GAMA-CIS-02": ("FAIL","INCORRETA","major","Confirmado; J2a: unknown em todos os registros do canal vivo"),
 "GAMA-CIS-03": ("FAIL","OMITIDA","major","Confirmado; ausencia de registro re-verificada pelo juiz (greps proprios)"),
 "GAMA-CIS-04": ("FAIL","OMITIDA","major","Confirmado; corpo r2 vazio verificado; tabela 4.11 nao lista CIS/COS"),
 "GAMA-CIS-05": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado ESCOPADO a mecanica diagnostica (report especifico sozinho, J2b); a natureza extra-oraculo da clausula e adjudicada no FEN-SET-GENCIPHER-EXTRA"),
 "GAMA-CIS-06": ("INCONCLUSIVE","INCONCLUSIVA","minor","Mantido; realizabilidade do fluxo subclasse nao medida; a omissao da clausula em si esta resolvida em ALFA-CIS-03/BETA-CIS-06"),
 "GAMA-COS-01": ("FAIL","INCORRETA","critica","Confirmado; argumento de identidade estrutural SUPERADO: juiz J2c executou a cascata COS diretamente"),
 "GAMA-COS-02": ("FAIL","INCORRETA","critica","Confirmado; J2c executou FP e FN"),
 "GAMA-COS-03": ("FAIL","INCORRETA","major","Confirmado"),
 "GAMA-COS-04": ("FAIL","OMITIDA","major","Confirmado; greps re-executados pelo juiz (flush: 0 hits)"),
 "GAMA-COS-05": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado escopado como GAMA-CIS-05; forma estrutural identica verificada"),
 "GAMA-COS-06": ("FAIL","OMITIDA","major","Confirmado"),
 "GAMA-KPR-01": ("FAIL","INCORRETA","critica","Confirmado; J2d re-executado; fatos historicos (668/668 InvalidSeq+unknown) re-verificados pelo juiz no hash congelado; disciplina causal mantida"),
 "GAMA-KPR-02": ("FAIL","INCORRETA","critica","Confirmado; J2e re-executado"),
 "GAMA-KPR-03": ("FAIL","INCORRETA","minor","Confirmado; sombreamento verificado no artefato pelo juiz (:179 vs :138); probe null executado (J2e); sem leitor -> minor"),
 "GAMA-KPR-04": ("FAIL","INCORRETA","major","Confirmado; J2f: 2 addError -> 1 registro (sobrevive a clausula da chave publica); chave de dedupe verificada na fonte"),
 "GAMA-KPR-05": ("FAIL","INCORRETA","major","Confirmado; unknown executado; 668/668 historico re-verificado"),
 "GAMA-KPR-06": ("INCONCLUSIVE","INCONCLUSIVA","major","Mantido; H-KPR-1 permanece hipotese com testes discriminantes nomeados; fatos de estratificacao re-verificados pelo juiz; atribuicao causal so no replay"),
 "GAMA-KPR-07": ("FAIL","OMITIDA","major","Confirmado; greps re-executados (co?/optional/generateKeyPair: 0 hits em registros)"),
 "GAMA-SKY-01": ("FAIL","INCORRETA","critica","Confirmado; J2g: 2 violacoes -> 0 registros; sem Category_fail no artefato (verificado)"),
 "GAMA-SKY-02": ("FAIL","INCORRETA","critica","Confirmado; J2g: RANDOMIZED negado; regra sem REQUIRES verificada"),
 "GAMA-SKY-03": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; remove por objeto verificado e executado"),
 "GAMA-SKY-04": ("FAIL","OMITIDA","major","Confirmado; linha 83 e edges:64 lidas pelo juiz: nenhuma ressalva do gate"),
 "GAMA-SKY-05": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; walk do juiz reproduz a dupla inclusao do ORDER"),
 "GAMA-PBK-01": ("FAIL","INCORRETA","major","Confirmado; controle 1-linha-vs-N executado tambem pelo juiz (J2i); chave de colapso = __LOC compartilhado + ErrorSummary sem expecting (fonte verificada)"),
 "GAMA-PBK-02": ("FAIL","INCORRETA","major","Confirmado; mensagem falsa por 10x medida (J2i)"),
 "GAMA-PBK-03": ("FAIL","INCORRETA","major","Confirmado; f1/f2 emitem InvalidSequenceOfMethodCalls unknown (.mop:29/:35 verificado)"),
 "GAMA-PBK-04": ("FAIL","INCORRETA","critica","Confirmado; harmonizado major->critica (FEN-PBK-RESIDUO): J2h mostra o residuo em trace conforme ao oraculo; registro afirma violacao de sequencia inexistente; par.4. Atualizacao de H2 registrada (pareamento retorna em forma adiada)"),
 "GAMA-PBK-05": ("FAIL","INCORRETA","critica","Confirmado; J2h re-executado (err2 + SPECCED_KEY negado)"),
 "GAMA-PBK-06": ("FAIL","OMITIDA","major","Confirmado; greps re-executados ('1000' fora de 10000: 0 hits em gh101)"),
 "GAMA-PBK-07": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; prefixo estrela mantido no artefato (walk do juiz); ressalva do residuo adiado mantida"),
 "GAMA-SET-12": ("FAIL","INCORRETA","minor","Confirmado; diff de 1 linha (destroy) entre extratores conferido nos arquivos de evidencia; config re-verificada"),
 "GAMA-SET-13": ("FAIL","INCORRETA","major","Confirmado; 6/20 linhas 'new' nos CSVs de evidencia; GAMA-SET-09 ja verificado pelo juiz no batch A"),
 "GAMA-SET-14": ("FAIL","INCORRETA","major","Rota unica FECHADA pelo juiz: keying literal declaring-class#name verificado em RvsecAnalysisClient:585-586,628-630; sem resolucao de hierarquia; lado dinamico (call() casa subtipos) coerente com BETA-SET-04"),
 "GAMA-SET-15": ("PASS","FIDELIDADE_DEMONSTRADA","minor","Confirmado; todos os expecting alcancaveis sao literais de compilacao (leitura dos 5 .mop pelo juiz); SKY nada serializa"),
 "GAMA-SET-16": ("INCONCLUSIVE","INCONCLUSIVA","major","Mantido; zeros re-verificados pelo juiz (greps no hash congelado); zero nunca e conformidade; testes de replay nomeados"),
}

# REF-C-02 backfill: the 7 FAIL rows whose agents filed no fenomeno_id.
# Assignments are the ones the synthesis matrix (rev. 1 §1/§2) already made
# narratively; here they enter the machine-readable record.
FEN_BACKFILL = {
    "BETA-CIS-06": "FEN-CIS-CTOR1-OMITIDA",
    "BETA-CIS-07": "FEN-CIS-LENOFF",
    "BETA-CIS-08": "FEN-SET-GENCIPHER-EXTRA",
    "BETA-COS-07": "FEN-CIS-LENOFF",
    "BETA-COS-09": "FEN-SET-GENCIPHER-EXTRA",
    "BETA-COS-10": "FEN-CIS-CTOR1-OMITIDA",
    "BETA-PBK-06": "FEN-PBK-RESIDUO",
}

def main():
    rows_out = []
    header = None
    for fname in ("alfa_claims.csv", "beta_claims.csv", "gama_claims.csv"):
        with open(os.path.join(AUD, fname), newline="", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            if header is None:
                header = rd.fieldnames[:]
            for row in rd:
                cid = row["id"].strip()
                if cid not in R:
                    sys.exit(f"missing resolution for {cid}")
                res, cls, sev, just = R[cid]
                row["resolucao_juiz"] = res
                row["classificacao_final"] = cls
                row["severidade_final"] = sev
                row["justificativa_curta"] = just
                agent_fen = (row.get("fenomeno_id") or "").strip()
                row["fenomeno_id_final"] = agent_fen or FEN_BACKFILL.get(cid, "")
                rows_out.append(row)
    assert len(rows_out) == 133, len(rows_out)
    # rev. 2 invariant: every FAIL row carries a phenomenon in the judge column
    unlinked = [r["id"] for r in rows_out
                if r["resolucao_juiz"] == "FAIL" and not r["fenomeno_id_final"]]
    assert not unlinked, f"FAIL rows without fenomeno_id_final: {unlinked}"
    out_header = header + ["resolucao_juiz", "classificacao_final", "severidade_final", "justificativa_curta", "fenomeno_id_final"]
    out = os.path.join(AUD, "juiz_claims_resolvidos_batchB.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_header, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)
    from collections import Counter
    c = Counter(r["resolucao_juiz"] for r in rows_out)
    crit = sum(1 for r in rows_out if r["resolucao_juiz"] == "FAIL" and r["severidade_final"] == "critica")
    print(f"wrote {out}: {len(rows_out)} claims -> {dict(c)}; critical FAILs: {crit}")

if __name__ == "__main__":
    main()
