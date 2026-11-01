# language: pt
Funcionalidade: Juros de obra cobrados pelo banco
  Durante a obra o banco libera recursos à construtora conforme o avanço físico, e o
  comprador paga juros (juros de obra / evolução de obra) sobre o que já foi liberado.
  O avanço cresce linearmente do nível na assinatura até 100% na entrega. Essa cobrança
  nunca reduz o saldo do financiamento.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Cenário: Os juros de obra crescem mês a mês com o avanço físico
    Dado um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses até a entrega
    E a obra está 0% concluída na assinatura
    Quando o comprador executa a simulação
    Então os juros de obra no mês 1 devem ser R$ 152,26
    E os juros de obra no mês 19 devem ser R$ 3.201,99
    E o total de juros de obra deve ser R$ 30.965,10

  Esquema do Cenário: Comprar um prédio já adiantado significa pagar mais juros desde o primeiro dia
    Dado um imóvel "SO" anunciado por R$ 300.000,00 com 4 meses até a entrega
    E a obra está <avanco>% concluída na assinatura
    Quando o comprador executa a simulação
    Então os juros de obra no mês 1 devem ser R$ <primeiro_mes>
    E o total de juros de obra deve ser R$ <total>

    Exemplos:
      | avanco | primeiro_mes | total    |
      | 0      | 493,12       | 4.987,20 |
      | 80     | 1.676,61     | 7.363,12 |

  Cenário: Os juros de obra não reduzem o saldo financiado na entrega
    Dado um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses até a entrega
    E a obra está 0% concluída na assinatura
    Quando o comprador executa a simulação
    Então o saldo do financiamento na entrega deve ser R$ 391.802,30
