# language: pt
Funcionalidade: Comparação de imóveis e simulação com mais dinheiro
  Quem escolhe entre vários imóveis na planta quer vê-los lado a lado e testar como
  colocar mais dinheiro na mesa muda cada boleto.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E a construtora exige uma entrada de 20,0% do preço de tabela
    E a obra está 0% concluída na assinatura

  Cenário: Os cinco imóveis candidatos lado a lado
    Dado que o comprador paga R$ 13.000,00 de FGTS na assinatura
    E os imóveis candidatos:
      | nome | preco      | meses |
      | SO   | 300.000,00 | 4     |
      | F    | 396.000,00 | 8     |
      | SV   | 233.000,00 | 17    |
      | F4   | 320.400,00 | 19    |
      | RA   | 440.000,00 | 19    |
    Quando o comprador compara os imóveis candidatos
    Então a tabela de comparação deve ser:
      | nome | parcela_construtora | divida_fantasma_incc | saldo_na_entrega | juros_de_obra | primeira_parcela_sac | renda_minima_sac |
      | SO   | 11.750,00           | 5.474,19             | 245.474,19       | 4.987,20      | 2.688,00             | 8.960,01         |
      | F    | 8.275,00            | 14.616,68            | 331.416,68       | 12.029,66     | 3.629,09             | 12.096,98        |
      | SV   | 1.976,47            | 18.750,66            | 205.150,66       | 14.646,21     | 2.246,45             | 7.488,17         |
      | F4   | 2.688,42            | 28.983,31            | 285.303,31       | 22.548,22     | 3.124,14             | 10.413,80        |
      | RA   | 3.947,37            | 39.802,30            | 391.802,30       | 30.965,10     | 4.290,33             | 14.301,10        |

  Cenário: Uma escada de dinheiro mostra o que cada real a mais na assinatura compra
    Dado um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses até a entrega
    E o comprador paga R$ 13.000,00 de FGTS na assinatura
    Quando o comprador compara pagar os seguintes valores em dinheiro na assinatura:
      | dinheiro   |
      | 0,00       |
      | 30.000,00  |
      | 75.000,00  |
      | 100.000,00 |
    Então a escada de dinheiro deve ser:
      | dinheiro   | parcela_construtora | divida_fantasma_incc | saldo_na_entrega | primeira_parcela_sac | renda_minima_sac |
      | 0,00       | 3.947,37            | 39.802,30            | 391.802,30       | 4.290,33             | 14.301,10        |
      | 30.000,00  | 2.368,42            | 39.802,30            | 391.802,30       | 4.290,33             | 14.301,10        |
      | 75.000,00  | 0,00                | 39.802,30            | 391.802,30       | 4.290,33             | 14.301,10        |
      | 100.000,00 | 0,00                | 36.975,43            | 363.975,43       | 3.985,62             | 13.285,40        |

  Cenário: Reexecutar com um INCC menor mostra quanto do custo é indexação
    Dado um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses até a entrega
    Quando o comprador executa a simulação
    E o comprador reexecuta a simulação com o INCC a 4,00% ao ano
    Então a dívida fantasma do INCC sobre o saldo do financiamento deve cair de R$ 39.802,30 para R$ 22.552,00
    E a parcela da SAC no mês 1 deve cair de R$ 4.290,33 para R$ 4.101,44
