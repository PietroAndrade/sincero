# language: pt
Funcionalidade: Financiamento bancário após a entrega das chaves
  Na entrega, o saldo corrigido pelo INCC é financiado pelo banco no prazo contratado,
  pela SAC (amortização constante, parcelas decrescentes) ou pela PRICE (parcela fixa).
  O banco exige que a primeira parcela caiba em uma fração da renda familiar.

  Contexto:
    Dado INCC de 7,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    E um imóvel "RA" anunciado por R$ 440.000,00 com 19 meses até a entrega
    E a construtora exige uma entrada de 20,0% do preço de tabela

  Cenário: As parcelas da SAC começam altas e diminuem todo mês
    Quando o comprador executa a simulação
    Então a amortização mensal da SAC deve ser R$ 1.088,34
    E a parcela da SAC no mês 1 deve ser R$ 4.290,33
    E a parcela da SAC no mês 2 deve ser R$ 4.281,44
    E a parcela da SAC no mês 180 deve ser R$ 2.698,23
    E a parcela da SAC no mês 360 deve ser R$ 1.097,23
    E o total de juros pagos na SAC deve ser R$ 577.959,37

  Cenário: A PRICE mantém a parcela fixa mas custa mais juros no total
    Quando o comprador executa a simulação
    Então a parcela da PRICE deve ser R$ 3.382,59
    E os juros da PRICE no mês 1 devem ser R$ 3.201,99
    E a amortização da PRICE no mês 1 deve ser R$ 180,60
    E o total de juros pagos na PRICE deve ser R$ 825.929,20

  Cenário: A renda mínima decorre da primeira parcela e do teto de comprometimento do banco
    Dado que o banco aceita parcelas de até 30% da renda familiar
    Quando o comprador executa a simulação
    Então a renda mínima para a SAC deve ser R$ 14.301,10
    E a renda mínima para a PRICE deve ser R$ 11.275,29

  Cenário: Um INCC menor durante a obra também reduz a parcela do banco
    Dado INCC de 4,00% ao ano e financiamento bancário de 10,26% ao ano em 360 meses
    Quando o comprador executa a simulação
    Então a parcela da SAC no mês 1 deve ser R$ 4.101,44
