
def simular_sac(valor_imovel, percentual_entrada=0.20, taxa_anual=10.26, prazo_anos=30):
    entrada_base = valor_imovel * percentual_entrada
    saldo_devedor_base = valor_imovel - entrada_base
    
    # Aplicando as mesmas proporções de custos extras do seu exemplo (relação proporcional)
    # Exemplo anterior: Imovel 274k, Entrada 51k, Saldo 223k
    # Custos extras: incc entrada (11k/51k), incc saldo (42k/223k)
    # Vamos projetar proporcionalmente baseado na volatilidade do seu caso
    fator_incc_entrada = 11.0 / 51.0
    fator_incc_saldo = 42.0 / 223.0
    
    incc_entrada = entrada_base * fator_incc_entrada
    incc_saldo = saldo_devedor_base * fator_incc_saldo
    
    # Evolução de obra proporcional (anterior foi 35k para 274k)
    fator_obra = 35.0 / 274.0
    evolucao_obra = valor_imovel * fator_obra
    
    # Documentação proporcional (7k para 274k)
    fator_doc = 7.0 / 274.0
    documentacao = valor_imovel * fator_doc
    
    saldo_financiado_final = saldo_devedor_base + incc_saldo
    custo_total_real = valor_imovel + incc_entrada + evolucao_obra + incc_saldo + documentacao
    
    # Cálculo da primeira parcela SAC
    prazo_meses = prazo_anos * 12
    amortizacao = saldo_financiado_final / prazo_meses
    taxa_mensal = (1 + taxa_anual/100)**(1/12) - 1
    juros_1 = saldo_financiado_final * taxa_mensal
    parcela_1 = amortizacao + juros_1
    
    # Ultima parcela
    juros_fim = amortizacao * taxa_mensal
    parcela_fim = amortizacao + juros_fim
    
    return {
        "entrada_base": entrada_base,
        "incc_entrada": incc_entrada,
        "saldo_base": saldo_devedor_base,
        "incc_saldo": incc_saldo,
        "saldo_final": saldo_financiado_final,
        "obra": evolucao_obra,
        "doc": documentacao,
        "total": custo_total_real,
        "amortizacao": amortizacao,
        "parcela_1": parcela_1,
        "parcela_fim": parcela_fim
    }

riva = simular_sac(440000)
fatima = simular_sac(396000)

print("RA 440k:")
for k, v in riva.items():
    print(f"{k}: {v:.2f}")

print("\nF 396k:")
for k, v in fatima.items():
    print(f"{k}: {v:.2f}")
