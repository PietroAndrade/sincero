# language: pt
Funcionalidade: Juros de obra cobrados pelo banco
  Durante os meses restantes até a entrega o banco libera o saldo financiado à
  construtora, e o comprador paga juros (juros de obra / evolução de obra) sobre o que já
  foi liberado. A liberação é distribuída uniformemente pelos meses restantes. Essa
  cobrança nunca reduz o saldo do financiamento.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Cenário: Os juros de obra crescem mês a mês conforme mais saldo é liberado
    Dado um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    Quando o comprador executa a simulação
    Então os juros de obra no mês 1 devem ser R$ 152,26
    E os juros de obra no mês 19 devem ser R$ 3.201,99
    E o total de juros de obra deve ser R$ 30.965,10

  Esquema do Cenário: Quanto menos meses restantes, menos juros de obra se paga
    Dado um imóvel "<nome>" anunciado por R$ <preco> com <meses> meses restantes até a entrega
    Quando o comprador executa a simulação
    Então os juros de obra no mês 1 devem ser R$ <primeiro_mes>
    E o total de juros de obra deve ser R$ <total>

    Exemplos:
      | nome | preco      | meses | primeiro_mes | total     |
      | SO   | 300.000,00 | 4     | 493,12       | 4.987,20  |
      | F    | 396.000,00 | 8     | 325,46       | 12.029,66 |
      | RA   | 440.000,00 | 19    | 152,26       | 30.965,10 |

  Cenário: Os juros de obra não reduzem o saldo financiado na entrega
    Dado um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    Quando o comprador executa a simulação
    Então o saldo do financiamento na entrega deve ser R$ 391.802,30
