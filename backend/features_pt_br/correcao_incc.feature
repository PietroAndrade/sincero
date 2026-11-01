# language: pt
Funcionalidade: Correção do INCC sobre o saldo do financiamento
  A parte do preço não paga como entrada fica com a construtora até a entrega e é
  corrigida mensalmente pelo INCC. Nas chaves, o saldo corrigido é o que o banco
  precisa financiar; a diferença para o saldo nominal é a "dívida fantasma" que
  surpreende a maioria dos compradores.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Esquema do Cenário: Quanto mais longa a obra, maior a dívida fantasma do INCC
    Dado um imóvel "<nome>" anunciado por R$ <preco> com <meses> meses até a entrega
    Quando o comprador executa a simulação
    Então o saldo nominal do financiamento deve ser R$ <nominal>
    E o saldo do financiamento na entrega deve ser R$ <na_entrega>
    E a dívida fantasma do INCC sobre o saldo do financiamento deve ser R$ <divida_fantasma>

    Exemplos:
      | nome | preco      | meses | nominal    | na_entrega | divida_fantasma |
      | SO   | 300.000,00 | 4     | 240.000,00 | 245.474,19 | 5.474,19        |
      | F    | 396.000,00 | 8     | 316.800,00 | 331.416,68 | 14.616,68       |
      | RA   | 440.000,00 | 19    | 352.000,00 | 391.802,30 | 39.802,30       |

  Cenário: O contrato de referência da análise original cresce de R$ 223 mil para R$ 264 mil
    Dado um imóvel "REF" anunciado por R$ 274.000,00 com 30 meses até a entrega
    E a construtora exige uma entrada de 18,613% do preço de tabela
    Quando o comprador executa a simulação
    Então a entrada exigida deve ser R$ 50.999,62
    E o saldo nominal do financiamento deve ser R$ 223.000,38
    E o saldo do financiamento na entrega deve ser R$ 264.097,96
    E a dívida fantasma do INCC sobre o saldo do financiamento deve ser R$ 41.097,58

  Cenário: Um INCC menor encolhe a dívida fantasma
    Dado INCC de 4,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses até a entrega
    Quando o comprador executa a simulação
    Então a dívida fantasma do INCC sobre o saldo do financiamento deve ser R$ 22.552,00
