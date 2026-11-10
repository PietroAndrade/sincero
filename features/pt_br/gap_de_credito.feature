# language: pt
Funcionalidade: Gap de crédito no repasse ao banco
  O banco pré-aprova um crédito com base no saldo nominal da assinatura. Na entrega o
  saldo foi corrigido pelo INCC, então o comprador precisa de uma aprovação maior. O que
  o banco não cobrir vira dívida de curto prazo com a construtora (pro-soluto).

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E a construtora exige uma entrada de 20,0% do preço de tabela
    E qualquer dívida pro-soluto é paga à construtora em 12 meses

  Esquema do Cenário: A pré-aprovação do banco decide o tamanho da dívida pro-soluto
    Dado que o banco pré-aprovou um crédito de R$ <pre_aprovado>
    Quando o comprador executa a simulação
    Então o crédito necessário na entrega deve ser R$ 391.802,30
    E o gap de crédito deve ser R$ <gap>
    E a parcela mensal do pro-soluto deve ser R$ <pro_soluto>

    Exemplos:
      | pre_aprovado | gap       | pro_soluto |
      | 352.000,00   | 39.802,30 | 3.316,86   |
      | 370.000,00   | 21.802,30 | 1.816,86   |
      | 400.000,00   | 0,00      | 0,00       |

  Cenário: Um prazo maior de pro-soluto reduz pela metade o peso mensal
    Dado que o banco pré-aprovou um crédito de R$ 352.000,00
    E qualquer dívida pro-soluto é paga à construtora em 24 meses
    Quando o comprador executa a simulação
    Então a parcela mensal do pro-soluto deve ser R$ 1.658,43

  Cenário: Sem pré-aprovação explícita assume-se o saldo nominal
    Quando o comprador executa a simulação
    Então o gap de crédito deve ser R$ 39.802,30
