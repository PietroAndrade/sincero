# language: pt
Funcionalidade: Entrada devida à construtora durante a obra
  A construtora exige um percentual do preço de tabela como entrada. O que o comprador
  paga na assinatura (FGTS ou dinheiro) é abatido imediatamente; o restante é dividido
  em parcelas nominais iguais até a entrega, cada uma corrigida pelo INCC acumulado até
  o mês em que é paga.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses até a entrega
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Cenário: O FGTS pago na assinatura é abatido antes de dividir a entrada em parcelas
    Dado que o comprador paga R$ 13.000,00 de FGTS na assinatura
    Quando o comprador executa a simulação
    Então a entrada exigida deve ser R$ 88.000,00
    E o saldo da entrada a pagar durante a obra deve ser R$ 75.000,00
    E a parcela mensal nominal da construtora deve ser R$ 3.947,37

  Cenário: Cada parcela da construtora cresce com o INCC acumulado até o seu pagamento
    Dado que o comprador paga R$ 13.000,00 de FGTS na assinatura
    Quando o comprador executa a simulação
    Então a parcela da construtora no mês 1 deve ser R$ 3.969,69
    E a parcela da construtora no mês 19 deve ser R$ 4.393,72
    E o total pago à construtora durante a obra deve ser R$ 79.387,99
    E a correção do INCC sobre a entrada deve ser R$ 4.387,99

  Esquema do Cenário: Mais dinheiro na assinatura reduz a parcela da construtora e, além da entrada, o saldo financiado
    Dado que o comprador paga R$ 13.000,00 de FGTS na assinatura
    E o comprador paga R$ <dinheiro> em dinheiro na assinatura
    Quando o comprador executa a simulação
    Então o saldo da entrada a pagar durante a obra deve ser R$ <restante>
    E a parcela mensal nominal da construtora deve ser R$ <parcela>
    E o saldo nominal do financiamento deve ser R$ <saldo_financiamento>

    Exemplos:
      | dinheiro   | restante  | parcela  | saldo_financiamento |
      | 0,00       | 75.000,00 | 3.947,37 | 352.000,00          |
      | 30.000,00  | 45.000,00 | 2.368,42 | 352.000,00          |
      | 75.000,00  | 0,00      | 0,00     | 352.000,00          |
      | 100.000,00 | 0,00      | 0,00     | 327.000,00          |

  Cenário: Sem nenhum pagamento na assinatura toda a entrada é dividida em parcelas
    Quando o comprador executa a simulação
    Então o saldo da entrada a pagar durante a obra deve ser R$ 88.000,00
    E a parcela mensal nominal da construtora deve ser R$ 4.631,58
