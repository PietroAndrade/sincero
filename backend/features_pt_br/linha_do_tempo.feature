# language: pt
Funcionalidade: Linha do tempo mensal do fluxo de caixa
  O mês 0 é a assinatura (pagamentos iniciais). Os meses 1..N são a fase de obra
  (parcelas da construtora, balões e juros de obra). A partir do mês N+1 paga-se apenas
  a parcela do banco.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses restantes até a entrega
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Cenário: A linha do tempo mostra onde terminam os boletos da construtora e começam os do banco
    Dado que o comprador paga R$ 13.000,00 de FGTS na assinatura
    E o comprador paga à construtora R$ 2.500,00 por mês
    E o contrato tem parcelas balão nos meses 6 e 12
    Quando o comprador executa a simulação
    Então a linha do tempo deve ter 380 meses
    E a linha do tempo no mês 0 deve ser:
      | parcela_construtora | balao | juros_de_obra | parcela_banco | total     |
      | 0,00                | 0,00  | 0,00          | 0,00          | 13.000,00 |
    E a linha do tempo no mês 6 deve ser:
      | parcela_construtora | balao     | juros_de_obra | parcela_banco | total     |
      | 2.586,02            | 14.223,11 | 939,69        | 0,00          | 17.748,82 |
    E a linha do tempo no mês 19 deve ser:
      | parcela_construtora | balao | juros_de_obra | parcela_banco | total    |
      | 2.782,69            | 0,00  | 3.201,99      | 0,00          | 5.984,68 |
    E a linha do tempo no mês 20 deve ser:
      | parcela_construtora | balao | juros_de_obra | parcela_banco | total    |
      | 0,00                | 0,00  | 0,00          | 4.290,33      | 4.290,33 |

  Cenário: O mês do balão é o mês mais pesado da fase de obra
    Dado que o comprador paga R$ 13.000,00 de FGTS na assinatura
    E o comprador paga à construtora R$ 2.500,00 por mês
    E o contrato tem parcelas balão nos meses 6 e 12
    Quando o comprador executa a simulação
    Então o pico de desembolso mensal deve ser R$ 19.331,55 no mês 12
    E o desembolso total durante a fase de obra deve ser R$ 123.179,77
