# language: pt
Funcionalidade: Custo total do imóvel até a entrega das chaves
  O custo real é o preço de tabela mais a correção do INCC sobre a entrada, a correção
  do INCC sobre o saldo do financiamento, os juros de obra e os custos de cartório
  (ITBI, escritura e registro).

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Cenário: A composição de custos mostra quase 20% acima do preço de tabela
    Dado que o comprador paga R$ 13.000,00 de FGTS na assinatura
    E custos de cartório de ITBI 2,0% e registro 0,5% do preço de tabela
    Quando o comprador executa a simulação
    Então a composição de custos deve ser:
      | componente          | valor_base | adicional | valor_final |
      | Entrada             | 88.000,00  | 4.387,99  | 92.387,99   |
      | Saldo financiamento | 352.000,00 | 39.802,30 | 391.802,30  |
      | Juros de obra       | 0,00       | 30.965,10 | 30.965,10   |
      | Custos de cartório  | 0,00       | 11.000,00 | 11.000,00   |
      | Total               | 440.000,00 | 86.155,39 | 526.155,39  |
    E o custo extra total sobre o preço de tabela deve ser 19,58%

  Cenário: Os custos de cartório se dividem entre ITBI e registro
    Dado custos de cartório de ITBI 2,0% e registro 0,5% do preço de tabela
    Quando o comprador executa a simulação
    Então o ITBI deve ser R$ 8.800,00
    E os custos de registro e escritura devem ser R$ 2.200,00
