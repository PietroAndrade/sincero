# language: pt
Funcionalidade: Validação de entradas
  Entradas inválidas são rejeitadas com uma mensagem clara em vez de produzir uma
  simulação enganosa.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Esquema do Cenário: Dados impossíveis do imóvel são rejeitados
    Dado um imóvel "X" anunciado por R$ <preco> com <meses> meses restantes até a entrega
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "<erro>"

    Exemplos:
      | preco      | meses | erro                                                    |
      | 0,00       | 12    | o preço de tabela deve ser maior que zero               |
      | 440.000,00 | 0     | os meses restantes até a entrega devem ser pelo menos 1 |


  Esquema do Cenário: Um percentual de entrada impossível é rejeitado
    Dado um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E a construtora exige uma entrada de <percentual>% do preço de tabela
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "o percentual de entrada deve estar entre 0 e 100"

    Exemplos:
      | percentual |
      | -10        |
      | 150        |

  Cenário: Pagamentos negativos na assinatura são rejeitados
    Dado um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E o comprador paga R$ -1.000,00 em dinheiro na assinatura
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "os pagamentos na assinatura não podem ser negativos"

  Cenário: FGTS e dinheiro acima do preço de tabela são rejeitados
    Dado um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E que o comprador paga R$ 300.000,00 de FGTS na assinatura
    E o comprador paga R$ 200.000,00 em dinheiro na assinatura
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "os pagamentos na assinatura de R$ 500.000,00 excedem o preço de tabela de R$ 440.000,00"

  Cenário: Pagar todo o preço de tabela na assinatura é uma compra à vista, não um erro
    Dado um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E o comprador paga R$ 440.000,00 em dinheiro na assinatura
    Quando o comprador executa a simulação
    Então o saldo do financiamento na entrega deve ser R$ 0,00
    E o total de juros de obra deve ser R$ 0,00
    E a parcela da SAC no mês 1 deve ser R$ 0,00

  Esquema do Cenário: Taxas de mercado impossíveis são rejeitadas em vez de derrubar a simulação
    Dado INCC de <incc>% ao ano e financiamento bancário de <banco>% ao ano em <prazo> meses
    E um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "<erro>"

    Exemplos:
      | incc | banco | prazo | erro                                                  |
      | -100 | 10,26 | 360   | a taxa do INCC deve ser maior que -100% ao ano        |
      | 7,00 | -1,00 | 360   | a taxa de juros do banco não pode ser negativa        |
      | 7,00 | 10,26 | 0     | o prazo do financiamento deve ser de pelo menos 1 mês |

  Cenário: Um INCC deflacionário é incomum, mas válido
    Dado INCC de -2,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    Quando o comprador executa a simulação
    Então a dívida fantasma do INCC sobre o saldo do financiamento deve ser R$ -11.081,46

  Cenário: Custos de cartório negativos são rejeitados
    Dado um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E custos de cartório de ITBI -3,0% e registro 0,5% do preço de tabela
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "os percentuais de custos de cartório não podem ser negativos"

  Cenário: Um crédito pré-aprovado negativo é rejeitado
    Dado um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E que o banco pré-aprovou um crédito de R$ -1.000,00
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "o crédito pré-aprovado não pode ser negativo"

  Cenário: Um prazo de pro-soluto de zero meses não consegue dividir o gap de crédito
    Dado um imóvel "X" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E qualquer dívida pro-soluto é paga à construtora em 0 meses
    Quando o comprador executa a simulação
    Então a simulação deve ser rejeitada com o erro "o prazo do pro-soluto deve ser de pelo menos 1 mês"
