# Handoff: engine de cálculo de imóveis na planta

## 1. Escopo e regras de negócio

A ferramenta trata a assimetria de informação no mercado brasileiro de lançamentos (na planta), mapeando a "dívida fantasma" criada pela sobreposição de indexadores financeiros.

- Fase de obra (indexador INCC): corrigido mensalmente sobre o saldo devedor restante com a construtora e sobre o saldo projetado de repasse bancário. A média histórica usada nos cálculos é de 7,00% a.a.
- Evolução de obra (juros de obra): cobrada pela Caixa Econômica Federal proporcionalmente à evolução física da construção. Não amortiza o saldo devedor principal.
- Fase de amortização (pós-chaves): financiamento bancário tradicional pela Caixa (SBPE), com taxa de 10,26% a.a. + TR e prazo de 360 meses (30 anos). Os sistemas de amortização são SAC (parcelas decrescentes) e PRICE (parcelas fixas).

## 2. Dados dos empreendimentos (novembro de 2026)

O sistema deve processar estes cenários base (data base: novembro de 2026):

- SO: R$ 300.000, entrega em março de 2027 (4 meses)
- F: R$ 396.000, entrega em julho de 2027 (8 meses)
- SV: R$ 233.000, entrega em abril de 2028 (17 meses)
- F4: R$ 320.400, entrega em junho de 2028 (19 meses)
- RA: R$ 440.000, entrega em junho de 2028 (19 meses)

## 3. Código-fonte da engine (engine_financiamento.py)

A classe `CalculadoraImovelPlanta` projeta a correção do INCC pelo prazo exato da obra, calcula as mensalidades lineares com a construtora depois de abater o sinal (FGTS e dinheiro vivo) e gera as tabelas SAC e Price do banco.

```python
import math

class CalculadoraImovelPlanta:
    def __init__(self, taxa_incc_aa=7.0, taxa_banco_aa=10.26, prazo_meses=360):
        """
        Inicializa a engine de cálculos financeiros para imóveis na planta no Brasil.
        """
        self.taxa_incc_am = (1 + taxa_incc_aa / 100) ** (1 / 12) - 1
        self.taxa_banco_am = (1 + taxa_banco_aa / 100) ** (1 / 12) - 1
        self.prazo_meses = prazo_meses

    def calcular_cenario(self, nome, preco_tabela, meses_ate_entrega, fgts_sinal, dinheiro_vivo_inicial=0):
        # 1. Proporção padrão de entrada exigida pelas construtoras (Próximo a 18.6%)
        proporcao_entrada = 0.18613
        entrada_total_necessaria = preco_tabela * proporcao_entrada
        
        # 2. Saldo devedor nominal que irá para o repasse bancário
        saldo_repasse_nominal = preco_tabela - entrada_total_necessaria
        
        # 3. Cálculo do fluxo da construtora (Abatendo o sinal total na largada)
        sinal_total = fgts_sinal + dinheiro_vivo_inicial
        saldo_entrada_parcelar = max(0.0, entrada_total_necessaria - sinal_total)
        parcela_construtora_mensal = saldo_entrada_parcelar / meses_ate_entrega if meses_ate_entrega > 0 else 0
        
        # 4. Projeção do efeito cascata do INCC sobre o Saldo do Repasse Bancário durante a obra
        saldo_repasse_corrigido = saldo_repasse_nominal * ((1 + self.taxa_incc_am) ** meses_ate_entrega)
        divida_fantasma_incc = saldo_repasse_corrigido - saldo_repasse_nominal
        
        # 5. Financiamento Pós-Chaves: Tabela SAC (1ª Parcela)
        amortizacao_sac = saldo_repasse_corrigido / self.prazo_meses
        juros_primeira_parcela_sac = saldo_repasse_corrigido * self.taxa_banco_am
        primeira_parcela_sac = amortizacao_sac + juros_primeira_parcela_sac
        ultima_parcela_sac = amortizacao_sac + (amortizacao_sac * self.taxa_banco_am)
        
        # 6. Financiamento Pós-Chaves: Tabela Price (Parcela Fixa)
        if self.taxa_banco_am > 0:
            parcela_price = (saldo_repasse_corrigido * self.taxa_banco_am) / (1 - (1 + self.taxa_banco_am) ** (-self.prazo_meses))
        else:
            parcela_price = saldo_repasse_corrigido / self.prazo_meses

        return {
            "nome": nome,
            "prazo_obra_meses": meses_ate_entrega,
            "entrada_necessaria": round(entrada_total_necessaria, 2),
            "parcela_mensal_construtora": round(parcela_construtora_mensal, 2),
            "repasse_banco_original": round(saldo_repasse_nominal, 2),
            "correcao_incc_acumulada": round(divida_fantasma_incc, 2),
            "saldo_final_financiado": round(saldo_repasse_corrigido, 2),
            "primeira_parcela_sac": round(primeira_parcela_sac, 2),
            "ultima_parcela_sac": round(ultima_parcela_sac, 2),
            "parcela_fixa_price": round(parcela_price, 2),
            "renda_minima_sac": round(primeira_parcela_sac / 0.3, 2)
        }

# --- INSTANCIAÇÃO E EXECUÇÃO DE EXEMPLO DOS CENÁRIOS ALVO ---
if __name__ == "__main__":
    engine = CalculadoraImovelPlanta()
    
    # Lista de dicionários simulando os dados de entrada capturados no contexto do usuário
    empreendimentos = [
        {"nome": "SO", "preco": 300000, "meses": 4},
        {"nome": "F", "preco": 396000, "meses": 8},
        {"nome": "SV", "preco": 233000, "meses": 17},
        {"nome": "F4", "preco": 320400, "meses": 19},
        {"nome": "RA", "preco": 440000, "meses": 19}
    ]
    
    print("=== CENÁRIO PADRÃO: APENAS R$ 13 MIL DE FGTS COMO SINAL ===")
    for emp in empreendimentos:
        res = engine.calcular_cenario(emp["nome"], emp["preco"], emp["meses"], fgts_sinal=13000)
        print(f"\n🏠 {res['nome']} (Prazo: {res['prazo_obra_meses']}m)")
        print(f"   └─ Boleto Mensal Construtora: R$ {res['parcela_mensal_construtora']:.2f}")
        print(f"   └─ Impacto Invisível do INCC: R$ {res['correcao_incc_acumulada']:.2f}")
        print(f"   └─ Saldo de Financiamento na Entrega: R$ {res['saldo_final_financiado']:.2f}")
        print(f"   └─ Financiamento (1ª Parcela SAC): R$ {res['primeira_parcela_sac']:.2f}")
```

## 4. Próximos passos

Para transformar o script em uma aplicação de mercado (como CRIF ou SIMPL), as próximas funcionalidades são:

1. INCC dinâmico: criar uma rotina de scraping ou consumo de API para buscar a taxa do INCC (FGV) em tempo real, em vez de fixar 7%.
2. Amortização extra: permitir aportes esporádicos (anuais ou balões) e recalcular a redução imediata nas parcelas da construtora.
3. Linha do tempo visual: um gráfico de barras sobrepostas mostrando quando termina o boleto da construtora e começa o boleto bancário do repasse definitivo.

Pendentes: a estrutura JSON de payload para a interface e o cálculo do teto dos juros de obra.
