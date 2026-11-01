# language: pt
Funcionalidade: Parcelas balão pagas à construtora
  O comprador escolhe quanto paga à construtora por mês. O que as parcelas mensais não
  cobrem do saldo da entrada é pago em parcelas balão nos meses de obra combinados — o
  valor do balão é derivado, nunca digitado. Os balões são corrigidos pelo INCC como
  qualquer outro pagamento à construtora.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses até a entrega
    E a construtora exige uma entrada de 20,0% do preço de tabela
    E o comprador paga R$ 13.000,00 de FGTS na assinatura

  Cenário: Os balões absorvem exatamente o que as parcelas mensais deixam descoberto
    Dado que o comprador paga à construtora R$ 2.500,00 por mês
    E o contrato tem parcelas balão nos meses 6 e 12
    Quando o comprador executa a simulação
    Então o saldo da entrada a pagar durante a obra deve ser R$ 75.000,00
    E a parcela mensal nominal da construtora deve ser R$ 2.500,00
    E o valor não coberto pelas parcelas mensais deve ser R$ 27.500,00
    E a parcela balão nominal deve ser R$ 13.750,00
    E a parcela balão no mês 6 deve ser R$ 14.223,11
    E a parcela balão no mês 12 deve ser R$ 14.712,50
    E o total pago à construtora durante a obra deve ser R$ 79.214,67
    E a correção do INCC sobre a entrada deve ser R$ 4.214,67

  Cenário: Um único balão assume todo o valor descoberto
    Dado que o comprador paga à construtora R$ 3.000,00 por mês
    E o contrato tem uma parcela balão no mês 10
    Quando o comprador executa a simulação
    Então a parcela balão nominal deve ser R$ 18.000,00
    E a parcela balão no mês 10 deve ser R$ 19.044,04

  Cenário: Parcelas que cobrem exatamente o saldo dispensam balão
    Dado que o comprador paga à construtora R$ 3.947,37 por mês
    Quando o comprador executa a simulação
    Então o valor não coberto pelas parcelas mensais deve ser R$ 0,00
    E a parcela balão nominal deve ser R$ 0,00

  Cenário: Parcelas que deixam valor descoberto sem mês de balão são rejeitadas
    Dado que o comprador paga à construtora R$ 2.000,00 por mês
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "parcelas mensais de R$ 38.000,00 não cobrem o saldo da entrada de R$ 75.000,00; faltam R$ 37.000,00 — adicione meses de balão ou aumente a parcela"

  Esquema do Cenário: Um cronograma de balões que não cabe no contrato é rejeitado
    Dado que o comprador paga à construtora R$ <parcela> por mês
    E o contrato tem uma parcela balão no mês <mes>
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "<erro>"

    Exemplos:
      | parcela  | mes | erro                                                                 |
      | 5.000,00 | 6   | parcelas mensais de R$ 95.000,00 excedem o saldo da entrada de R$ 75.000,00 |
      | 2.000,00 | 24  | o mês de balão 24 é posterior à entrega (mês 19)                     |

  Cenário: Um mês de balão sem parcela mensal escolhida não pode ser dimensionado
    Dado que o contrato tem uma parcela balão no mês 6
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "é necessária uma parcela mensal da construtora para dimensionar as parcelas balão"
